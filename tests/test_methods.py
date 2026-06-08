import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.lib import methods


class TestRegistry(unittest.TestCase):
    def test_all_methods_registered(self):
        self.assertEqual(set(methods.HANDLERS), {
            "claude_marketplace", "claude_local", "codex_store",
            "codex_local", "external_cli", "built_binary"})

    def test_claude_marketplace_plan(self):
        ctx = methods.Ctx(repo=Path("."), home=Path.home(), python="py",
                          claude="claude", codex="codex", dry_run=True, plan=[])
        action = {"method": "claude_marketplace", "source": "a/b",
                  "marketplace": "mk", "plugin": "p"}
        methods.HANDLERS["claude_marketplace"](action, ctx)
        self.assertIn(["claude", "plugin", "marketplace", "add", "a/b"], ctx.plan)
        self.assertIn(["claude", "plugin", "install", "p@mk"], ctx.plan)
        self.assertIn(["claude", "plugin", "enable", "p@mk"], ctx.plan)


import tempfile, json


class TestCodexLocalSync(unittest.TestCase):
    def test_sync_wrapper_strips_bom_and_claude_plugin(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "wrap"
            (src / "skills" / "x").mkdir(parents=True)
            (src / "skills" / "x" / "SKILL.md").write_text("﻿---\nname: x\n", encoding="utf-8")
            (src / ".claude-plugin").mkdir()
            (src / ".claude-plugin" / "marketplace.json").write_text("{}", encoding="utf-8")
            dst = Path(d) / "out"
            methods._sync_codex_wrapper(src, dst, path_rewrite=False)
            sk = dst / "skills" / "x" / "SKILL.md"
            self.assertEqual(sk.read_bytes()[:3], b"---")           # no BOM
            self.assertFalse((dst / ".claude-plugin").exists())     # stripped
            self.assertTrue((dst / ".codex-plugin").exists())       # created

    def test_sync_skills_tree_places_under_skills(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "gen"
            (src / "gstack-x").mkdir(parents=True)
            (src / "gstack-x" / "SKILL.md").write_text("﻿---\nname: y\n.agents/skills/gstack\n", encoding="utf-8")
            dst = Path(d) / "out"
            methods._sync_codex_skills_tree(src, dst, path_rewrite=True)
            sk = dst / "skills" / "gstack-x" / "SKILL.md"
            self.assertEqual(sk.read_bytes()[:3], b"---")
            self.assertIn("$HOME/.gstack/core", sk.read_text(encoding="utf-8"))


class TestCodexLocalHandler(unittest.TestCase):
    def test_dry_run_plans_codex_add(self):
        ctx = methods.Ctx(repo=Path("."), home=Path.home(), python="py", dry_run=True, plan=[])
        a = {"method": "codex_local", "wrapper": "codex/caveman-plugin",
             "plugin": "caveman", "plugin_json": "codex/plugin-json/caveman.json",
             "marketplace": "personal"}
        out = methods.h_codex_local(a, ctx)
        self.assertEqual(out, "ok")
        self.assertIn(["codex", "plugin", "add", "caveman@personal"], ctx.plan)


class TestCodexInstalledParse(unittest.TestCase):
    def test_detects_installed_ref(self):
        out = ("gstack@personal             installed, enabled  0.1.0  C:\\x\n"
               "graphify@personal           installed, enabled  0.1.0  C:\\y\n")
        self.assertTrue(methods._is_installed_in_list(out, "gstack", "personal"))
        self.assertFalse(methods._is_installed_in_list(out, "reply-trace", "personal"))

    def test_not_installed_when_absent(self):
        self.assertFalse(methods._is_installed_in_list("", "gstack", "personal"))

    def test_not_installed_status_is_not_installed(self):
        out = "reply-trace@personal        not installed           C:\\x\n"
        self.assertFalse(methods._is_installed_in_list(out, "reply-trace", "personal"))


class TestExternalCli(unittest.TestCase):
    def test_dry_run_plans_pip_install(self):
        ctx = methods.Ctx(repo=Path("."), home=Path.home(), python="py",
                          dry_run=True, plan=[])
        a = {"method": "external_cli", "tool": "graphify", "pip_package": "graphifyy"}
        out = methods.h_external_cli(a, ctx)
        self.assertEqual(out, "ok")
        self.assertTrue(any("graphifyy" in " ".join(map(str, c)) for c in ctx.plan))


class TestBuiltBinary(unittest.TestCase):
    def test_dry_run_plans_clone_and_build(self):
        ctx = methods.Ctx(repo=Path("."), home=Path.home(), python="py",
                          dry_run=True, plan=[])
        a = {"method": "built_binary", "clone": "https://x/gstack",
             "dest": "~/.gstack/core", "builder": "bun", "needs": ["bash"]}
        out = methods.h_built_binary(a, ctx)
        self.assertIn(out, ("ok", "skip"))
        joined = [" ".join(map(str, c)) for c in ctx.plan]
        self.assertTrue(any("bun" in j for j in joined))


if __name__ == "__main__":
    unittest.main()
