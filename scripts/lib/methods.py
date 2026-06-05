"""Install method handlers. method string -> handler(action, ctx)."""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from . import glue


@dataclass
class Ctx:
    repo: Path
    home: Path
    python: str
    claude: str = "claude"
    codex: str = "codex"
    dry_run: bool = False
    plan: list = field(default_factory=list)   # records commands in dry_run

    def cli(self, args: list) -> str:
        """Record (dry_run) or run an idempotent CLI command."""
        if self.dry_run:
            self.plan.append(args)
            return "ok"
        return glue.idempotent_cli(args)


def _expand(path: str, ctx: Ctx) -> Path:
    if path.startswith("~"):
        return Path(path.replace("~", str(ctx.home), 1))
    return ctx.repo / path


def _plugin_id(a: dict) -> str:
    return a["plugin"]


def h_claude_marketplace(a: dict, ctx: Ctx) -> str:
    ctx.cli([ctx.claude, "plugin", "marketplace", "add", a["source"]])
    ref = f'{a["plugin"]}@{a["marketplace"]}'
    ctx.cli([ctx.claude, "plugin", "install", ref])
    return ctx.cli([ctx.claude, "plugin", "enable", ref])


def h_claude_local(a: dict, ctx: Ctx) -> str:
    # wrapper/skill content is placed by apply.py; here we only register+enable
    ref = f'{a["plugin"]}@{a["marketplace"]}'
    ctx.cli([ctx.claude, "plugin", "install", ref])
    return ctx.cli([ctx.claude, "plugin", "enable", ref])


def _is_installed_in_list(list_output: str, plugin: str, marketplace: str) -> bool:
    """True if `codex plugin list` output shows plugin@marketplace installed."""
    ref = f"{plugin}@{marketplace}"
    return any(ref in line and "installed" in line
               for line in list_output.splitlines())


def _codex_installed(ctx: Ctx, plugin: str, marketplace: str) -> bool:
    """Skip re-adding an already-installed Codex plugin: re-add triggers a
    cache-backup that fails with 'os error 5' on Windows, and first-time adds
    have no cache to back up. Idempotent + avoids the broken path."""
    _, out = glue.run_capture([ctx.codex, "plugin", "list"])
    return _is_installed_in_list(out, plugin, marketplace)


def h_codex_store(a: dict, ctx: Ctx) -> str:
    ref = f'{a["plugin"]}@{a["marketplace"]}'
    if not ctx.dry_run and _codex_installed(ctx, a["plugin"], a["marketplace"]):
        return "skip"
    return ctx.cli([ctx.codex, "plugin", "add", ref])


def _sync_codex_wrapper(src_dir: Path, dst: Path, *, path_rewrite: bool) -> None:
    """Copy a Claude-style wrapper dir into a Codex plugin dir: strip
    .claude-plugin, create .codex-plugin, copy every other file BOM-safe."""
    if dst.exists():
        shutil.rmtree(dst)
    (dst / ".codex-plugin").mkdir(parents=True)
    for f in src_dir.rglob("*"):
        if ".claude-plugin" in f.parts or f.is_dir():
            continue
        out = dst / f.relative_to(src_dir)
        if f.suffix == ".md":
            text = glue._read_text_utf8(f)
            if path_rewrite and f.name == "SKILL.md":
                text = glue.rewrite_gstack_paths(text)
            glue._write_text_utf8_no_bom(out, text)
        else:
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, out)


def _sync_codex_skills_tree(skills_src: Path, dst: Path, *, path_rewrite: bool) -> None:
    """gstack build output is a bare skills tree; place it under dst/skills."""
    if dst.exists():
        shutil.rmtree(dst)
    (dst / ".codex-plugin").mkdir(parents=True)
    skills_dst = dst / "skills"
    skills_dst.mkdir(parents=True)
    for f in skills_src.rglob("*"):
        if f.is_dir():
            continue
        out = skills_dst / f.relative_to(skills_src)
        if f.name == "SKILL.md":
            text = glue._read_text_utf8(f)
            if path_rewrite:
                text = glue.rewrite_gstack_paths(text)
            glue._write_text_utf8_no_bom(out, text)
        else:
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, out)


def h_codex_local(a: dict, ctx: Ctx) -> str:
    import json
    pid = _plugin_id(a)
    dst = ctx.home / ".codex/plugins" / pid
    if a.get("wrapper"):
        src = _expand(a["wrapper"], ctx)
        tree = False
    else:
        built = _expand(a["wrapper_from_build"], ctx)
        src = built if built.exists() else _expand(a["wrapper_fallback"], ctx)
        tree = True
    if not ctx.dry_run:
        if tree:
            _sync_codex_skills_tree(src, dst, path_rewrite=a.get("path_rewrite", False))
        else:
            _sync_codex_wrapper(src, dst, path_rewrite=a.get("path_rewrite", False))
        shutil.copy2(_expand(a["plugin_json"], ctx), dst / ".codex-plugin" / "plugin.json")
        mk_path = ctx.home / ".agents" / "plugins" / "marketplace.json"
        mk = json.loads(mk_path.read_text(encoding="utf-8"))
        if glue.codex_marketplace_upsert(mk, pid):
            mk_path.write_text(json.dumps(mk, indent=2, ensure_ascii=False), encoding="utf-8")
        if _codex_installed(ctx, pid, a["marketplace"]):
            return "skip"
    return ctx.cli([ctx.codex, "plugin", "add", f"{pid}@{a['marketplace']}"])


def h_external_cli(a: dict, ctx: Ctx) -> str:
    if ctx.dry_run:
        ctx.plan.append([ctx.python, "-m", "pip", "install", "--user", a["pip_package"]])
        return "ok"
    glue.pip_install(a["pip_package"], ctx.python)
    glue.make_shim(a["tool"], ctx.home / ".local" / "bin")
    return "ok"


def h_built_binary(a: dict, ctx: Ctx) -> str:
    dest = _expand(a["dest"], ctx)
    if ctx.dry_run:
        ctx.plan.append(["git", "clone", "--depth", "1", a["clone"], str(dest)])
        ctx.plan.append([a["builder"], "run", "build"])
        return "ok"
    if "bash" in a.get("needs", []) and not glue.ensure_bash():
        print("  WARN: bash unavailable; skipping build (fallback copy used)")
        return "skip"
    if not (dest / "browse").exists():
        glue.run_cli(["git", "clone", "--depth", "1", a["clone"], str(dest)])
    rc, _ = glue.run_cli([a["builder"], "install", "--frozen-lockfile"], cwd=str(dest))
    if rc != 0:
        glue.run_cli([a["builder"], "install"], cwd=str(dest))
    rc, err = glue.run_cli([a["builder"], "run", "build"], cwd=str(dest))
    return "ok" if rc == 0 else "fail"


HANDLERS = {
    "claude_marketplace": h_claude_marketplace,
    "claude_local": h_claude_local,
    "codex_store": h_codex_store,
    "codex_local": h_codex_local,
    "external_cli": h_external_cli,
    "built_binary": h_built_binary,
}
