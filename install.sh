#!/usr/bin/env bash
# Apply personal-agent-config -> live Claude/Codex (macOS/Linux). Idempotent.
set -euo pipefail
REPO="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO"

echo "== personal-agent-config install (pull/apply) =="

# 1) deps check (warn only)
pick_cmd() {
  command -v "$1" >/dev/null 2>&1 && { printf '%s\n' "$1"; return 0; }
  command -v "$2" >/dev/null 2>&1 && { printf '%s\n' "$2"; return 0; }
  return 1
}

PY_BIN="$(pick_cmd python python3 || true)"
PIP_BIN="$(pick_cmd pip pip3 || true)"
export PATH="$HOME/.local/bin:$PATH"

# pip fallback: accept `python -m pip` when no standalone pip exists
USE_PY_PIP=0
if [ -z "$PIP_BIN" ] && [ -n "$PY_BIN" ] && "$PY_BIN" -m pip --version >/dev/null 2>&1; then
  USE_PY_PIP=1
fi
run_pip() { if [ "$USE_PY_PIP" -eq 1 ]; then "$PY_BIN" -m pip "$@"; else "$PIP_BIN" "$@"; fi; }

missing=0
for c in git node claude codex; do
  command -v "$c" >/dev/null 2>&1 || { echo "  ERROR: '$c' not found on PATH"; missing=1; }
done
[ -n "$PY_BIN" ] || { echo "  ERROR: 'python'/'python3' not found on PATH"; missing=1; }
[ -n "$PIP_BIN" ] || [ "$USE_PY_PIP" -eq 1 ] || { echo "  ERROR: 'pip'/'pip3' not found (and 'python -m pip' unavailable)"; missing=1; }
[ "$missing" -eq 0 ] || exit 1
command -v bun >/dev/null 2>&1 || echo "  WARN: 'bun' not found (gstack build needs it)"

# 2) secrets
GITHUB_MCP_ENV="$HOME/.config/github-mcp/env"
if [ -f .env ]; then
  set -a; . ./.env; set +a
elif [ -f "$GITHUB_MCP_ENV" ]; then
  set -a; . "$GITHUB_MCP_ENV"; set +a
else
  echo "  No .env or ~/.config/github-mcp/env -> copying .env.example. Fill it then re-run."
  cp .env.example .env
  exit 1
fi
if [ -z "${GITHUB_PERSONAL_ACCESS_TOKEN:-}" ] && [ -f "$GITHUB_MCP_ENV" ]; then
  set -a; . "$GITHUB_MCP_ENV"; set +a
fi
if [ -z "${GITHUB_PERSONAL_ACCESS_TOKEN:-}" ]; then
  echo "  ERROR: GITHUB_PERSONAL_ACCESS_TOKEN is empty"
  exit 1
fi
mkdir -p "$HOME/.config/github-mcp"
GITHUB_MCP_ENV="$GITHUB_MCP_ENV" "$PY_BIN" - <<'PY'
import os, shlex
from pathlib import Path

path = Path(os.environ["GITHUB_MCP_ENV"])
token = os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"]
path.write_text(f"export GITHUB_PERSONAL_ACCESS_TOKEN={shlex.quote(token)}\n", encoding="utf-8")
PY
chmod 600 "$GITHUB_MCP_ENV"

# zsh sources the shared GitHub MCP token file; do not persist the token inline.
RC="$HOME/.zshrc"
mkdir -p "$(dirname "$RC")"
touch "$RC"
tmp_rc="$(mktemp)"
grep -v '^export GITHUB_PERSONAL_ACCESS_TOKEN=' "$RC" > "$tmp_rc" || true
cat "$tmp_rc" > "$RC"
rm -f "$tmp_rc"
grep -qF '[ -f "$HOME/.config/github-mcp/env" ] && . "$HOME/.config/github-mcp/env"' "$RC" 2>/dev/null || {
  printf '\n# personal-agent-config: GitHub MCP shared token\n[ -f "$HOME/.config/github-mcp/env" ] && . "$HOME/.config/github-mcp/env"\n' >> "$RC"
}

# 3) file apply (place files, merge MCP/config)
"${PY_BIN:-python}" scripts/apply.py

# 4) plugin install (manifest-driven engine: both hosts, externals, builds)
"${PY_BIN:-python}" scripts/install_plugins.py

# 5) korean descriptions
"${PY_BIN:-python}" "$HOME/.claude/tools/apply-ko-desc.py" || true

# 6) verify (real install state, not just the plan)
echo "== verify =="
if ! "${PY_BIN:-python}" scripts/install_plugins.py --verify-installed; then
  echo "  ERROR: install verification failed (a manifest plugin is not installed+enabled)"
  exit 1
fi
echo "Done. Restart Claude Code and Codex. Approve the Codex global hook trust prompt on first run."
