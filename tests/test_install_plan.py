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


class TestParseClaudeInstalled(unittest.TestCase):
    SAMPLE = (
        "Installed plugins:\n\n"
        "  ❯ caveman@caveman\n"
        "    Version: 655b7d9c5431\n"
        "    Scope: user\n"
        "    Status: ✔ enabled\n\n"
        "  ❯ gstack@personal-local\n"
        "    Version: 0.1.0\n"
        "    Status: ✘ disabled\n"
    )

    def test_collects_only_enabled_refs(self):
        refs = engine.parse_claude_installed(self.SAMPLE)
        self.assertIn("caveman@caveman", refs)
        self.assertNotIn("gstack@personal-local", refs)  # disabled

    def test_empty_output(self):
        self.assertEqual(engine.parse_claude_installed(""), set())


class TestExpectedRefs(unittest.TestCase):
    M = {"plugins": [
        {"id": "a", "install": [
            {"method": "claude_marketplace", "plugin": "a", "marketplace": "mk"},
            {"method": "codex_store", "plugin": "a", "marketplace": "openai-curated"},
        ]},
        {"id": "g", "install": [
            {"method": "claude_local", "plugin": "g", "marketplace": "personal-local"},
            {"method": "external_cli", "plugin": "g", "tool": "g", "pip_package": "gg"},
            {"method": "codex_local", "plugin": "g", "marketplace": "personal"},
        ]},
    ]}

    def test_groups_refs_by_host_excluding_external(self):
        refs = engine.expected_refs(self.M)
        self.assertEqual(refs["claude"], {"a@mk", "g@personal-local"})
        self.assertEqual(refs["codex"], {"a@openai-curated", "g@personal"})

    def test_host_filter(self):
        self.assertEqual(set(engine.expected_refs(self.M, "claude")), {"claude"})


class TestVerifyManifestSelfConsistent(unittest.TestCase):
    """The real manifest's expected claude refs must match what a full install
    would enable (guards against a manifest plugin with no resolvable ref)."""

    def test_real_manifest_expected_refs_nonempty(self):
        import scripts.lib.manifest as mani
        m = mani.load_manifest(REPO / "manifest/plugins.json")
        refs = engine.expected_refs(m)
        self.assertIn("gstack@personal-local", refs["claude"])
        self.assertIn("graphify@personal-local", refs["claude"])
        self.assertTrue(refs["codex"])


if __name__ == "__main__":
    unittest.main()
