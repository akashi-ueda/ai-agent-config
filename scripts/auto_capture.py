#!/usr/bin/env python
"""Global hook: mirror live Claude/Codex managed config back into this repo.

Assumes the repo is cloned at ~/ai-agent-config (Windows: %USERPROFILE%\\ai-agent-config).
Set AI_AGENT_CONFIG_REPO to override.

Designed for frequent hook execution:
- metadata fingerprint only (path, size, mtime)
- first run primes state and exits
- later changes run scripts/capture.py
- after a successful capture, commit + push the repo to origin
- lock + debounce prevent recursive/parallel capture

Auto git sync (commit + push) can be disabled by setting
AI_AGENT_CONFIG_NO_SYNC=1. Push runs detached so the hook never blocks the
prompt on the network.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
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
    # codex plugins: only the manifest each (capture.py copies just plugin.json) —
    # avoids rglob over large plugin trees on every prompt.
    CODEX / "plugins" / "gstack" / ".codex-plugin" / "plugin.json",
    CODEX / "plugins" / "mattpocock-skills" / ".codex-plugin" / "plugin.json",
    CODEX / "plugins" / "graphify" / ".codex-plugin" / "plugin.json",
]

WATCH_DIRS = [
    CLAUDE / "tools",
    CLAUDE / "plugins" / "marketplaces" / "personal-local",
    CODEX / "hooks",
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


GIT = shutil.which("git") or "git"

# Repo paths capture.py manages. Auto-commit stages only these so in-progress
# manual edits elsewhere (README, install.*, scripts) are never swept in.
MANAGED_PATHS = [
    "claude/CLAUDE.md",
    "claude/settings.json",
    "claude/tools",
    "claude/personal-local",
    "claude/mcp.portable.json",
    "codex/AGENTS.md",
    "codex/hooks",
    "codex/hooks.json.tmpl",
    "codex/config.portable.toml",
    "codex/personal-marketplace.json",
    "codex/plugin-json",
]


def _git(*args, timeout=15):
    return subprocess.run([GIT, "-C", str(REPO), *args], timeout=timeout,
                          text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def current_branch() -> str:
    r = _git("symbolic-ref", "--quiet", "--short", "HEAD")
    return r.stdout.strip() if r.returncode == 0 else ""


def do_push(branch: str) -> None:
    """Rebase on origin then push. Runs in a detached child (no hook timeout).

    On a rebase conflict it aborts and leaves the local commit for manual
    resolution rather than forcing anything.
    """
    pull = _git("pull", "--rebase", "--autostash", "origin", branch, timeout=120)
    if pull.returncode != 0:
        _git("rebase", "--abort")
        log(f"push aborted: rebase on origin/{branch} failed (manual merge needed)\n{(pull.stdout or '').strip()}")
        return
    push = _git("push", "origin", branch, timeout=120)
    if push.returncode != 0:
        log(f"push failed rc={push.returncode}: {(push.stdout or '').strip()}")
    else:
        log(f"pushed {branch} -> origin")


def git_sync(host: str) -> None:
    """Stage managed paths, commit, and dispatch a detached rebase+push.

    Commit is synchronous (fast, local); the network step (pull --rebase +
    push) runs in a detached child so the hook never blocks the prompt.
    No-op when nothing managed changed or AI_AGENT_CONFIG_NO_SYNC is set.
    """
    if os.environ.get("AI_AGENT_CONFIG_NO_SYNC", "").lower() in ("1", "true", "on", "yes"):
        return
    if not (REPO / ".git").exists():
        log("git_sync skipped: not a git repo")
        return
    try:
        # stage only managed paths (-A within each, so deletions are tracked)
        subprocess.run([GIT, "-C", str(REPO), "add", "-A", "--", *MANAGED_PATHS],
                       timeout=15, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        staged = subprocess.run([GIT, "-C", str(REPO), "diff", "--cached", "--quiet"]).returncode
        if staged == 0:
            return  # nothing managed to commit
        branch = current_branch()
        if not branch:
            log("git_sync: detached HEAD, skipping commit/push")
            return
        msg = f"chore(auto-capture): sync {host} live config"
        commit = _git("commit", "--no-verify", "-m", msg)
        if commit.returncode != 0:
            log(f"git commit failed rc={commit.returncode}: {(commit.stdout or '').strip()}")
            return
        log(f"committed: {msg}")
        # dispatch detached rebase+push via this script's --push-only mode (cross-platform)
        out = open(LOG_FILE, "a", encoding="utf-8")
        out.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} push dispatched (background, branch={branch})\n")
        out.flush()
        subprocess.Popen(
            [sys.executable, os.path.abspath(__file__), "--push-only", branch],
            stdout=out, stderr=out, start_new_session=True,
        )
    except Exception as exc:
        log(f"git_sync error: {exc!r}")


def main() -> int:
    if "--push-only" in sys.argv:
        i = sys.argv.index("--push-only")
        branch = sys.argv[i + 1] if i + 1 < len(sys.argv) else current_branch()
        if branch:
            do_push(branch)
        return 0

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

    host = sys.argv[1] if len(sys.argv) > 1 else "?"
    try:
        rc = run_capture()
        after = fingerprint()
        write_state({"fingerprint": after, "last_capture": time.time(), "last_rc": rc})
        if rc == 0:
            git_sync(host)
        return 0
    except Exception as exc:
        log(f"error: {exc!r}")
        return 0
    finally:
        release_lock()


if __name__ == "__main__":
    raise SystemExit(main())
