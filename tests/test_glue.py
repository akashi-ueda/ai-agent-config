import sys, unittest, tempfile, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.lib import glue


class TestBomSafeCopy(unittest.TestCase):
    def test_strips_bom_and_preserves_utf8(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "src.md"
            dst = Path(d) / "out" / "dst.md"
            src.write_text("﻿---\nname: x — y\n", encoding="utf-8")
            glue.bom_safe_copy(src, dst)
            raw = dst.read_bytes()
            self.assertEqual(raw[:3], b"---")
            self.assertIn("—", dst.read_text(encoding="utf-8"))


class TestIdempotentCli(unittest.TestCase):
    def test_already_enabled_stderr_is_success(self):
        self.assertTrue(glue.is_benign_already("× Failed: Plugin is already enabled"))
        self.assertTrue(glue.is_benign_already("already installed (scope: user)"))
        self.assertFalse(glue.is_benign_already("network error: timed out"))


class TestPipMode(unittest.TestCase):
    def test_prefers_standalone_then_falls_back_to_python_m_pip(self):
        cmd = glue.pip_command(has_standalone_pip=True, python="py")
        self.assertEqual(cmd, ["pip"])
        cmd = glue.pip_command(has_standalone_pip=False, python="py")
        self.assertEqual(cmd, ["py", "-m", "pip"])


class TestMakeShim(unittest.TestCase):
    def test_resolves_versioned_user_scripts(self):
        import sysconfig
        got = glue.user_scripts_dir()
        self.assertEqual(got, sysconfig.get_path("scripts", glue._user_scheme()))


class TestRewriteGstackPaths(unittest.TestCase):
    def test_rewrites_install_paths_without_mangling_root(self):
        text = (
            'GSTACK_ROOT="$HOME/.agents/skills/gstack"\n'
            '[ -d "$_ROOT/.agents/skills/gstack" ] && X=1\n'
            'Y="$HOME/.codex/skills/gstack/bin"\n'
        )
        out = glue.rewrite_gstack_paths(text)
        self.assertIn('GSTACK_ROOT="$HOME/.gstack/core"', out)
        self.assertIn('"$_ROOT/.gstack/core"', out)
        self.assertNotIn("$_ROOT/$HOME", out)
        self.assertIn('Y="$HOME/.gstack/core/bin"', out)
        self.assertNotIn(".agents/skills/gstack", out)


import json as _json

class TestMarketplaceUpsert(unittest.TestCase):
    def _mk(self):
        return {"name": "personal", "plugins": [
            {"name": "gstack", "source": {"source": "local", "path": "./.codex/plugins/gstack"}}
        ]}

    def test_adds_missing_entry_once(self):
        mk = self._mk()
        changed = glue.codex_marketplace_upsert(mk, "reply-trace")
        self.assertTrue(changed)
        names = [p["name"] for p in mk["plugins"]]
        self.assertEqual(names.count("reply-trace"), 1)
        changed2 = glue.codex_marketplace_upsert(mk, "reply-trace")
        self.assertFalse(changed2)
        self.assertEqual([p["name"] for p in mk["plugins"]].count("reply-trace"), 1)


class TestRunCliUtf8(unittest.TestCase):
    def test_decodes_utf8_output_without_raising(self):
        # subprocess output containing non-ASCII (✓, —, 한글) must not crash
        # under the Windows locale codec; run_cli forces UTF-8 decoding.
        # child emits raw UTF-8 bytes regardless of its locale; the PARENT
        # (run_cli) must decode them without raising.
        code = "import sys; sys.stdout.buffer.write('✓ — 한글'.encode('utf-8'))"
        rc, err = glue.run_cli([sys.executable, "-c", code])
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
