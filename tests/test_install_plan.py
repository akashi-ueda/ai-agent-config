import sys, unittest, subprocess
from pathlib import Path
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
import scripts.install_plugins as engine  # noqa: E402


class TestParsePersonalIds(unittest.TestCase):
    def test_extracts_personal_ids_only(self):
        out = (
            "Marketplace `personal`\n"
            "gstack@personal             installed, enabled  0.1.0  C:\\x\n"
            "reply-trace@personal        installed, enabled  0.1.0  C:\\y\n"
            "Marketplace `openai-curated`\n"
            "superpowers@openai-curated  installed, enabled  9c1  C:\\z\n"
        )
        self.assertEqual(engine.parse_codex_personal_ids(out),
                         {"gstack", "reply-trace"})

    def test_empty_on_no_personal(self):
        self.assertEqual(engine.parse_codex_personal_ids(""), set())


class TestDryRunPlan(unittest.TestCase):
    def test_dry_run_lists_all_8_plugins(self):
        out = subprocess.run(
            [sys.executable, "scripts/install_plugins.py", "--dry-run"],
            cwd=REPO, capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        for pid in ["harness", "caveman", "superpowers", "codex",
                    "reply-trace", "gstack", "mattpocock-skills", "graphify"]:
            self.assertIn(pid, out.stdout)


class TestActionHosts(unittest.TestCase):
    def test_method_bound_hosts(self):
        self.assertEqual(engine.action_hosts({"method": "claude_local"}), {"claude"})
        self.assertEqual(engine.action_hosts({"method": "codex_local"}), {"codex"})

    def test_external_defaults_to_both(self):
        self.assertEqual(engine.action_hosts({"method": "external_cli"}),
                         {"claude", "codex"})

    def test_external_host_tag_respected(self):
        self.assertEqual(engine.action_hosts(
            {"method": "built_binary", "host": "codex"}), {"codex"})


class TestHostScopedDryRun(unittest.TestCase):
    def test_host_claude_keeps_external_drops_codex(self):
        out = subprocess.run(
            [sys.executable, "scripts/install_plugins.py", "--dry-run", "--host", "claude"],
            cwd=REPO, capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("external_cli", out.stdout)   # graphify CLI (host: both)
        self.assertNotIn("codex_local", out.stdout)
        self.assertNotIn("codex_store", out.stdout)


if __name__ == "__main__":
    unittest.main()
