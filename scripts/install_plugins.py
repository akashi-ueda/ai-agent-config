#!/usr/bin/env python
"""Install plugins declared in manifest/plugins.json onto Claude + Codex.

Deterministic engine: each install action dispatches to a method handler in
scripts/lib/methods.py; env glue lives in scripts/lib/glue.py. File placement
(personal-local dir, MCP/config merge) is handled separately by apply.py.

Usage:
  python scripts/install_plugins.py [--dry-run] [--only ID] [--host claude|codex] [--prune]
  python scripts/install_plugins.py --verify-installed [--host claude|codex]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from scripts.lib import glue, manifest, methods  # noqa: E402

HOST_OF_METHOD = {
    "claude_marketplace": "claude", "claude_local": "claude",
    "codex_store": "codex", "codex_local": "codex",
}
EXTERNAL_METHODS = {"external_cli", "built_binary"}


def action_hosts(a: dict) -> set:
    """Hosts an install action provisions, for --host filtering.

    Method-bound steps map by method. External (pip/build) steps declare a
    `host` in the manifest (claude|codex|both, default both): a shared CLI or
    built binary can back skills on either host, so e.g. `--host claude` still
    pulls graphify's pip CLI instead of leaving the Claude skill without it."""
    method = a["method"]
    if method in EXTERNAL_METHODS:
        h = a.get("host", "both")
        return {"claude", "codex"} if h == "both" else {h}
    return {HOST_OF_METHOD[method]}


def expected_refs(m: dict, host: str | None = None) -> dict:
    """host -> set of `plugin@marketplace` refs the manifest expects installed.

    Only method-bound steps install a plugin ref; external pip/build steps do
    not. Pure, for post-install verification."""
    refs = {"claude": set(), "codex": set()}
    for p in m["plugins"]:
        for a in p["install"]:
            h = HOST_OF_METHOD.get(a["method"])
            if h:
                refs[h].add(f'{a["plugin"]}@{a["marketplace"]}')
    return {host: refs[host]} if host else refs


def parse_claude_installed(list_output: str) -> set:
    """Enabled `plugin@marketplace` refs from `claude plugin list` block output:
    a `<marker> plugin@mk` line followed by a `Status: ... enabled` line. Pure."""
    refs, current = set(), None
    for line in list_output.splitlines():
        s = line.strip()
        mt = re.match(r"(?:\S\s+)?([\w.-]+@[\w.-]+)$", s)
        if mt:
            current = mt.group(1)
        elif current and s.startswith("Status:"):
            if "enabled" in s and "disabled" not in s:
                refs.add(current)
            current = None
    return refs


def verify_installed(ctx: methods.Ctx, m: dict, host: str | None = None) -> dict:
    """host -> set of expected refs NOT live-installed+enabled. Empty == clean.

    This is the real post-install check (vs --dry-run's plan): it parses the
    actual `plugin list` output, so a masked install failure surfaces here."""
    want = expected_refs(m, host)
    missing = {}
    if "claude" in want:
        _, out = glue.run_capture([ctx.claude, "plugin", "list"])
        live = parse_claude_installed(out)
        missing["claude"] = {r for r in want["claude"] if r not in live}
    if "codex" in want:
        _, out = glue.run_capture([ctx.codex, "plugin", "list"])
        miss = set()
        for ref in want["codex"]:
            plugin, mk = ref.split("@", 1)
            if not methods._is_installed_in_list(out, plugin, mk):
                miss.add(ref)
        missing["codex"] = miss
    return missing


def _run_verify(ctx: methods.Ctx, m: dict, host: str | None) -> int:
    missing = verify_installed(ctx, m, host)
    print("== verify installed ==")
    bad = False
    for h, refs in sorted(missing.items()):
        if refs:
            bad = True
            for r in sorted(refs):
                print(f"  MISSING {h:6} {r}")
        else:
            n = len(expected_refs(m, h)[h])
            print(f"  ok      {h:6} all {n} plugins installed+enabled")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only")
    ap.add_argument("--host", choices=["claude", "codex"])
    ap.add_argument("--prune", action="store_true")
    ap.add_argument("--verify-installed", action="store_true",
                    help="check live install state (not a plan); exit 1 if any "
                         "manifest plugin is not installed+enabled")
    args = ap.parse_args()

    m = manifest.load_manifest(REPO / "manifest/plugins.json")
    manifest.validate_manifest(m, set(methods.HANDLERS), REPO)

    ctx = methods.Ctx(repo=REPO, home=Path.home(), python=sys.executable,
                      dry_run=args.dry_run)

    if args.verify_installed:
        return _run_verify(ctx, m, args.host)

    rows = []
    for p in m["plugins"]:
        if args.only and p["id"] != args.only:
            continue
        for a in p["install"]:
            # --host limits to actions that provision that host (external steps
            # declare their host(s) in the manifest; see action_hosts).
            if args.host and args.host not in action_hosts(a):
                continue
            try:
                status = methods.HANDLERS[a["method"]](a, ctx)
            except Exception as e:  # noqa: BLE001
                status = "fail"
                print(f"  ERROR {p['id']}/{a['method']}: {e}")
            rows.append((p["id"], a["method"], status))

    print("\n== install summary ==")
    for pid, method, status in rows:
        print(f"  {status:5}  {pid:18} {method}")

    if not args.dry_run:
        # Orphan handling is scoped to the Codex `personal` marketplace, which is
        # fully ours. Claude marketplaces can hold user-installed plugins outside
        # this manifest, so we never auto-prune there.
        live = _live_codex_personal_ids(ctx)
        orphans = manifest.detect_orphans(m, live)
        for o in sorted(orphans):
            print(f"  orphan {o:18} (codex personal, not in manifest)")
        if args.prune and orphans:
            for o in sorted(orphans):
                glue.run_cli([ctx.codex, "plugin", "remove", f"{o}@personal"])

    return 1 if any(s == "fail" for _, _, s in rows) else 0


def parse_codex_personal_ids(list_output: str) -> set:
    """Plugin ids from `codex plugin list` that belong to the personal
    marketplace. Pure (testable); parsing is separated from the CLI call."""
    ids = set()
    for line in list_output.splitlines():
        if "@personal" in line:
            ids.add(line.split("@personal")[0].strip().split()[-1])
    return ids


def _live_codex_personal_ids(ctx: methods.Ctx) -> set:
    """Best-effort live ids; empty on any error (orphan check then no-ops)."""
    try:
        _, out = glue.run_capture([ctx.codex, "plugin", "list"])
        return parse_codex_personal_ids(out)
    except Exception:  # noqa: BLE001
        return set()


if __name__ == "__main__":
    raise SystemExit(main())
