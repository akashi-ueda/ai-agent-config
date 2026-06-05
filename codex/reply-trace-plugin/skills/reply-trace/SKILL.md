---
name: reply-trace
description: "End each reply with a one-line disclosure of the plugins, skills, MCP tools, subagents, and hooks you used this turn. Use whenever you invoke a plugin/skill, call an MCP tool, spawn a subagent, or a hook fires on your behalf — append the footer as the last line. Omit empty categories and omit the line entirely when nothing was used."
---

# Reply Trace footer

Append a single disclosure line as the **last line** of your reply whenever you
used any of: a **plugin**, **skill**, **MCP tool**, **subagent**, or **hook**
during this turn. This makes agent behavior transparent to the user.

A companion `UserPromptSubmit` hook re-injects a short reminder every turn so the
rule does not drift over a long session. The hook only reminds — **you** write
the line, because only you know what you actually used.

## When to emit

Emit the footer when, during the current turn, you:

- invoked a plugin or host extension,
- invoked a skill (including plugin-namespaced skills, e.g. `caveman:caveman`),
- called an MCP tool (`mcp__<server>__<tool>`), or
- spawned a subagent or delegated work to another agent, or
- a hook acted on your behalf (e.g. a `PreToolUse` gate, a capture-on-stop hook).

Do **not** count: plain built-in tools the user can see you using (Read, Edit,
Bash, etc.), unless a hook fired around them. If nothing in the list above
happened, **omit the line completely** — never print an empty footer.

## Format

One line, last in the reply. Default label is `Auto-used`. Categories appear in
this order, each omitted when empty:

```
Auto-used — plugins: <plugin>[, <plugin>...]; skills: <skill>[, <skill>...]; MCP: <server>/<tool>[, ...]; subagents: <name> (<role>)[, ...]; hooks: <name> (<role>)[, ...]
```

- **plugins**: host/plugin id when a plugin or extension was explicitly used.
- **skills**: the skill id you invoked. Use the namespaced id when it has one.
- **MCP**: `<server>/<tool>` for each MCP tool called (dedupe repeats).
- **subagents**: subagent name + short role in parentheses.
- **hooks**: hook name + a short role in parentheses, e.g.
  `auto-capture (mirrors live config to the repo)`.

### Examples

```
Auto-used — plugins: Browser; skills: browser:control-in-app-browser
```
```
Auto-used — MCP: anthropicDocs/search_docs, github/list_issues; hooks: pre_tool_use (checks command policy)
```
```
Auto-used — skills: superpowers:brainstorming; subagents: reviewer (checks diff); hooks: stop (runs a review gate before finishing)
```

## Configuration

The hook reads these environment variables (all optional) and tells you which to
apply via its per-turn reminder:

- `REPLY_TRACE_LABEL` — replace the `Auto-used` label (e.g. `사용한 자동 트리거`).
- `REPLY_TRACE_LOCALE` — `en` (default), `ko`, `ja`, or another locale. When non-`en`,
  write the category names, subagent roles, and hook roles in that language but keep the same
  structure. Built-in locale `ko` maps to label `사용한 자동 트리거` and category
  words `플러그인`/`스킬`/`MCP`/`서브에이전트`/`훅`.
- `REPLY_TRACE_DISABLE` — when set (`1`/`true`), suppress the footer
  entirely for that environment.

Legacy `AGENT_ATTRIBUTION_*` names are accepted as fallbacks.

### Locale `ko` example

```
사용한 자동 트리거 — 플러그인: Browser; 스킬: browser:control-in-app-browser; MCP: anthropicDocs/search_docs; 서브에이전트: reviewer (diff 검토); 훅: pre_tool_use (명령 정책 확인)
```

## Rules of thumb

- Exactly one line, always last, no blank line padding.
- Omit empty categories; omit the whole line when nothing was auto-used.
- Be honest: list only what you actually used this turn, deduped.
