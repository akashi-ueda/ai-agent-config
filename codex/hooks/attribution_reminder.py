#!/usr/bin/env python3
"""UserPromptSubmit hook for the `attribution` plugin.

Re-injects a short reminder each turn so the agent keeps ending replies with the
attribution footer (skills / MCP tools / hooks it auto-used). The hook never
writes the footer itself — only the agent knows what it actually used — it just
reinforces the rule and passes through the active configuration.

Output goes to stdout, which the host adds to the prompt context.

Config (all optional, read from the environment):
  AGENT_ATTRIBUTION_DISABLE  set to 1/true/on/yes -> emit nothing
  AGENT_ATTRIBUTION_LABEL    custom footer label (overrides locale default)
  AGENT_ATTRIBUTION_LOCALE   en (default) | ko | <other>
"""
from __future__ import annotations

import os
import sys

# Built-in locale presets: locale -> (label, skills, mcp, hooks)
LOCALES = {
    "en": ("Auto-used", "skills", "MCP", "hooks"),
    "ko": ("사용한 자동 트리거", "스킬", "MCP", "훅"),
}


def truthy(value: str) -> bool:
    return value.strip().lower() in ("1", "true", "on", "yes")


def main() -> int:
    if truthy(os.environ.get("AGENT_ATTRIBUTION_DISABLE", "")):
        return 0

    locale = os.environ.get("AGENT_ATTRIBUTION_LOCALE", "en").strip() or "en"
    label_default, c_skills, c_mcp, c_hooks = LOCALES.get(locale, LOCALES["en"])
    label = os.environ.get("AGENT_ATTRIBUTION_LABEL", "").strip() or label_default

    lang_note = "" if locale == "en" else f" Write category names and hook roles in locale '{locale}'."

    msg = (
        "[attribution] If this turn you invoked any skill, called any MCP tool, "
        "or a hook fired on your behalf, end your reply with ONE last line:\n"
        f"  {label} — {c_skills}: <skill>[, ...]; {c_mcp}: <server>/<tool>[, ...]; "
        f"{c_hooks}: <name> (<role>)[, ...]\n"
        "Omit empty categories; omit the whole line if nothing was auto-used. "
        "Do not count plain built-in tools (Read/Edit/Bash) unless a hook fired around them."
        + lang_note
    )
    print(msg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
