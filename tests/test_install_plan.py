import sys, unittest, subprocess
from pathlib import Path
REPO = Path(__file__).resolve().parent.parent


class TestDryRunPlan(unittest.TestCase):
    def test_dry_run_lists_all_8_plugins(self):
        out = subprocess.run(
            [sys.executable, "scripts/install_plugins.py", "--dry-run"],
            cwd=REPO, capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        for pid in ["harness", "caveman", "superpowers", "codex",
                    "reply-trace", "gstack", "mattpocock-skills", "graphify"]:
            self.assertIn(pid, out.stdout)


if __name__ == "__main__":
    unittest.main()
