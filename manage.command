#!/bin/bash
# One-click menu for personal-agent-config (macOS). Double-click in Finder or run.
# Reset options back up the managed config first and keep auth/history;
# reset.py prompts for confirmation before deleting anything.
cd "$(dirname "$0")" || exit 1
while true; do
  cat <<'MENU'

 personal-agent-config
 =====================
  1. Install all (Claude + Codex)
  2. Install Claude only
  3. Install Codex only
  4. Reset Claude (keep auth/history) + reinstall
  5. Reset Codex (keep auth/history) + reinstall
  6. Reset all + reinstall
  0. Exit
MENU
  read -r -p "Select [0-6]: " choice
  case "$choice" in
    1) ./install.sh; break;;
    2) ./install.sh --host claude; break;;
    3) ./install.sh --host codex; break;;
    4) ./install.sh --host claude --reset; break;;
    5) ./install.sh --host codex --reset; break;;
    6) ./install.sh --reset; break;;
    0) break;;
    *) echo "Invalid choice.";;
  esac
done
echo
echo "== finished (exit code $?) =="
read -n1 -r -p "Press any key to close..."
echo
