import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
import scripts.reset as reset  # noqa: E402

# Paths that MUST survive a reset (auth + history). If any is equal to or nested
# under a delete path, the reset would destroy it.
KEEP = {
    "claude": [reset.CLAUDE / ".credentials.json", reset.CLAUDE / "projects",
               reset.CLAUDE / "sessions", reset.CLAUDE / "shell-snapshots",
               reset.CLAUDE / "plugins" / "data"],
    "codex": [reset.CODEX / "auth.json", reset.CODEX / "config.toml",
              reset.CODEX / "sessions", reset.CODEX / "node_repl",
              reset.CODEX / "logs_2.sqlite", reset.CODEX / "memories_1.sqlite"],
}


class TestDeleteListSafety(unittest.TestCase):
    def test_no_keep_path_is_removed(self):
        for host, (_home, delete, _keep) in reset.HOSTS.items():
            for sentinel in KEEP[host]:
                ancestors = {sentinel, *sentinel.parents}
                for d in delete:
                    self.assertNotIn(
                        d, ancestors,
                        f"{host}: delete path {d} would remove kept {sentinel}")

    def test_delete_paths_under_agent_home(self):
        for _host, (home, delete, _keep) in reset.HOSTS.items():
            for d in delete:
                self.assertIn(home, d.parents, f"{d} not under {home}")


class TestHostsArg(unittest.TestCase):
    def test_single_and_both(self):
        self.assertEqual(reset.hosts_arg(["--host", "claude"]), ["claude"])
        self.assertEqual(reset.hosts_arg(["--host", "codex"]), ["codex"])
        self.assertEqual(reset.hosts_arg(["--host", "both"]), ["claude", "codex"])

    def test_missing_or_bad(self):
        self.assertIsNone(reset.hosts_arg(["--dry-run"]))
        self.assertIsNone(reset.hosts_arg(["--host", "bogus"]))
        self.assertIsNone(reset.hosts_arg(["--host"]))


class TestConfirm(unittest.TestCase):
    def test_yes_flag_bypasses(self):
        self.assertTrue(reset.confirm(["claude"], yes=True, dry=False))

    def test_dry_bypasses(self):
        self.assertTrue(reset.confirm(["claude"], yes=False, dry=True))

    def test_noninteractive_without_yes_refuses(self):
        # under unittest stdin is not a tty -> must refuse
        self.assertFalse(reset.confirm(["claude"], yes=False, dry=False))


class TestBackupAndDelete(unittest.TestCase):
    def _make(self, home):
        (home / "CLAUDE.md").write_text("x", encoding="utf-8")
        (home / "tools").mkdir()
        (home / "tools" / "t.py").write_text("y", encoding="utf-8")
        (home / ".credentials.json").write_text("secret", encoding="utf-8")

    def test_backs_up_then_deletes_managed_keeps_rest(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d) / ".claude"
            home.mkdir()
            self._make(home)
            backup = Path(d) / "backup"
            paths = [home / "CLAUDE.md", home / "tools", home / "missing"]
            n = reset.backup_and_delete(home, paths, backup, dry=False)
            self.assertEqual(n, 2)                                   # missing skipped
            self.assertFalse((home / "CLAUDE.md").exists())          # deleted
            self.assertFalse((home / "tools").exists())
            self.assertTrue((home / ".credentials.json").exists())   # kept
            self.assertEqual((backup / "CLAUDE.md").read_text(encoding="utf-8"), "x")
            self.assertEqual((backup / "tools" / "t.py").read_text(encoding="utf-8"), "y")

    def test_dry_run_touches_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d) / ".claude"
            home.mkdir()
            self._make(home)
            backup = Path(d) / "backup"
            reset.backup_and_delete(home, [home / "CLAUDE.md"], backup, dry=True)
            self.assertTrue((home / "CLAUDE.md").exists())           # intact
            self.assertFalse(backup.exists())


if __name__ == "__main__":
    unittest.main()
