#!/usr/bin/env python
"""Apply repo (SSOT) -> live Claude/Codex config. Cross-platform (Windows/macOS).

Does the file-level work: load .env, render templates + substitute secrets,
place files, merge MCP defs into ~/.claude.json, merge portable Codex keys into
~/.codex/config.toml (preserving machine-specific sections).

Plugin (re)install and verification are handled by the install.ps1/install.sh
wrapper (they need the claude/codex CLIs).

Usage: python scripts/apply.py [--dry-run]
"""
import json, os, re, shutil, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HOME = Path.home()
CLAUDE = HOME / ".claude"
CODEX = HOME / ".codex"
DRY = "--dry-run" in sys.argv

def log(msg): print(("[dry] " if DRY else "[apply] ") + msg)

def load_env():
    env = {}
    f = REPO / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            v = v.strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]  # strip surrounding quotes (needed for paths with spaces)
            env[k.strip()] = v
    # fall back to process env
    for k in ("GITHUB_PERSONAL_ACCESS_TOKEN",):
        env.setdefault(k, os.environ.get(k, ""))
    return env

def python_exe():
    # interpreter that will run the Codex hook on THIS machine
    return sys.executable.replace("\\", "/")

def subst(text, vars):
    for k, v in vars.items():
        text = text.replace("{{" + k + "}}", v)
    return text

def subst_obj(o, vars):
    if isinstance(o, str):
        return subst(o, vars)
    if isinstance(o, list):
        return [subst_obj(x, vars) for x in o]
    if isinstance(o, dict):
        return {k: subst_obj(v, vars) for k, v in o.items()}
    return o

def render_json(path: Path, vars):
    """Load JSON (placeholders are valid JSON strings), substitute in string
    values, return obj. json.dump later escapes backslashes correctly."""
    return subst_obj(json.loads(path.read_text(encoding="utf-8")), vars)

def write(path: Path, content: str):
    log(f"write {path}")
    if DRY:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def copy(src: Path, dst: Path):
    log(f"copy {src.name} -> {dst}")
    if DRY:
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)

def copytree(src: Path, dst: Path):
    log(f"copytree {src} -> {dst}")
    if DRY:
        return
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)

def merge_claude_mcp(vars):
    live = CLAUDE.parent / ".claude.json"   # ~/.claude.json
    portable = render_json(REPO / "claude/mcp.portable.json", vars)
    portable.pop("_comment", None)
    data = {}
    if live.exists():
        data = json.loads(live.read_text(encoding="utf-8"))
    data.setdefault("mcpServers", {})
    for name, cfg in portable.items():
        data["mcpServers"][name] = cfg
    log(f"merge {len(portable)} MCP servers -> {live}")
    if not DRY:
        live.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

# Codex config.toml: replace the portable top-level tables/keys, keep the rest.
PORTABLE_KEYS = {"model", "model_reasoning_effort", "personality"}
PORTABLE_TABLES = ("features", "mcp_servers.openaiDeveloperDocs", "mcp_servers.anthropicDocs",
                   "mcp_servers.microsoftLearn", "mcp_servers.github", "mcp_servers.github.http_headers",
                   "desktop", "memories")

def _table_header(line):
    m = re.match(r"^\s*\[+([^\]]+)\]+\s*$", line)
    return m.group(1).strip() if m else None

def merge_codex_config(vars):
    live = CODEX / "config.toml"
    portable_text = subst((REPO / "codex/config.portable.toml").read_text(encoding="utf-8"), vars)
    if not live.exists():
        write(live, portable_text)
        return
    lines = live.read_text(encoding="utf-8").splitlines()
    out, skip = [], False
    for line in lines:
        hdr = _table_header(line)
        key = line.split("=", 1)[0].strip() if ("=" in line and not line.strip().startswith("#")) else None
        if hdr is not None:
            skip = hdr in PORTABLE_TABLES
            if skip:
                continue
        elif skip:
            continue  # inside a skipped table
        elif key in PORTABLE_KEYS:
            continue  # drop top-level portable scalar (re-added from portable block)
        out.append(line)
    # strip trailing blanks, append portable block
    while out and out[-1].strip() == "":
        out.pop()
    merged = "\n".join(out) + "\n\n# >>> ai-agent-config portable (managed) >>>\n" + portable_text.rstrip() + "\n# <<< ai-agent-config portable <<<\n"
    log(f"merge portable keys -> {live}")
    if not DRY:
        live.write_text(merged, encoding="utf-8")

def main():
    env = load_env()
    vars = {
        "PYTHON": python_exe(),
        "CODEX_HOME": str(CODEX).replace("\\", "/"),
        "CLAUDE_HOME": str(CLAUDE).replace("\\", "/"),
    }
    # --- Claude authored files ---
    copy(REPO / "claude/CLAUDE.md", CLAUDE / "CLAUDE.md")
    # settings.json: render {{CLAUDE_HOME}} via parsed JSON (escape-safe)
    log(f"render settings.json -> {CLAUDE / 'settings.json'}")
    if not DRY:
        (CLAUDE / "settings.json").write_text(
            json.dumps(render_json(REPO / "claude/settings.json", vars), indent=2, ensure_ascii=False),
            encoding="utf-8")
    for t in (REPO / "claude/tools").glob("*"):
        if t.is_file():
            copy(t, CLAUDE / "tools" / t.name)
    # personal-local wrapper marketplace (CLI install done by wrapper)
    copytree(REPO / "claude/personal-local", CLAUDE / "plugins/marketplaces/personal-local")
    # --- Codex authored files ---
    copy(REPO / "codex/AGENTS.md", CODEX / "AGENTS.md")
    copy(REPO / "codex/hooks/caveman.py", CODEX / "hooks/caveman.py")
    write(CODEX / "hooks.json", subst((REPO / "codex/hooks.json.tmpl").read_text(encoding="utf-8"), vars))
    # --- merges ---
    merge_claude_mcp(vars)
    merge_codex_config(vars)
    log("file apply done. Run plugin reinstall + verify via install wrapper.")

if __name__ == "__main__":
    main()
