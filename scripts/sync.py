#!/usr/bin/env python
"""Capture live Claude/Codex config -> repo, then commit & push.

Instruction-driven (not a per-prompt hook): run this *after* you change global
config — instructions, MCP, hooks, plugins, or skills. CLAUDE.md / AGENTS.md tell
the agent to invoke it. Manual use:

    python ~/ai-agent-config/scripts/sync.py [host] [-m "msg"] [--no-push]

It mirrors live managed config into the repo (scripts/capture.py), stages only
the managed paths, commits, rebases on origin, and pushes. Synchronous — prints
what it did. No-op when nothing managed changed.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(os.environ.get("AI_AGENT_CONFIG_REPO", Path.home() / "ai-agent-config"))
GIT = shutil.which("git") or "git"

# Repo paths capture.py manages; stage only these so unrelated WIP is never swept in.
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


def _git(*args, timeout=120):
    return subprocess.run([GIT, "-C", str(REPO), *args], timeout=timeout,
                          text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def run_capture() -> int:
    script = REPO / "scripts" / "capture.py"
    if not script.exists():
        print(f"[sync] missing {script}", file=sys.stderr)
        return 1
    proc = subprocess.run([sys.executable, str(script)], cwd=str(REPO),
                          text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if proc.stdout:
        print(proc.stdout.rstrip())
    return proc.returncode


def git_sync(host: str, message: str | None, push: bool) -> None:
    if not (REPO / ".git").exists():
        print("[sync] not a git repo, skipping commit/push")
        return
    branch = _git("symbolic-ref", "--quiet", "--short", "HEAD").stdout.strip()
    if not branch:
        print("[sync] detached HEAD — resolve manually")
        return
    # Integrate remote FIRST so we never build on a stale base (other machines /
    # the co-resident agent may have pushed). Conflict -> abort + stop.
    if push:
        pre = _git("pull", "--rebase", "--autostash", "origin", branch)
        if pre.returncode != 0:
            _git("rebase", "--abort")
            print(f"[sync] pre-sync rebase on origin/{branch} failed — resolve manually, then re-run:\n{pre.stdout.rstrip()}")
            return
    subprocess.run([GIT, "-C", str(REPO), "add", "-A", "--", *MANAGED_PATHS],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if subprocess.run([GIT, "-C", str(REPO), "diff", "--cached", "--quiet"]).returncode == 0:
        print("[sync] nothing managed changed — clean")
        return
    msg = message or f"chore(sync): {host} live config"
    commit = _git("commit", "--no-verify", "-m", msg)
    if commit.returncode != 0:
        print(f"[sync] commit failed:\n{commit.stdout.rstrip()}")
        return
    print(f"[sync] committed: {msg}")
    if not push:
        print("[sync] --no-push set; left commit local")
        return
    pull = _git("pull", "--rebase", "--autostash", "origin", branch)
    if pull.returncode != 0:
        _git("rebase", "--abort")
        print(f"[sync] rebase on origin/{branch} failed — push skipped, merge manually:\n{pull.stdout.rstrip()}")
        return
    out = _git("push", "origin", branch)
    print(out.stdout.rstrip() if out.returncode != 0 else f"[sync] pushed {branch} -> origin")


def main() -> int:
    args = sys.argv[1:]
    push = "--no-push" not in args
    args = [a for a in args if a != "--no-push"]
    message = None
    if "-m" in args:
        i = args.index("-m")
        message = args[i + 1] if i + 1 < len(args) else None
        del args[i:i + 2]
    host = args[0] if args else "manual"
    rc = run_capture()
    if rc != 0:
        print(f"[sync] capture failed rc={rc}; not committing")
        return rc
    git_sync(host, message, push)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
