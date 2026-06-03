#!/usr/bin/env python
"""Global hook: mirror live Claude/Codex managed config back into this repo.

Assumes the repo is cloned at ~/ai-agent-config (Windows: %USERPROFILE%\\ai-agent-config).
Set AI_AGENT_CONFIG_REPO to override.

Designed for frequent hook execution:
- metadata fingerprint only (path, size, mtime)
- first run primes state and exits
- later changes run scripts/capture.py
- lock + debounce prevent recursive/parallel capture
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HOME = Path.home()
REPO = Path(os.environ.get("AI_AGENT_CONFIG_REPO", HOME / "ai-agent-config"))
CLAUDE = HOME / ".claude"
CODEX = HOME / ".codex"
AGENTS = HOME / ".agents"
STATE_DIR = HOME / ".ai-agent-config-state"
STATE_FILE = STATE_DIR / "auto-capture.json"
LOCK_FILE = STATE_DIR / "auto-capture.lock"
LOG_FILE = STATE_DIR / "auto-capture.log"
DEBOUNCE_SECONDS = 5

WATCH_FILES = [
    CLAUDE / "CLAUDE.md",
    CLAUDE / "settings.json",
    HOME / ".claude.json",
    CODEX / "AGENTS.md",
    CODEX / "hooks.json",
    CODEX / "config.toml",
    AGENTS / "plugins" / "marketplace.json",
]

WATCH_DIRS = [
    CLAUDE / "tools",
    CLAUDE / "plugins" / "marketplaces" / "personal-local",
    CODEX / "hooks",
    CODEX / "plugins" / "gstack",
    CODEX / "plugins" / "mattpocock-skills",
    CODEX / "plugins" / "graphify",
]

IGNORE_PARTS = {
    ".git",
    "__pycache__",
    "node_modules",
    "cache",
    "sessions",
    "projects",
    "backups",
}


def log(msg: str) -> None:
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")
    except Exception:
        pass


def iter_files():
    for path in WATCH_FILES:
        if path.exists():
            yield path
    for root in WATCH_DIRS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.name.endswith(".bak"):
                continue
            if any(part in IGNORE_PARTS for part in path.parts):
                continue
            yield path


def fingerprint() -> str:
    rows = []
    for path in sorted(set(iter_files()), key=lambda p: str(p)):
        try:
            st = path.stat()
        except OSError:
            continue
        try:
            rel = str(path.relative_to(HOME))
        except ValueError:
            rel = str(path)
        rows.append(f"{rel}\0{st.st_size}\0{st.st_mtime_ns}")
    return hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()


def read_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_state(state: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def acquire_lock() -> bool:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if LOCK_FILE.exists():
        try:
            if time.time() - LOCK_FILE.stat().st_mtime > 30:
                LOCK_FILE.unlink()
        except OSError:
            return False
    try:
        fd = os.open(str(LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode("ascii"))
        os.close(fd)
        return True
    except FileExistsError:
        return False


def release_lock() -> None:
    try:
        LOCK_FILE.unlink()
    except OSError:
        pass


def run_capture() -> int:
    script = REPO / "scripts" / "capture.py"
    if not script.exists():
        log(f"missing repo capture script: {script}")
        return 1
    proc = subprocess.run(
        [sys.executable, str(script), "--from-hook"],
        cwd=str(REPO),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=20,
    )
    if proc.stdout:
        log(proc.stdout.rstrip())
    return proc.returncode


def main() -> int:
    if "--prime" in sys.argv:
        write_state({"fingerprint": fingerprint(), "last_capture": 0})
        return 0

    now = time.time()
    state = read_state()
    current = fingerprint()
    previous = state.get("fingerprint")

    if not previous:
        write_state({"fingerprint": current, "last_capture": 0})
        return 0
    if current == previous:
        return 0
    if now - float(state.get("last_capture", 0)) < DEBOUNCE_SECONDS:
        return 0
    if not acquire_lock():
        return 0

    try:
        rc = run_capture()
        after = fingerprint()
        write_state({"fingerprint": after, "last_capture": time.time(), "last_rc": rc})
        return 0
    except Exception as exc:
        log(f"error: {exc!r}")
        return 0
    finally:
        release_lock()


if __name__ == "__main__":
    raise SystemExit(main())
