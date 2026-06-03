#!/usr/bin/env bash
# Apply ai-agent-config -> live Claude/Codex (macOS/Linux). Idempotent.
set -euo pipefail
REPO="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO"

echo "== ai-agent-config install (pull/apply) =="

# 1) deps check (warn only)
for c in git python3 claude codex; do
  command -v "$c" >/dev/null 2>&1 || echo "  WARN: '$c' not found on PATH"
done
command -v uv  >/dev/null 2>&1 || echo "  WARN: 'uv' not found (graphify needs it)"
command -v bun >/dev/null 2>&1 || echo "  WARN: 'bun' not found (gstack ./setup needs it)"

# 2) secrets
if [ ! -f .env ]; then
  echo "  No .env -> copying templates/.env.example. Fill it then re-run."
  cp templates/.env.example .env
  exit 1
fi
set -a; . ./.env; set +a
# persist to shell rc (idempotent)
RC="$HOME/.zshrc"; [ -n "${BASH_VERSION:-}" ] && RC="$HOME/.bashrc"
for v in GITHUB_PERSONAL_ACCESS_TOKEN; do
  grep -q "export $v=" "$RC" 2>/dev/null || echo "export $v=\"${!v}\"" >> "$RC"
done

# 3) file apply (render + place + merge MCP/config)
python3 scripts/apply.py

# 4) plugins (Claude)
claude plugin marketplace add revfactory/harness        2>/dev/null || true
claude plugin marketplace add JuliusBrussee/caveman     2>/dev/null || true
claude plugin marketplace add "$REPO/claude/personal-local" 2>/dev/null || true
claude plugin install harness@harness-marketplace            2>/dev/null || true
claude plugin install caveman@caveman                        2>/dev/null || true
claude plugin install superpowers@claude-plugins-official    2>/dev/null || true
claude plugin install gstack@personal-local                  2>/dev/null || true
claude plugin install mattpocock-skills@personal-local       2>/dev/null || true

# 5) external installers
command -v uv >/dev/null 2>&1 && { uv tool install graphifyy || true; graphify install --platform "$(uname | grep -qi darwin && echo mac || echo linux)" || true; graphify install --platform codex || true; }
# gstack bins (OS-specific build)
if command -v bun >/dev/null 2>&1; then
  [ -d "$HOME/.claude/skills/gstack" ] || git clone --depth 1 https://github.com/garrytan/gstack "$HOME/.claude/skills/gstack"
  ( cd "$HOME/.claude/skills/gstack" && ./setup && ./setup --host codex ) || true
fi

# 6) Codex superpowers
codex plugin marketplace add obra/superpowers 2>/dev/null || true

# 7) korean descriptions
python3 "$HOME/.claude/tools/apply-ko-desc.py" || true

# 8) verify
echo "== verify =="
claude plugin list 2>/dev/null | grep -E "@|enabled" || true
echo "Done. Restart Claude Code and Codex. Approve the Codex global hook trust prompt on first run."
