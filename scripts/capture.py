#!/usr/bin/env python
"""Capture live Claude/Codex authored config -> repo (push direction).

Copies the hand-authored, portable files back into the repo and re-templatizes
machine-specific paths/secrets. Run before committing changes you made directly
in ~/.claude or ~/.codex.

Does NOT auto-regenerate config.portable.toml / mcp.portable.json (edit those in
the repo directly — they rarely change). Verify `git diff` before committing.

Usage: python scripts/capture.py [--dry-run]
"""
import os, re, shutil, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HOME = Path.home()
CLAUDE = HOME / ".claude"
CODEX = HOME / ".codex"
DRY = "--dry-run" in sys.argv

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

def main():
    copy(CLAUDE / "CLAUDE.md", REPO / "claude/CLAUDE.md")
    copy(CLAUDE / "settings.json", REPO / "claude/settings.json")
    for t in (CLAUDE / "tools").glob("*"):
        if t.is_file() and not t.name.endswith(".bak"):
            copy(t, REPO / "claude/tools" / t.name)
    copytree(CLAUDE / "plugins/marketplaces/personal-local", REPO / "claude/personal-local")
    copy(CODEX / "AGENTS.md", REPO / "codex/AGENTS.md")
    copy(CODEX / "hooks/caveman.py", REPO / "codex/hooks/caveman.py")
    # re-templatize live hooks.json -> hooks.json.tmpl
    live_hooks = CODEX / "hooks.json"
    if live_hooks.exists():
        txt = live_hooks.read_text(encoding="utf-8")
        txt = re.sub(r'"[^"]*python(?:\.exe)?"', '"{{PYTHON}}"', txt, flags=re.I)
        txt = txt.replace(str(CODEX).replace("\\", "\\\\"), "{{CODEX_HOME}}")
        txt = txt.replace(str(CODEX).replace("\\", "/"), "{{CODEX_HOME}}")
        log("re-templatize hooks.json -> codex/hooks.json.tmpl")
        if not DRY:
            (REPO / "codex/hooks.json.tmpl").write_text(txt, encoding="utf-8")
    # strip .bak that may have been copied
    if not DRY:
        for b in REPO.rglob("*.bak"):
            b.unlink()
    print("Captured. Review `git diff`, then commit. (config.portable.toml / mcp.portable.json are edited in-repo, not captured.)")

if __name__ == "__main__":
    main()
