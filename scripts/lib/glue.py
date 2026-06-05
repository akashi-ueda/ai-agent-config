"""Environment glue helpers for the plugin install engine. OS/version quirks
live here so method handlers and the manifest stay OS-agnostic."""
from __future__ import annotations

import shutil
from pathlib import Path


def _read_text_utf8(path: Path) -> str:
    """Read as UTF-8, transparently dropping a leading BOM if present."""
    return path.read_text(encoding="utf-8-sig")


def _write_text_utf8_no_bom(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")  # Python never adds a BOM here


def bom_safe_copy(src: Path, dst: Path) -> None:
    """Copy a single text file, guaranteeing BOM-less UTF-8 output."""
    _write_text_utf8_no_bom(Path(dst), _read_text_utf8(Path(src)))


def rewrite_gstack_paths(text: str) -> str:
    """Point gstack SKILL.md path vars at the installed core (~/.gstack/core).
    The $_ROOT/ prefix rule runs BEFORE the bare rule to avoid the greedy
    $_ROOT/$HOME/.gstack/core mangle."""
    text = text.replace("$HOME/.codex/skills/gstack", "$HOME/.gstack/core")
    text = text.replace("$HOME/.agents/skills/gstack", "$HOME/.gstack/core")
    text = text.replace("$_ROOT/.agents/skills/gstack", "$_ROOT/.gstack/core")
    text = text.replace(".agents/skills/gstack", "$HOME/.gstack/core")
    return text
