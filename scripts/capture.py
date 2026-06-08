#!/usr/bin/env python
"""Capture live Claude/Codex authored config -> repo (push direction).

Copies hand-authored, portable files back into the repo and re-templatizes
machine-specific paths/secrets. Captures Claude MCP servers and portable Codex
config tables. Run manually (or via scripts/sync.py) before committing direct
live edits.

Usage: python scripts/capture.py [--dry-run]
"""
import json, re, shutil, sys
from pathlib import Path
try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11
    tomllib = None

REPO = Path(__file__).resolve().parent.parent
HOME = Path.home()
CLAUDE = HOME / ".claude"
CODEX = HOME / ".codex"
AGENTS = HOME / ".agents"
DRY = "--dry-run" in sys.argv

# MCP servers the repo manages (mirrors claude/mcp.portable.json + codex portable).
# Anything else in live ~/.claude.json is left out of capture.
MANAGED_MCP_SERVERS = {"openaiDeveloperDocs", "anthropicDocs", "microsoftLearn", "github"}

def log(m): print(("[dry] " if DRY else "[capture] ") + m)

def copy(src: Path, dst: Path):
    if not src.exists():
        log(f"skip (missing) {src}"); return
    log(f"{src} -> {dst.relative_to(REPO)}")
    if DRY: return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)

def copytree(src: Path, dst: Path):
    if not src.exists():
        log(f"skip (missing) {src}"); return
    log(f"{src} -> {dst.relative_to(REPO)} (tree)")
    if DRY: return
    if dst.exists(): shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("*.bak"))

# Secret patterns that must never be committed. ${ENV}/{{VAR}} refs are left intact.
SECRET_RE = re.compile(
    r"(ghp_[A-Za-z0-9]{20,}"
    r"|github_pat_[A-Za-z0-9_]{20,}"
    r"|gho_[A-Za-z0-9]{20,}"
    r"|sk-[A-Za-z0-9-]{20,}"
    r"|xox[baprs]-[A-Za-z0-9-]{10,}"
    r"|AKIA[0-9A-Z]{16}"
    r"|Bearer\s+(?!\$\{)(?!\{\{)[A-Za-z0-9._\-]{20,})"
)

def redact(text: str) -> str:
    """Replace inline secrets with a placeholder so capture never leaks them to git."""
    def _sub(m):
        log("WARNING: redacted a secret-looking value during capture")
        tok = m.group(0)
        return "Bearer {{REDACTED}}" if tok.lower().startswith("bearer") else "{{REDACTED}}"
    return SECRET_RE.sub(_sub, text)

def portable_text(text: str) -> str:
    pairs = [
        (str(CLAUDE).replace("\\", "\\\\"), "{{CLAUDE_HOME}}"),
        (str(CLAUDE).replace("\\", "/"), "{{CLAUDE_HOME}}"),
        (str(CODEX).replace("\\", "\\\\"), "{{CODEX_HOME}}"),
        (str(CODEX).replace("\\", "/"), "{{CODEX_HOME}}"),
        (sys.executable.replace("\\", "\\\\"), "{{PYTHON}}"),
        (sys.executable.replace("\\", "/"), "{{PYTHON}}"),
    ]
    for src, dst in pairs:
        text = text.replace(src, dst)
    # only collapse quoted *paths* (contain a separator) ending in a python binary
    text = re.sub(r'"[^"]*[\\/][^"]*python(?:\d+(?:\.\d+)*)?(?:\.exe)?"', '"{{PYTHON}}"', text, flags=re.I)
    return redact(text)

def copy_json_template(src: Path, dst: Path):
    if not src.exists():
        log(f"skip (missing) {src}"); return
    log(f"template {src} -> {dst.relative_to(REPO)}")
    if DRY: return
    dst.parent.mkdir(parents=True, exist_ok=True)
    txt = portable_text(src.read_text(encoding="utf-8"))
    dst.write_text(txt if txt.endswith("\n") else txt + "\n", encoding="utf-8")

def capture_claude_mcp():
    live = HOME / ".claude.json"
    if not live.exists():
        log(f"skip (missing) {live}"); return
    data = json.loads(live.read_text(encoding="utf-8"))
    servers = data.get("mcpServers", {})
    if not isinstance(servers, dict):
        return
    # capture only managed servers so transient/non-managed MCP defs in live
    # ~/.claude.json never leak into the repo (and can't carry secrets there).
    servers = {k: v for k, v in servers.items() if k in MANAGED_MCP_SERVERS}
    out = {
        "_comment": "Portable MCP server definitions (SSOT). install merges into ~/.claude.json mcpServers. ${GITHUB_PERSONAL_ACCESS_TOKEN} expanded by Claude at runtime.",
        **servers,
    }
    txt = portable_text(json.dumps(out, ensure_ascii=False, indent=2))
    log("capture ~/.claude.json mcpServers -> claude/mcp.portable.json")
    if not DRY:
        (REPO / "claude/mcp.portable.json").write_text(txt + "\n", encoding="utf-8")

def toml_value(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, list):
        return "[" + ", ".join(toml_value(v) for v in value) + "]"
    return json.dumps(str(value), ensure_ascii=False)

def emit_table(lines, name, data):
    if not isinstance(data, dict):
        return
    lines.append(f"[{name}]")
    nested = []
    for k, v in data.items():
        if isinstance(v, dict):
            nested.append((k, v))
        else:
            lines.append(f"{k} = {toml_value(v)}")
    lines.append("")
    for k, v in nested:
        emit_table(lines, f"{name}.{k}", v)

def capture_codex_portable():
    if tomllib is None:
        return
    live = CODEX / "config.toml"
    if not live.exists():
        return
    try:
        data = tomllib.loads(live.read_text(encoding="utf-8"))
    except Exception as exc:
        log(f"skip codex config capture (invalid toml): {exc}")
        return
    lines = [
        "# Portable Codex config fragment (SSOT).",
        "# install merges ONLY these keys into ~/.codex/config.toml.",
        "# NOT synced (machine-specific, regenerated locally):",
        "#   node_repl, marketplaces, plugins enable, hooks.state, projects, [windows], notify.",
        "",
    ]
    for key in ("model", "model_reasoning_effort", "personality"):
        if key in data:
            lines.append(f"{key} = {toml_value(data[key])}")
    lines.append("")
    for table in ("features", "desktop", "memories"):
        if table in data:
            emit_table(lines, table, data[table])
    mcp = data.get("mcp_servers", {})
    if isinstance(mcp, dict):
        for name, cfg in mcp.items():
            if name == "node_repl":
                continue
            emit_table(lines, f"mcp_servers.{name}", cfg)
    log("capture ~/.codex/config.toml portable keys -> codex/config.portable.toml")
    if not DRY:
        (REPO / "codex/config.portable.toml").write_text(redact("\n".join(lines).rstrip()) + "\n", encoding="utf-8")

def capture_codex_plugins():
    copy(AGENTS / "plugins" / "marketplace.json", REPO / "codex/personal-marketplace.json")
    for name in ("caveman", "gstack", "mattpocock-skills", "graphify", "reply-trace"):
        copy(CODEX / "plugins" / name / ".codex-plugin" / "plugin.json", REPO / "codex/plugin-json" / f"{name}.json")

def main():
    copy(CLAUDE / "CLAUDE.md", REPO / "claude/CLAUDE.md")
    copy_json_template(CLAUDE / "settings.json", REPO / "claude/settings.json")
    for t in (CLAUDE / "tools").glob("*"):
        if t.is_file() and not t.name.endswith(".bak") and t.name != "auto-capture.py":
            copy(t, REPO / "claude/tools" / t.name)
    copytree(CLAUDE / "plugins/marketplaces/personal-local", REPO / "claude/personal-local")
    capture_claude_mcp()
    copy(CODEX / "AGENTS.md", REPO / "codex/AGENTS.md")
    capture_codex_portable()
    capture_codex_plugins()
    # strip .bak that may have been copied
    if not DRY:
        for b in REPO.rglob("*.bak"):
            b.unlink()
    print("Captured. Review `git diff`, then commit.")

if __name__ == "__main__":
    main()
