#!/usr/bin/env python
"""Codex caveman-mode injector for plugin-bundled hooks."""
import json
import sys

event = sys.argv[1] if len(sys.argv) > 1 else "UserPromptSubmit"
text = (
    "CAVEMAN MODE ACTIVE. Default response = caveman compression: drop "
    "articles/filler/pleasantries/hedging, fragments OK, short synonyms, keep "
    "full technical accuracy. Exact commands/paths/identifiers/errors. Relax "
    "compression for security warnings, destructive or high-risk actions, "
    "complex multi-step procedures, or when the user asks for detail, teaching, "
    "brainstorming, or normal mode. Deactivate on 'normal mode' or 'stop caveman'."
)
print(json.dumps({
    "hookSpecificOutput": {"hookEventName": event, "additionalContext": text}
}))
sys.exit(0)
