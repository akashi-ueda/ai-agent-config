#!/usr/bin/env python3
"""Prompt-time reminder hook for the `reply-trace` plugin.

Re-injects a short reminder each turn so the agent keeps ending replies with the
reply trace footer (plugins / skills / MCP tools / subagents / hooks it used).
The hook never writes the footer itself — only the agent knows what it actually used — it just
reinforces the rule and passes through the active configuration.

Output goes to stdout, which the host adds to the prompt context.

Config (all optional, read from the environment):
  REPLY_TRACE_DISABLE  set to 1/true/on/yes -> emit nothing
  REPLY_TRACE_LABEL    custom footer label (overrides locale default)
  REPLY_TRACE_LOCALE   en (default) | ko | ja | <other>

Legacy AGENT_ATTRIBUTION_* names are still accepted as fallbacks.
"""
from __future__ import annotations

import os

# Built-in locale presets:
# locale -> (label, plugins, skills, mcp, subagents, hooks)
LOCALES = {
    "en": ("Auto-used", "plugins", "skills", "MCP", "subagents", "hooks"),
    "ko": ("사용한 자동 트리거", "플러그인", "스킬", "MCP", "서브에이전트", "훅"),
    "ja": ("使用した自動トリガー", "プラグイン", "スキル", "MCP", "サブエージェント", "フック"),
}


def truthy(value: str) -> bool:
    return value.strip().lower() in ("1", "true", "on", "yes")


def env(name: str, legacy_name: str = "") -> str:
    value = os.environ.get(name, "")
    if value:
        return value
    return os.environ.get(legacy_name, "") if legacy_name else ""


def main() -> int:
    if truthy(env("REPLY_TRACE_DISABLE", "AGENT_ATTRIBUTION_DISABLE")):
        return 0

    locale = env("REPLY_TRACE_LOCALE", "AGENT_ATTRIBUTION_LOCALE").strip() or "en"
    label_default, c_plugins, c_skills, c_mcp, c_subagents, c_hooks = LOCALES.get(locale, LOCALES["en"])
    label = env("REPLY_TRACE_LABEL", "AGENT_ATTRIBUTION_LABEL").strip() or label_default

    lang_note = "" if locale == "en" else f" Write category names and hook roles in locale '{locale}'."

    msg = (
        "[reply-trace] If this turn you invoked any plugin/skill, called any MCP tool, "
        "spawned any subagent, or a hook fired on your behalf, end your reply with ONE last line:\n"
        f"  {label} — {c_plugins}: <plugin>[, ...]; {c_skills}: <skill>[, ...]; "
        f"{c_mcp}: <server>/<tool>[, ...]; {c_subagents}: <name> (<role>)[, ...]; "
        f"{c_hooks}: <name> (<role>)[, ...]\n"
        "Omit empty categories; omit the whole line if nothing was auto-used. "
        "Do not count plain built-in tools unless an adapter, plugin, MCP tool, subagent, or hook was involved."
        + lang_note
    )
    print(msg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
