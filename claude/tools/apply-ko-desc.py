#!/usr/bin/env python
"""Translate installed skill/plugin descriptions to Korean in-place.

- Only rewrites the description field inside the YAML frontmatter (between the
  first two `---` lines). Body and all other keys untouched.
- Handles single-line and folded (`>` / `|`) descriptions.
- Keyed by frontmatter `name:`. Map loaded from skill-descriptions.ko.map.json
  ({ "<name>": "<korean>" }).
- Also rewrites installed plugin JSON, marketplace JSON, package JSON, and
  Markdown frontmatter descriptions when a map entry exists.
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
    HOME / ".claude" / "plugins" / "marketplaces",
    HOME / ".claude" / "skills",
    HOME / ".codex" / "plugins",
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

def map_key_for_markdown(path, lines, end):
    parts = path.parts
    if "commands" in parts:
        return f"codex-command-{path.stem}" if "openai-codex" in parts else path.stem
    name = get_name(lines, end)
    if name:
        return name
    return path.stem

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

PLUGIN_JSON_NAMES = {
    ".claude-plugin",
    ".codex-plugin",
}

def rewrite_plugin_json(path, km):
    parent = path.parent.name
    if parent not in PLUGIN_JSON_NAMES:
        return False
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    name = data.get("name")
    ko = km.get(name)
    if not ko:
        return False

    changed = False
    for key in ("description",):
        if data.get(key) != ko:
            data[key] = ko
            changed = True

    interface = data.get("interface")
    if isinstance(interface, dict):
        for key in ("shortDescription", "longDescription"):
            if interface.get(key) != ko:
                interface[key] = ko
                changed = True

    if not changed:
        return False
    if not DRY:
        bak = path.with_suffix(path.suffix + ".bak")
        if not bak.exists():
            bak.write_text(raw, encoding="utf-8")
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return True

def rewrite_marketplace_json(path, km):
    if path.parent.name != ".claude-plugin" or path.name != "marketplace.json":
        return False
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    changed = False

    name = data.get("name")
    ko = km.get(name)
    metadata = data.get("metadata")
    if ko and isinstance(metadata, dict) and metadata.get("description") != ko:
        metadata["description"] = ko
        changed = True

    plugins = data.get("plugins")
    if isinstance(plugins, list):
        for plugin in plugins:
            if not isinstance(plugin, dict):
                continue
            pko = km.get(plugin.get("name"))
            if pko and plugin.get("description") != pko:
                plugin["description"] = pko
                changed = True

    if not changed:
        return False
    if not DRY:
        bak = path.with_suffix(path.suffix + ".bak")
        if not bak.exists():
            bak.write_text(raw, encoding="utf-8")
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return True

def rewrite_package_json(path, km):
    if path.name != "package.json":
        return False
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    ko = km.get(data.get("name"))
    if not ko or data.get("description") == ko:
        return False
    data["description"] = ko
    if not DRY:
        bak = path.with_suffix(path.suffix + ".bak")
        if not bak.exists():
            bak.write_text(raw, encoding="utf-8")
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return True

def rewrite_hook_json(path, km):
    if path.name != "hooks.json":
        return False
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    key = "codex-hook-stop-review-gate" if "openai-codex" in path.parts else path.stem
    ko = km.get(key)
    if not ko or data.get("description") == ko:
        return False
    data["description"] = ko
    if not DRY:
        bak = path.with_suffix(path.suffix + ".bak")
        if not bak.exists():
            bak.write_text(raw, encoding="utf-8")
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
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
        for p in root.rglob("plugin.json"):
            rp = p.resolve()
            if rp in seen:
                continue
            seen.add(rp)
            if RESTORE:
                if restore(p):
                    n_ok += 1
                continue
            try:
                if rewrite_plugin_json(p, km):
                    n_ok += 1
                else:
                    n_skip += 1
            except (json.JSONDecodeError, UnicodeDecodeError):
                n_skip += 1
        for p in list(root.rglob("marketplace.json")) + list(root.rglob("package.json")) + list(root.rglob("hooks.json")):
            rp = p.resolve()
            if rp in seen:
                continue
            seen.add(rp)
            if RESTORE:
                if restore(p):
                    n_ok += 1
                continue
            try:
                if rewrite_marketplace_json(p, km) or rewrite_package_json(p, km) or rewrite_hook_json(p, km):
                    n_ok += 1
                else:
                    n_skip += 1
            except (json.JSONDecodeError, UnicodeDecodeError):
                n_skip += 1
        for p in root.rglob("*.md"):
            rp = p.resolve()
            if rp in seen:
                continue
            seen.add(rp)
            lines = p.read_text(encoding="utf-8").splitlines()
            b = frontmatter_bounds(lines)
            if not b:
                continue
            name = map_key_for_markdown(p, lines, b[1])
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
