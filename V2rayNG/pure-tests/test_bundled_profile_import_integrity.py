"""Bundled GFW profile import must preserve the user's existing local profiles."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / "app/src/main"
ACTIVITY = ROOT / "java/com/v2ray/ang/GFW_youtube_config_Activity.java"
CONFIG_MANAGER = ROOT / "kotlin/com/v2ray/ang/util/AngConfigManager.kt"


class BundledProfileImportIntegrityTest(unittest.TestCase):
    def test_button_appends_instead_of_replacing_local_group(self):
        activity = ACTIVITY.read_text(encoding="utf-8")
        self.assertIn(
            "AngConfigManager.INSTANCE.importBatchConfig(server, mahsa_subid, true)", activity
        )
        self.assertNotIn(
            "AngConfigManager.INSTANCE.importBatchConfig(server, mahsa_subid, false)", activity
        )

    def test_replace_subscriptions_is_only_used_on_explicit_nonappend_path(self):
        source = CONFIG_MANAGER.read_text(encoding="utf-8")
        func = source.split("fun importBatchConfig(servers: String?, subid: String, append: Boolean)", 1)[1].split(
            "fun importSubscription(", 1
        )[0]
        self.assertIn("if (!append && subid.isNotBlank())", func)
        self.assertIn("MmkvManager.replaceSubscriptionServers(subid, staged)", func)


if __name__ == "__main__":
    unittest.main()
