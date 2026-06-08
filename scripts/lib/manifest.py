"""Load, validate, and diff the plugins manifest."""
from __future__ import annotations

import json
from pathlib import Path

SCHEMA = "personal-agent-config/plugins v1"
# manifest path keys whose values must exist on disk (repo-relative)
PATH_FIELDS = ("wrapper", "plugin_json", "wrapper_fallback")
# keys each method requires; checked at validate time so a malformed manifest
# fails fast instead of raising KeyError deep inside a handler.
REQUIRED_KEYS = {
    "claude_marketplace": ("source", "marketplace", "plugin"),
    "claude_local": ("source", "marketplace", "plugin"),
    "codex_store": ("marketplace", "plugin"),
    "codex_local": ("plugin", "plugin_json", "marketplace"),
    "external_cli": ("tool", "pip_package"),
    "built_binary": ("clone", "dest", "builder"),
}


class ManifestError(Exception):
    pass


def load_manifest(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_manifest(m: dict, known_methods: set, repo: Path) -> None:
    if m.get("_schema") != SCHEMA:
        raise ManifestError(f"bad _schema: {m.get('_schema')!r}")
    plugins = m.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        raise ManifestError("plugins must be a non-empty list")
    for p in plugins:
        for field in ("id", "repo", "install"):
            if not p.get(field):
                raise ManifestError(f"plugin missing {field}: {p.get('id')!r}")
        if not isinstance(p["install"], list) or not p["install"]:
            raise ManifestError(f"empty install[]: {p['id']!r}")
        for a in p["install"]:
            method = a.get("method")
            if method not in known_methods:
                raise ManifestError(f"{p['id']}: unknown method {method!r}")
            for key in REQUIRED_KEYS.get(method, ()):
                if not a.get(key):
                    raise ManifestError(
                        f"{p['id']}: {method} action missing {key!r}")
            for pf in PATH_FIELDS:
                if pf in a and not a[pf].startswith("~"):
                    if not (repo / a[pf]).exists():
                        raise ManifestError(
                            f"{p['id']}: {pf} path not found: {a[pf]}")


def manifest_plugin_ids(m: dict) -> set:
    """All plugin ids the manifest declares (the `plugin` field of each
    action, falling back to the plugin id)."""
    ids = set()
    for p in m["plugins"]:
        ids.add(p["id"])
        for a in p["install"]:
            if a.get("plugin"):
                ids.add(a["plugin"])
    return ids


def detect_orphans(m: dict, live_ids: set) -> set:
    """Live managed plugin ids that the manifest no longer declares."""
    return set(live_ids) - manifest_plugin_ids(m)
