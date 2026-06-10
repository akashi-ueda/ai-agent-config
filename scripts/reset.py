#!/usr/bin/env python
"""Factory-reset live Claude/Codex config, preserving auth + history.

Removes ONLY the repo-regenerated managed artifacts (the things apply.py +
install_plugins.py rebuild). Auth/credentials, sessions, projects, machine
config, and history are KEPT. Everything removed is copied to a timestamped
backup folder first, so a reset is always reversible.

Run install (apply.py + install_plugins.py) afterwards to rebuild — or use the
install wrapper's --reset flag, which chains reset + reinstall.

Usage:
  python scripts/reset.py --host claude|codex|both [--yes] [--dry-run]

Safety: refuses to run non-interactively without --yes. --dry-run prints the
backup+delete plan without touching anything.
"""
from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

HOME = Path.home()
CLAUDE = HOME / ".claude"
CODEX = HOME / ".codex"

# Managed/regenerable paths reset removes, per host. MUST be a subset of what
# apply.py + install_plugins.py rebuild — anything here that is NOT regenerated
# would be permanent loss (mitigated by the mandatory backup, but keep it true).
# Auth, sessions, projects, machine config, history are intentionally absent.
CLAUDE_DELETE = [
    CLAUDE / "CLAUDE.md",
    CLAUDE / "settings.json",
    CLAUDE / "tools",
    CLAUDE / "plugins" / "marketplaces",
    CLAUDE / "plugins" / "cache",
    CLAUDE / "plugins" / "installed_plugins.json",
    CLAUDE / "plugins" / "known_marketplaces.json",
]
CODEX_PERSONAL_PLUGINS = ["caveman", "graphify", "gstack", "mattpocock-skills", "reply-trace"]
CODEX_DELETE = [
    CODEX / "AGENTS.md",
    CODEX / "plugins" / "cache",
    *[CODEX / "plugins" / p for p in CODEX_PERSONAL_PLUGINS],
]

HOSTS = {
    "claude": (CLAUDE, CLAUDE_DELETE,
               "credentials, projects, sessions, session-env, shell-snapshots, plugins/data"),
    "codex": (CODEX, CODEX_DELETE,
              "auth.json, config.toml, sessions, logs/sqlite, node_repl, memories"),
}


def log(msg, dry):
    print(("[dry] " if dry else "[reset] ") + msg)


def backup_and_delete(home: Path, paths, backup_root: Path, dry: bool) -> int:
    n = 0
    for p in paths:
        if not p.exists():
            continue
        rel = p.relative_to(home)
        dest = backup_root / rel
        log(f"backup {rel} -> {dest}", dry)
        log(f"delete {rel}", dry)
        if dry:
            n += 1
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        if p.is_dir():
            shutil.copytree(p, dest)
            shutil.rmtree(p)
        else:
            shutil.copy2(p, dest)
            p.unlink()
        n += 1
    return n


def reset_host(host: str, backup_ts: str, dry: bool) -> None:
    home, paths, keep = HOSTS[host]
    backup_root = HOME / f".{host}-reset-backup-{backup_ts}"
    log(f"=== reset {host}: keep [{keep}]; backup -> {backup_root} ===", dry)
    n = backup_and_delete(home, paths, backup_root, dry)
    log(f"{host}: {n} managed path(s) {'would be ' if dry else ''}backed up + removed", dry)


def hosts_arg(argv) -> "list[str] | None":
    if "--host" not in argv:
        return None
    i = argv.index("--host")
    if i + 1 >= len(argv):
        return None
    h = argv[i + 1]
    if h == "both":
        return ["claude", "codex"]
    return [h] if h in HOSTS else None


def confirm(targets, yes: bool, dry: bool) -> bool:
    if dry or yes:
        return True
    if not sys.stdin.isatty():
        print("[reset] ERROR: non-interactive; pass --yes to confirm destructive reset")
        return False
    print(f"About to reset: {', '.join(targets)} (managed config only; auth/history kept, "
          f"full backup made first).")
    try:
        return input("Type YES to proceed: ").strip() == "YES"
    except EOFError:
        print("[reset] no input; aborting")
        return False


def main() -> int:
    argv = sys.argv[1:]
    dry = "--dry-run" in argv
    yes = "--yes" in argv
    targets = hosts_arg(argv)
    if not targets:
        print("usage: reset.py --host claude|codex|both [--yes] [--dry-run]")
        return 2
    if not confirm(targets, yes, dry):
        print("[reset] aborted.")
        return 1
    ts = time.strftime("%Y%m%d-%H%M%S")
    for host in targets:
        reset_host(host, ts, dry)
    print("[reset] done. Run install (apply.py + install_plugins.py) to rebuild.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
