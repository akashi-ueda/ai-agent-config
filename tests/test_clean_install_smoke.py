"""Clean-install smoke test (issue #23 part 2).

Regression guard for the two bugs a from-scratch install exposed:
  #16 - the personal-local directory marketplace was never registered, so its
        plugins could not install on a clean machine.
  #17 - a failed install was masked as skip/ok because only the enable result
        was returned.

Rather than a flaky CI job that needs the real claude/codex CLIs + network, this
drives the REAL engine (methods handlers + install_plugins.verify_installed)
against an in-process fake CLI. It runs in the normal `unittest discover` CI job,
deterministically and offline. Scope is personal-local — the part that broke.
"""
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from scripts.lib import glue, manifest, methods  # noqa: E402
import scripts.install_plugins as engine  # noqa: E402

PERSONAL_LOCAL_PLUGINS = {"gstack", "mattpocock-skills", "graphify", "refresh-plugins"}


class FakeCli:
    """Minimal stand-in for `claude`/`codex` plugin commands, backed by state.

    Faithful where it matters: a directory marketplace (personal-local) must be
    `marketplace add`-ed before its plugins resolve, mirroring the real CLI's
    "Plugin X not found in marketplace" failure that bug #16 hit."""

    DIR_MARKETPLACES = {"personal-local": PERSONAL_LOCAL_PLUGINS}

    def __init__(self):
        self.registered = set()      # marketplace names that were added
        self.installed = {}          # "plugin@mk" -> enabled(bool)

    @staticmethod
    def _mk_name(src: str) -> str:
        return src.replace("\\", "/").rstrip("/").split("/")[-1]

    def run_cli(self, args, dry_run=False, cwd=None):
        sub = args[2]
        if sub == "marketplace" and args[3] == "add":
            self.registered.add(self._mk_name(args[4]))
            return 0, ""
        if sub == "install":
            ref = args[3]
            plugin, mk = ref.split("@", 1)
            if mk in self.DIR_MARKETPLACES:
                if mk not in self.registered or plugin not in self.DIR_MARKETPLACES[mk]:
                    return 1, f'Plugin "{plugin}" not found in marketplace "{mk}"'
            self.installed.setdefault(ref, False)
            return 0, ""
        if sub == "enable":
            ref = args[3]
            if ref not in self.installed:
                return 1, f'Plugin "{ref}" is not installed'
            if self.installed[ref]:
                return 1, f'Plugin "{ref}" is already enabled'
            self.installed[ref] = True
            return 0, ""
        return 0, ""

    def run_capture(self, args, cwd=None):
        if args[2] == "list":
            out = ["Installed plugins:", ""]
            for ref, enabled in self.installed.items():
                out += [f"  ❯ {ref}",
                        f"    Status: {'✔ enabled' if enabled else '✘ disabled'}", ""]
            return 0, "\n".join(out)
        return 0, ""


class CleanInstallSmoke(unittest.TestCase):
    def setUp(self):
        self.fake = FakeCli()
        # idempotent_cli (in glue) calls the module-level run_cli; patch both it
        # and run_capture so the real handlers/verify run against the fake.
        self._patches = [
            mock.patch.object(glue, "run_cli", self.fake.run_cli),
            mock.patch.object(glue, "run_capture", self.fake.run_capture),
        ]
        for p in self._patches:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in self._patches])
        self.m = manifest.load_manifest(REPO / "manifest/plugins.json")
        self.ctx = methods.Ctx(repo=REPO, home=Path.home(), python="py")  # dry_run=False

    def _personal_local_actions(self):
        return [a for p in self.m["plugins"] for a in p["install"]
                if a["method"] == "claude_local"]

    def test_clean_install_registers_and_enables_all_personal_local(self):
        """The fixed engine registers the marketplace, so a from-empty run
        installs+enables every personal-local plugin (guards #16)."""
        for a in self._personal_local_actions():
            self.assertEqual(methods.h_claude_local(a, self.ctx), "ok")
        live = engine.parse_claude_installed(self.fake.run_capture(["claude", "plugin", "list"])[1])
        for plugin in PERSONAL_LOCAL_PLUGINS:
            self.assertIn(f"{plugin}@personal-local", live)

    def test_without_marketplace_registration_install_fails_loudly(self):
        """Simulate the pre-#16 engine (install/enable, no marketplace add):
        the install must fail AND surface as 'fail' (not masked, guards #17)."""
        status = methods._install_enable(self.ctx, "gstack@personal-local")
        self.assertEqual(status, "fail")
        self.assertNotIn("gstack@personal-local", self.fake.installed)

    def test_verify_installed_flags_incomplete_personal_local(self):
        """A partial install (one plugin missing) must be caught by the engine's
        post-install verification, not reported clean."""
        actions = self._personal_local_actions()
        for a in actions[:-1]:                       # install all but the last
            methods.h_claude_local(a, self.ctx)
        missing = engine.verify_installed(self.ctx, self.m, host="claude")["claude"]
        skipped = actions[-1]
        self.assertIn(f'{skipped["plugin"]}@{skipped["marketplace"]}', missing)


if __name__ == "__main__":
    unittest.main()
