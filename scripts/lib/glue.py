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


import os
import sysconfig


def _user_scheme() -> str:
    return "nt_user" if os.name == "nt" else "posix_user"


def user_scripts_dir() -> str:
    """User-install Scripts/bin dir. On Windows this is versioned
    (...\\Python\\PythonXY\\Scripts), NOT user-base + \\Scripts."""
    return sysconfig.get_path("scripts", _user_scheme())


def make_shim(exe_name: str, shim_dir: Path) -> "Path | None":
    """Create a .cmd (Windows) / symlink (posix) shim for a user-installed exe
    if it is not already on PATH. Returns the shim path or None."""
    import shutil as _sh
    if _sh.which(exe_name):
        return None
    scripts = Path(user_scripts_dir())
    target = scripts / (exe_name + (".exe" if os.name == "nt" else ""))
    if not target.exists():
        return None
    shim_dir.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        shim = shim_dir / f"{exe_name}.cmd"
        shim.write_text(f'@echo off\r\n"{target}" %*\r\n', encoding="ascii")
    else:
        shim = shim_dir / exe_name
        if shim.exists() or shim.is_symlink():
            shim.unlink()
        shim.symlink_to(target)
    return shim


def pip_command(has_standalone_pip: bool, python: str) -> list:
    return ["pip"] if has_standalone_pip else [python, "-m", "pip"]


def pip_install(package: str, python: str, dry_run: bool = False) -> None:
    import shutil as _sh
    has_pip = bool(_sh.which("pip") or _sh.which("pip3"))
    base = pip_command(has_pip, python)
    args = base + ["install", "--user", package]
    if dry_run:
        print("[dry] " + " ".join(args)); return
    rc = _run(args)
    if rc != 0:
        _run(base + ["install", "--user", "--break-system-packages", package])


def rewrite_gstack_paths(text: str) -> str:
    """Point gstack SKILL.md path vars at the installed core (~/.gstack/core).
    The $_ROOT/ prefix rule runs BEFORE the bare rule to avoid the greedy
    $_ROOT/$HOME/.gstack/core mangle."""
    text = text.replace("$HOME/.codex/skills/gstack", "$HOME/.gstack/core")
    text = text.replace("$HOME/.agents/skills/gstack", "$HOME/.gstack/core")
    text = text.replace("$_ROOT/.agents/skills/gstack", "$_ROOT/.gstack/core")
    text = text.replace(".agents/skills/gstack", "$HOME/.gstack/core")
    return text
