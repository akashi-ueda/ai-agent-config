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


if __name__ == "__main__":
    unittest.main()
