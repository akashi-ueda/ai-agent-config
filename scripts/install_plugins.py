#!/usr/bin/env python
"""Install plugins declared in manifest/plugins.json onto Claude + Codex.

Deterministic engine: each install action dispatches to a method handler in
scripts/lib/methods.py; env glue lives in scripts/lib/glue.py. File placement
(personal-local dir, MCP/config merge) is handled separately by apply.py.

Usage:
  python scripts/install_plugins.py [--dry-run] [--only ID] [--host claude|codex] [--prune]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from scripts.lib import glue, manifest, methods  # noqa: E402

HOST_OF_METHOD = {
    "claude_marketplace": "claude", "claude_local": "claude",
    "codex_store": "codex", "codex_local": "codex",
    "external_cli": "external", "built_binary": "external",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only")
    ap.add_argument("--host", choices=["claude", "codex"])
    ap.add_argument("--prune", action="store_true")
    args = ap.parse_args()

    m = manifest.load_manifest(REPO / "manifest/plugins.json")
    manifest.validate_manifest(m, set(methods.HANDLERS), REPO)

    ctx = methods.Ctx(repo=REPO, home=Path.home(), python=sys.executable,
                      dry_run=args.dry_run)
    rows = []
    for p in m["plugins"]:
        if args.only and p["id"] != args.only:
            continue
        for a in p["install"]:
            if args.host and HOST_OF_METHOD[a["method"]] not in (args.host, "external"):
                continue
            try:
                status = methods.HANDLERS[a["method"]](a, ctx)
            except Exception as e:  # noqa: BLE001
                status = "fail"
                print(f"  ERROR {p['id']}/{a['method']}: {e}")
            rows.append((p["id"], a["method"], status))

    print("\n== install summary ==")
    for pid, method, status in rows:
        print(f"  {status:5}  {pid:18} {method}")

    if not args.dry_run:
        live = _live_managed_ids(ctx)
        orphans = manifest.detect_orphans(m, live)
        for o in sorted(orphans):
            print(f"  orphan {o:18} (in live, not in manifest)")
        if args.prune and orphans:
            for o in sorted(orphans):
                glue.run_cli([ctx.codex, "plugin", "remove", f"{o}@personal"])
                glue.run_cli([ctx.claude, "plugin", "uninstall", o])

    return 1 if any(s == "fail" for _, _, s in rows) else 0


def _live_managed_ids(ctx: methods.Ctx) -> set:
    """Best-effort: parse `codex plugin list` personal entries. Returns a set
    of plugin ids; empty on any error (orphan check then no-ops)."""
    try:
        import subprocess
        out = subprocess.run([ctx.codex, "plugin", "list"],
                             capture_output=True, text=True,
                             encoding="utf-8", errors="replace")
        ids = set()
        for line in out.stdout.splitlines():
            if "@personal" in line:
                ids.add(line.split("@personal")[0].strip().split()[-1])
        return ids
    except Exception:  # noqa: BLE001
        return set()


if __name__ == "__main__":
    raise SystemExit(main())
