import sys, unittest, subprocess
from pathlib import Path
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
import scripts.apply as apply_mod  # noqa: E402


class TestHostArg(unittest.TestCase):
    def test_parses_host(self):
        self.assertEqual(apply_mod.host_arg(["x", "--host", "claude"]), "claude")
        self.assertEqual(apply_mod.host_arg(["x", "--host", "codex"]), "codex")

    def test_absent_is_none(self):
        self.assertIsNone(apply_mod.host_arg(["x", "--dry-run"]))


class TestApplyHostDryRun(unittest.TestCase):
    """--host scopes the file apply to one agent; dry-run logs which files it
    would place, so absence of the other host's files proves the scoping."""

    def _run(self, *extra):
        return subprocess.run(
            [sys.executable, "scripts/apply.py", "--dry-run", *extra],
            cwd=REPO, capture_output=True, text=True)

    def test_host_claude_skips_codex(self):
        out = self._run("--host", "claude")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("CLAUDE.md", out.stdout)
        self.assertNotIn("AGENTS.md", out.stdout)

    def test_host_codex_skips_claude(self):
        out = self._run("--host", "codex")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("AGENTS.md", out.stdout)
        self.assertNotIn("CLAUDE.md", out.stdout)

    def test_default_applies_both(self):
        out = self._run()
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("CLAUDE.md", out.stdout)
        self.assertIn("AGENTS.md", out.stdout)

    def test_unknown_host_errors(self):
        out = self._run("--host", "bogus")
        self.assertEqual(out.returncode, 2)


if __name__ == "__main__":
    unittest.main()
