# Plugin install redesign — design spec

Date: 2026-06-05
Status: approved (brainstorming)

## Problem

Plugin install is spread across `install.ps1`, `install.sh`, and two
documentation-only manifests (`manifest/claude-plugins.json`,
`manifest/codex-plugins.json`). The plugin list and per-plugin install logic are
hardcoded and duplicated across the two host scripts, so:

- **Drift** — the same plugin set is declared in three places; they fall out of
  sync (e.g. `attribution` vs `reply-trace` naming, marketplace name vs source
  repo name).
- **Host divergence** — Claude (marketplace + directory wrapper) and Codex
  (personal local wrapper + store) have different plugin models, each
  hand-coded per host script.
- **Fragile env glue** — environment-specific bugs (UTF-8 BOM in copied
  SKILL.md, missing standalone `pip`, versioned user Scripts dir, `bash`
  required by gstack build) live inline in PowerShell/bash and were each fixed
  reactively with no shared, tested home.

## Goal

Single declarative SSOT manifest + a deterministic Python install engine +
a manual README/structured-file-driven update agent that proposes manifest
changes as a reviewed PR. (Brainstorming decision: option D — full redesign.)

Non-goals (YAGNI): strict sha pinning, scheduled cron refresh, automatic
plugin discovery, any GUI.

## Decisions

- **Engine**: single Python orchestrator + a method-enum handler registry
  (A+C). PowerShell/bash shrink to ~15-line bootstrap wrappers.
- **Update agent**: manual trigger, emits a manifest-diff PR only — never
  installs. Human reviews and merges.
- **Source of truth for refresh**: structured files first
  (`.claude-plugin/marketplace.json`, `plugin.json`, Codex `hosts/` adapters),
  README only to supplement non-structured steps (external CLI / build).
- **Version policy**: float + observed record. Install always takes the
  current marketplace snapshot; the manifest records the last observed
  version/sha for drift detection only (CLIs do not support sha-pinned
  installs).
- **Manifest format**: JSON (stdlib read+write, agent-editable, no extra dep).
  Comments via `_note` fields.

## Architecture

```
                    manifest/plugins.json   (SSOT)
                         |
        +----------------+-----------------+
        |                |                 |
   [install]         [refresh]          [docs]
        |                |
  install_plugins.py  refresh-plugins skill
  (Python engine)     reads each repo's structured files
        |             (+ README supplement) -> manifest diff PR
  lib/methods.py      (no install)
  method registry
        |
  lib/glue helpers (tested, single home)
```

### Components

| Component | Role | Notes |
|---|---|---|
| `manifest/plugins.json` | All plugin declarations (SSOT) | Replaces both `*-plugins.json` |
| `scripts/install_plugins.py` | Read manifest, run method handlers | New; calls CLIs via subprocess |
| `scripts/lib/methods.py` | method enum -> handler functions | All glue lives behind here |
| `scripts/lib/glue.py` | tested env helpers | bom_safe_copy, pip_mode, etc. |
| `scripts/apply.py` | file placement + MCP/config merge | **Unchanged** (already deterministic, cross-platform) |
| `refresh-plugins` skill | read repos, emit manifest diff PR | New; manual trigger |

`install.ps1` / `install.sh` shrink to: deps check, secrets export, then
`python apply.py` + `python install_plugins.py` + `apply-ko-desc.py`.

`capture.py` / `sync.py` stay as-is (live->repo mirror). The manifest is NOT a
capture target — it is hand/agent-maintained SSOT.

## Manifest schema (`ai-agent-config/plugins v1`)

Each plugin has an `install[]` array; one entry per host/method. The
drift-prone registered marketplace name and plugin id are explicit fields.

```json
{
  "_schema": "ai-agent-config/plugins v1",
  "plugins": [
    {
      "id": "reply-trace",
      "repo": "akashi-ueda/reply-trace",
      "_note": "response disclosure footer",
      "observed": { "version": "0.1.0", "checked": "2026-06-05" },
      "install": [
        { "method": "claude_marketplace",
          "source": "akashi-ueda/reply-trace",
          "marketplace": "reply-trace",
          "plugin": "reply-trace" },
        { "method": "codex_local",
          "wrapper": "codex/reply-trace-plugin",
          "plugin_json": "codex/plugin-json/reply-trace.json",
          "marketplace": "personal" }
      ]
    },
    {
      "id": "gstack",
      "repo": "garrytan/gstack",
      "observed": { "version": "0.1.0", "checked": "2026-06-05" },
      "install": [
        { "method": "claude_local", "marketplace": "personal-local", "plugin": "gstack" },
        { "method": "built_binary",
          "clone": "https://github.com/garrytan/gstack",
          "dest": "~/.gstack/core", "builder": "bun", "needs": ["bash"] },
        { "method": "codex_local",
          "wrapper_from_build": "~/.gstack/core/.agents/skills",
          "wrapper_fallback": "claude/personal-local/plugins/gstack/skills",
          "plugin_json": "codex/plugin-json/gstack.json",
          "path_rewrite": true,
          "marketplace": "personal" }
      ]
    },
    {
      "id": "superpowers",
      "repo": "anthropics/claude-plugins-official",
      "observed": { "version": "5.1.0", "checked": "2026-06-05" },
      "install": [
        { "method": "claude_marketplace", "source": "anthropics/claude-plugins-official",
          "marketplace": "claude-plugins-official", "plugin": "superpowers" },
        { "method": "codex_store", "marketplace": "openai-curated", "plugin": "superpowers" }
      ]
    }
  ]
}
```

Field rules:
- `id` — logical name. `repo` — source the refresh agent reads.
- `install[]` — ordered; array order = execution order (implicit deps, e.g.
  gstack `built_binary` before `codex_local`). Handlers also guard on
  preconditions (build output present).
- `observed` — drift record only (float policy; not install-enforced).
- `_note` — comment substitute.

Full plugin set to migrate (8): harness, caveman, superpowers, codex,
gstack, mattpocock-skills, graphify, reply-trace.

## Method handler registry (`scripts/lib/methods.py`)

```python
HANDLERS = {
  "claude_marketplace": h_claude_marketplace,
  "claude_local":       h_claude_local,
  "codex_store":        h_codex_store,
  "codex_local":        h_codex_local,
  "external_cli":       h_external_cli,
  "built_binary":       h_built_binary,
}
```

| method | Action | Glue used |
|---|---|---|
| `claude_marketplace` | `marketplace add <source>` -> `install <plugin>@<marketplace>` -> `enable`; ignore benign "already" stderr | idempotent_cli |
| `claude_local` | `install <plugin>@personal-local` -> enable. **Wrapper/skill content is NOT manifest-driven** — `apply.py` owns placing `claude/personal-local` wholesale; this method only does CLI registration | idempotent_cli |
| `codex_store` | `codex plugin add <plugin>@<marketplace>` | idempotent_cli |
| `codex_local` | wrapper -> `~/.codex/plugins/<id>` BOM-safe copy; strip `.claude-plugin`, create `.codex-plugin`; place plugin.json; upsert personal marketplace.json entry; `codex plugin add <id>@personal`. If `path_rewrite`, rewrite SKILL.md paths as BOM-less UTF-8 | bom_safe_copy, path_rewrite, codex_marketplace_upsert |
| `external_cli` | `pip` install with `python -m pip` fallback; make shim from versioned user Scripts | pip_install, make_shim |
| `built_binary` | clone if missing -> run builder (bun). If `needs:[bash]`, prepend Git `usr\bin` to PATH; if absent, warn + skip (fallback) | ensure_bash, run_builder |

### Glue helpers (`scripts/lib/glue.py`, unit-tested)

- `idempotent_cli(cmd)` — treat "already enabled/installed" stderr as success;
  never aborts the run.
- `bom_safe_copy` / `path_rewrite` — read/write BOM-less UTF-8 (fix the BOM +
  mojibake + greedy `$_ROOT` rewrite bugs).
- `pip_install` — fall back to `python -m pip` when no standalone pip.
- `make_shim` — resolve user Scripts via `sysconfig.get_path('scripts','nt_user')`
  (versioned dir).
- `ensure_bash` — detect Git bash on Windows.
- `codex_marketplace_upsert` — ensure plugin entry exists in personal
  marketplace.json (fix the missing-attribution-entry bug).

OS branching lives only inside helpers; method handlers and the manifest are
OS-agnostic. The host scripts call none of this.

## Install engine flow (`scripts/install_plugins.py`)

```
1. load + validate_manifest(plugins.json)         # fail fast on bad manifest
2. ctx = { os, home, repo, claude_bin, codex_bin, python, pip_mode, dry_run }
3. for plugin in plugins:
     for action in plugin.install:
       handler = HANDLERS[action.method]
       try: handler(action, ctx)
       except StepError as e: collect(e); continue   # one failure != abort all
4. detect_orphans(manifest, live)                  # report; uninstall iff --prune
5. print summary table (plugin x method x ok/skip/fail/orphan)
6. exit 1 if any hard-fail (skip/orphan count as 0)
```

Flags: `--dry-run` (plan only, no CLI calls), `--only <id>`, `--host claude|codex`,
`--prune` (see Reconcile below).

Manifest is loaded through `validate_manifest()` before any action:
- `_schema` matches the expected version.
- Each plugin has `id`, `repo`, non-empty `install[]`.
- Every action's `method` exists in `HANDLERS`.
- Referenced repo-relative paths (`wrapper`, `plugin_json`, `wrapper_fallback`)
  exist on disk.
A validation failure aborts before any CLI call (fail fast, not mid-run).

### Reconcile / prune (orphan handling)

The manifest is the SSOT for *what should be installed*, but installs are
additive — removing a plugin from the manifest does not uninstall it from the
live host. (Observed in practice: after the `attribution` -> `reply-trace`
rename, the stale Codex `attribution` plugin lingered and had to be removed by
hand.)

- Default run: detect **orphans** — plugins present in the live host's managed
  scope (Claude user plugins, Codex `personal` marketplace) but absent from the
  manifest — and print them in the summary as `orphan` rows. No deletion.
- `--prune`: additionally uninstall the detected orphans
  (`claude plugin uninstall`, `codex plugin remove`). Opt-in only; never
  automatic, because deletion is destructive.

The `refresh-plugins` skill also reports orphans in its PR description so drift
is visible during review.

### Thin orchestration (`install.ps1` / `install.sh`, ~15 lines)

```
1. deps check (git/node/claude/codex/python)   # warn
2. secrets: .env or ~/.config/github-mcp/env -> export + write shared file
3. python scripts/apply.py            # file placement + MCP/config merge (existing)
4. python scripts/install_plugins.py  # plugin install (new engine)
5. python ~/.claude/tools/apply-ko-desc.py   # korean descriptions
```

All per-plugin logic, lists, and glue removed from the host scripts.

## Refresh agent (`refresh-plugins` skill)

Claude skill under `claude/personal-local/plugins/`. Manual trigger. Never
installs — emits a manifest-diff PR only.

```
/refresh-plugins
  1. load manifest/plugins.json
  2. for plugin: read repo structured files first
       - .claude-plugin/marketplace.json -> registered marketplace name, plugin id, version
       - plugins/<id>/.claude-plugin/plugin.json -> version
       - hosts/codex/* -> Codex adapter identifiers
     supplement with README (prose) only for external CLI / build step changes
  3. diff vs manifest -> classify drift:
       - identifier change (marketplace / plugin id)   <- critical (reply-trace class)
       - version bump                                  <- update observed
       - new install step (README)                     <- flag for review
  4. detect orphans (live managed plugins absent from manifest)
  5. if drift or orphans: edit manifest, write summary report (incl. orphan
     list flagged for manual prune), branch + commit + PR (gh)
  6. if none: report "all current", no change
```

Repo reads via the `github` MCP or `gh api` (raw file fetch; no clone).

Safety:
- Agent edits manifest **data** only; never code/handlers.
- Never executes README commands (e.g. `curl | bash`) — flags them for manual
  review in the report.
- Identifier changes spelled out before->after in the PR description.
- Scope limited to plugins already in the manifest; adding new plugins is a
  human edit.

Later (out of scope now): wrap this skill in `loop`/cron for periodic refresh.

## Migration / rollout

```
P1. Write plugins.json from current install.ps1/sh + manifests (8 plugins).
    Do not touch apply.py / capture.py / sync.py.
P2. Write lib/glue.py helpers + unit tests; port existing ps1/sh logic 1:1
    (including the just-fixed bugs).
P3. Write install_plugins.py. Compare `--dry-run` against current ps1 behavior.
P4. Replace install.ps1/sh with ~15-line bootstrap; remove old plugin logic.
P5. Write refresh-plugins skill.
P6. Delete manifest/claude-plugins.json + codex-plugins.json; update README,
    CLAUDE.md, AGENTS.md.
```

Each phase ends with live verification + a commit. Up to P4 the old scripts keep
working (easy rollback).

## Testing / verification

Gate at P3 and P4:
- `install_plugins.py --dry-run` plan matches the current 8-plugin x host map.
- After a real run: `claude plugin list` shows 8 enabled; `codex plugin list`
  shows personal 4 + superpowers; gstack SKILL.md has **no BOM** (starts `---`);
  graphify shim present; reply-trace on both hosts.
- Idempotent: a second run does not abort and yields the same state.
- Partial runs work (`--only gstack --dry-run`).

Unit tests:

| helper | cases |
|---|---|
| bom_safe_copy / path_rewrite | no BOM added, em-dash preserved, `$_ROOT` not mangled |
| pip_mode | picks `python -m pip` when no standalone pip |
| make_shim | resolves nt_user versioned Scripts dir |
| codex_marketplace_upsert | adds entry when missing, no duplicates |
| idempotent_cli | "already" stderr treated as success |
| validate_manifest | rejects unknown method, missing field, bad path |
| detect_orphans | live-but-not-in-manifest flagged; `--prune` removes |

## Risks / mitigations

- Codex `os error 5` (cache-backup lock) — handler retries once.
- Machine without bun/bash — built_binary skips + fallback copy (current behavior).
- Refresh agent misreads — absorbed by the PR review gate.
