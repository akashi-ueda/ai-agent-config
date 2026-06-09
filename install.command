#!/bin/bash
# One-click installer for personal-agent-config (macOS).
# Double-click in Finder, or run from a terminal. Prereqs still apply:
# git, node, claude, codex, python on PATH + .env with the token filled.
cd "$(dirname "$0")" || exit 1
./install.sh
status=$?
echo
echo "== install.sh finished (exit code $status) =="
read -n1 -r -p "Press any key to close..."
echo
