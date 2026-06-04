#!/usr/bin/env bash
# Apply ai-agent-config -> live Claude/Codex (macOS/Linux). Idempotent.
set -euo pipefail
REPO="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO"

echo "== ai-agent-config install (pull/apply) =="

# 1) deps check (warn only)
pick_cmd() {
  command -v "$1" >/dev/null 2>&1 && { printf '%s\n' "$1"; return 0; }
  command -v "$2" >/dev/null 2>&1 && { printf '%s\n' "$2"; return 0; }
  return 1
}

PY_BIN="$(pick_cmd python python3 || true)"
PIP_BIN="$(pick_cmd pip pip3 || true)"
export PATH="$HOME/.local/bin:$PATH"

run_claude() {
  claude "$@"
}

missing=0
for c in git node claude codex; do
  command -v "$c" >/dev/null 2>&1 || { echo "  ERROR: '$c' not found on PATH"; missing=1; }
done
[ -n "$PY_BIN" ] || { echo "  ERROR: 'python'/'python3' not found on PATH"; missing=1; }
[ -n "$PIP_BIN" ] || { echo "  ERROR: 'pip'/'pip3' not found on PATH"; missing=1; }
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
  printf '\n# ai-agent-config: GitHub MCP shared token\n[ -f "$HOME/.config/github-mcp/env" ] && . "$HOME/.config/github-mcp/env"\n' >> "$RC"
}

# 3) file apply (render + place + merge MCP/config)
"${PY_BIN:-python}" scripts/apply.py

# 4) plugins (Claude)
run_claude plugin marketplace add revfactory/harness        2>/dev/null || true
run_claude plugin marketplace add JuliusBrussee/caveman     2>/dev/null || true
run_claude plugin marketplace add anthropics/claude-plugins-official 2>/dev/null || true
run_claude plugin marketplace add openai/codex-plugin-cc    2>/dev/null || true
run_claude plugin marketplace add akashi-ueda/agent-attribution 2>/dev/null || true
run_claude plugin marketplace add "$REPO/claude/personal-local" 2>/dev/null || true
for p in \
  harness@harness-marketplace \
  caveman@caveman \
  superpowers@claude-plugins-official \
  codex@openai-codex \
  gstack@personal-local \
  mattpocock-skills@personal-local \
  graphify@personal-local \
  attribution@agent-attribution
do
  run_claude plugin install "$p" 2>/dev/null || true
  run_claude plugin enable "$p" 2>/dev/null || true
done

# 5) external CLIs/binaries only. Do not register standalone agent skills.
if ! command -v graphify >/dev/null 2>&1; then
  if [ -n "$PIP_BIN" ]; then
    "$PIP_BIN" install --user graphifyy || "$PIP_BIN" install --user --break-system-packages graphifyy || true
  fi
  if ! command -v graphify >/dev/null 2>&1 && [ -n "$PY_BIN" ]; then
    PY_USER_BASE="$("$PY_BIN" -m site --user-base 2>/dev/null || true)"
    if [ -n "$PY_USER_BASE" ] && [ -x "$PY_USER_BASE/bin/graphify" ]; then
      mkdir -p "$HOME/.local/bin"
      ln -sf "$PY_USER_BASE/bin/graphify" "$HOME/.local/bin/graphify"
    fi
  fi
fi
# gstack core lives outside every agent's skills dir. Plugin skills resolve bins from here.
if command -v bun >/dev/null 2>&1; then
  GS_CORE="$HOME/.gstack/core"
  [ -d "$GS_CORE/.git" ] || [ -d "$GS_CORE/browse" ] || git clone --depth 1 https://github.com/garrytan/gstack "$GS_CORE"
  ( cd "$GS_CORE" && (bun install --frozen-lockfile 2>/dev/null || bun install) ) || true
  ( cd "$GS_CORE" && bun run build ) || true
fi

sync_codex_plugin() {
  local name="$1"
  local src="$2"
  local dst="$HOME/.codex/plugins/$name"
  rm -rf "$dst"
  mkdir -p "$dst"
  cp -R "$src"/. "$dst"/
  rm -rf "$dst/.claude-plugin"
  mkdir -p "$dst/.codex-plugin"
}

sync_codex_gstack_plugin() {
  local dst="$HOME/.codex/plugins/gstack"
  rm -rf "$dst"
  mkdir -p "$dst/.codex-plugin" "$dst/skills"
  if [ -d "$HOME/.gstack/core/.agents/skills" ]; then
    cp -R "$HOME/.gstack/core/.agents/skills"/. "$dst/skills"/
    while IFS= read -r -d '' f; do
      perl -0pi -e 's#\$HOME/\.codex/skills/gstack#\$HOME/.gstack/core#g; s#\$HOME/\.agents/skills/gstack#\$HOME/.gstack/core#g; s#\.agents/skills/gstack#\$HOME/.gstack/core#g' "$f"
    done < <(find "$dst/skills" -type f -name 'SKILL.md' -print0)
  else
    cp -R "$REPO/claude/personal-local/plugins/gstack/skills"/. "$dst/skills"/
  fi
}

# 6) Codex plugins. Store plugins come from OpenAI-curated; local wrappers go through personal marketplace.
mkdir -p "$HOME/.agents/plugins" "$HOME/.codex/plugins"
cp "$REPO/codex/personal-marketplace.json" "$HOME/.agents/plugins/marketplace.json"
sync_codex_gstack_plugin
cp "$REPO/codex/plugin-json/gstack.json" "$HOME/.codex/plugins/gstack/.codex-plugin/plugin.json"
sync_codex_plugin mattpocock-skills "$REPO/claude/personal-local/plugins/mattpocock-skills"
cp "$REPO/codex/plugin-json/mattpocock-skills.json" "$HOME/.codex/plugins/mattpocock-skills/.codex-plugin/plugin.json"
sync_codex_plugin graphify "$REPO/claude/personal-local/plugins/graphify"
cp "$REPO/codex/plugin-json/graphify.json" "$HOME/.codex/plugins/graphify/.codex-plugin/plugin.json"
sync_codex_plugin attribution "$REPO/codex/attribution-plugin"
cp "$REPO/codex/plugin-json/attribution.json" "$HOME/.codex/plugins/attribution/.codex-plugin/plugin.json"
codex plugin add superpowers@openai-curated 2>/dev/null || true
codex plugin add gstack@personal 2>/dev/null || true
codex plugin add mattpocock-skills@personal 2>/dev/null || true
codex plugin add graphify@personal 2>/dev/null || true
codex plugin add attribution@personal 2>/dev/null || true

# 7) korean descriptions
"${PY_BIN:-python}" "$HOME/.claude/tools/apply-ko-desc.py" || true
"${PY_BIN:-python}" "$REPO/scripts/auto_capture.py" --prime || true

# 8) verify
echo "== verify =="
run_claude plugin list 2>/dev/null | grep -E "@|enabled" || true
echo "Done. Restart Claude Code and Codex. Approve the Codex global hook trust prompt on first run."
