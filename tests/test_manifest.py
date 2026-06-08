import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.lib import manifest

REPO = Path(__file__).resolve().parent.parent
KNOWN = {"claude_marketplace", "claude_local", "codex_store",
         "codex_local", "external_cli", "built_binary"}


class TestValidate(unittest.TestCase):
    def test_real_manifest_is_valid(self):
        m = manifest.load_manifest(REPO / "manifest/plugins.json")
        manifest.validate_manifest(m, KNOWN, REPO)  # must not raise

    def test_unknown_method_rejected(self):
        m = {"_schema": "personal-agent-config/plugins v1", "plugins": [
            {"id": "x", "repo": "a/b", "install": [{"method": "nope"}]}]}
        with self.assertRaises(manifest.ManifestError):
            manifest.validate_manifest(m, KNOWN, REPO)

    def test_missing_field_rejected(self):
        m = {"_schema": "personal-agent-config/plugins v1", "plugins": [
            {"id": "x", "install": []}]}
        with self.assertRaises(manifest.ManifestError):
            manifest.validate_manifest(m, KNOWN, REPO)

    def test_action_missing_required_key_rejected(self):
        # claude_marketplace requires source/marketplace/plugin; omit plugin
        m = {"_schema": "personal-agent-config/plugins v1", "plugins": [
            {"id": "x", "repo": "a/b", "install": [
                {"method": "claude_marketplace", "source": "a/b", "marketplace": "mk"}]}]}
        with self.assertRaisesRegex(manifest.ManifestError, "missing 'plugin'"):
            manifest.validate_manifest(m, KNOWN, REPO)


class TestOrphans(unittest.TestCase):
    def test_live_not_in_manifest_is_orphan(self):
        m = {"_schema": "personal-agent-config/plugins v1", "plugins": [
            {"id": "gstack", "repo": "a/b", "install": [
                {"method": "claude_local", "marketplace": "personal-local", "plugin": "gstack"}]}]}
        live = {"gstack", "attribution"}
        orphans = manifest.detect_orphans(m, live)
        self.assertEqual(orphans, {"attribution"})

    def test_no_orphans(self):
        m = {"_schema": "personal-agent-config/plugins v1", "plugins": [
            {"id": "gstack", "repo": "a/b", "install": [
                {"method": "claude_local", "marketplace": "personal-local", "plugin": "gstack"}]}]}
        self.assertEqual(manifest.detect_orphans(m, {"gstack"}), set())


if __name__ == "__main__":
    unittest.main()
