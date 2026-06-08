"""Environment glue helpers for the plugin install engine. OS/version quirks
live here so method handlers and the manifest stay OS-agnostic."""
from __future__ import annotations

import os
import subprocess
import sysconfig
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


def _run(args: list, extra_env: dict | None = None, cwd: str | None = None) -> int:
    env = None
    if extra_env:
        env = dict(os.environ); env.update(extra_env)
    # Force UTF-8 decoding: the Windows locale codec (cp932/cp949) cannot decode
    # the UTF-8 output (✓, —, Korean) that the claude/codex CLIs emit.
    proc = subprocess.run(args, capture_output=True, text=True, env=env, cwd=cwd,
                          encoding="utf-8", errors="replace")
    return proc.returncode


def is_benign_already(stderr: str) -> bool:
    s = (stderr or "").lower()
    return "already enabled" in s or "already installed" in s


def run_cli(args: list, dry_run: bool = False, cwd: str | None = None) -> tuple:
    """Run a CLI; return (returncode, stderr). Never raises on nonzero."""
    if dry_run:
        print("[dry] " + " ".join(args)); return 0, ""
    proc = subprocess.run(args, capture_output=True, text=True, cwd=cwd,
                          encoding="utf-8", errors="replace")
    return proc.returncode, proc.stderr


def run_capture(args: list, cwd: str | None = None) -> tuple:
    """Run a CLI; return (returncode, stdout). UTF-8 decoded. Never raises."""
    proc = subprocess.run(args, capture_output=True, text=True, cwd=cwd,
                          encoding="utf-8", errors="replace")
    return proc.returncode, proc.stdout


def idempotent_cli(args: list, dry_run: bool = False) -> str:
    """Run a plugin install/enable; treat 'already ...' stderr as success.
    Returns 'ok' | 'skip' (benign) | 'fail'."""
    rc, err = run_cli(args, dry_run=dry_run)
    if rc == 0:
        return "ok"
    return "skip" if is_benign_already(err) else "fail"


def ensure_bash() -> bool:
    """Ensure `bash` is callable; on Windows prepend Git's usr\\bin. Returns
    True if bash is available after the attempt."""
    import shutil as _sh
    if _sh.which("bash"):
        return True
    if os.name == "nt":
        git = _sh.which("git")
        if git:
            git_dir = Path(git).resolve().parent.parent  # ...\Git
            usr_bin = git_dir / "usr" / "bin"
            if (usr_bin / "bash.exe").exists():
                os.environ["PATH"] = f"{usr_bin}{os.pathsep}" + os.environ["PATH"]
                return bool(_sh.which("bash"))
    return False


def pip_command(has_standalone_pip: bool, python: str) -> list:
    return ["pip"] if has_standalone_pip else [python, "-m", "pip"]


def pip_install(package: str, python: str, dry_run: bool = False) -> None:
    import shutil as _sh
    # pip_command returns the literal "pip" when standalone; only treat pip as
    # available when that exact name resolves. A pip3-only box falls back to
    # `python -m pip` (robust, same interpreter) instead of exec'ing missing 'pip'.
    has_pip = bool(_sh.which("pip"))
    base = pip_command(has_pip, python)
    args = base + ["install", "--user", package]
    if dry_run:
        print("[dry] " + " ".join(args)); return
    rc = _run(args)
    if rc != 0:
        _run(base + ["install", "--user", "--break-system-packages", package])


def codex_marketplace_upsert(marketplace: dict, plugin_id: str) -> bool:
    """Ensure `plugin_id` exists in a Codex personal marketplace dict.
    Returns True if it added the entry, False if already present."""
    plugins = marketplace.setdefault("plugins", [])
    if any(p.get("name") == plugin_id for p in plugins):
        return False
    plugins.append({
        "name": plugin_id,
        "source": {"source": "local", "path": f"./.codex/plugins/{plugin_id}"},
        "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
        "category": "Productivity",
    })
    return True


def rewrite_gstack_paths(text: str) -> str:
    """Point gstack SKILL.md path vars at the installed core (~/.gstack/core).
    The $_ROOT/ prefix rule runs BEFORE the bare rule to avoid the greedy
    $_ROOT/$HOME/.gstack/core mangle."""
    text = text.replace("$HOME/.codex/skills/gstack", "$HOME/.gstack/core")
    text = text.replace("$HOME/.agents/skills/gstack", "$HOME/.gstack/core")
    text = text.replace("$_ROOT/.agents/skills/gstack", "$_ROOT/.gstack/core")
    text = text.replace(".agents/skills/gstack", "$HOME/.gstack/core")
    return text
