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


if __name__ == "__main__":
    unittest.main()
