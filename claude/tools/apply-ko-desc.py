#!/usr/bin/env python
"""Translate SKILL.md `description:` frontmatter to Korean in-place.

- Only rewrites the description field inside the YAML frontmatter (between the
  first two `---` lines). Body and all other keys untouched.
- Handles single-line and folded (`>` / `|`) descriptions.
- Keyed by frontmatter `name:`. Map loaded from skill-descriptions.ko.map.json
  ({ "<name>": "<korean>" }).
- Writes a one-time `.bak` next to each modified file (skipped if exists).
- Idempotent + re-appliable (run again after a plugin update to restore Korean).

Usage:
  python apply-ko-desc.py            # apply
  python apply-ko-desc.py --restore  # restore originals from .bak
  python apply-ko-desc.py --dry-run
"""
import json, re, sys, os
from pathlib import Path

HOME = Path(os.path.expanduser("~"))
ROOTS = [
    HOME / ".claude" / "plugins" / "cache",
    HOME / ".claude" / "plugins" / "marketplaces" / "personal-local",
    HOME / ".claude" / "skills",
]
MAP_FILE = HOME / ".claude" / "tools" / "skill-descriptions.ko.map.json"

DRY = "--dry-run" in sys.argv
RESTORE = "--restore" in sys.argv

def frontmatter_bounds(lines):
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return (0, i)
    return None

NAME_RE = re.compile(r"^name:\s*(.+?)\s*$")
KEY_RE = re.compile(r"^[A-Za-z0-9_-]+:")

def get_name(lines, end):
    for i in range(1, end):
        m = NAME_RE.match(lines[i])
        if m:
            return m.group(1).strip().strip('"\'')
    return None

def rewrite(path, ko):
    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines()
    b = frontmatter_bounds(lines)
    if not b:
        return False
    _, end = b
    # find description line within frontmatter
    di = None
    for i in range(1, end):
        if lines[i].startswith("description:"):
            di = i
            break
    if di is None:
        return False
    # determine extent of description value (folded/multi-line)
    after = di + 1
    val = lines[di][len("description:"):].strip()
    if val in (">", "|", ">-", "|-", ">+", "|+", ""):
        # consume following indented continuation lines until next key or ---
        while after < end and not KEY_RE.match(lines[after]) and lines[after].strip() != "---":
            after += 1
    new_lines = lines[:di] + [f"description: {ko}"] + lines[after:]
    new = "\n".join(new_lines)
    if raw.endswith("\n"):
        new += "\n"
    if new == raw:
        return False
    if not DRY:
        bak = path.with_suffix(path.suffix + ".bak")
        if not bak.exists():
            bak.write_text(raw, encoding="utf-8")
        path.write_text(new, encoding="utf-8")
    return True

def restore(path):
    bak = path.with_suffix(path.suffix + ".bak")
    if bak.exists():
        if not DRY:
            path.write_text(bak.read_text(encoding="utf-8"), encoding="utf-8")
        return True
    return False

def main():
    km = json.loads(MAP_FILE.read_text(encoding="utf-8")) if MAP_FILE.exists() else {}
    seen = set()
    n_ok = n_skip = 0
    for root in ROOTS:
        if not root.exists():
            continue
        for p in root.rglob("SKILL.md"):
            rp = p.resolve()
            if rp in seen:
                continue
            seen.add(rp)
            lines = p.read_text(encoding="utf-8").splitlines()
            b = frontmatter_bounds(lines)
            if not b:
                continue
            name = get_name(lines, b[1])
            if RESTORE:
                if restore(p):
                    n_ok += 1
                continue
            ko = km.get(name)
            if not ko:
                n_skip += 1
                continue
            if rewrite(p, ko):
                n_ok += 1
            else:
                n_skip += 1
    tag = "restored" if RESTORE else ("would-change" if DRY else "changed")
    print(f"{tag}: {n_ok}  skipped/no-map: {n_skip}  map-entries: {len(km)}")

if __name__ == "__main__":
    main()
