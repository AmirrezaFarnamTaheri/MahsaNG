"""Safety wiring contract for optional, read-only multi-pass TCP diagnostics."""
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1] / "app" / "src" / "main"
MAIN = ROOT / "kotlin" / "com" / "v2ray" / "ang"
ANDROID = "{http://schemas.android.com/apk/res/android}"

class AdvancedTcpRetryContractTest(unittest.TestCase):
    def test_entry_is_explicit_and_activity_not_exported(self):
        menu = ET.parse(ROOT / "res" / "menu" / "menu_main.xml")
        self.assertTrue(any(
            item.get(f"{ANDROID}id") == "@+id/advanced_tcp_retry"
            for item in menu.iter("item")
        ))
        manifest = ET.parse(ROOT / "AndroidManifest.xml")
        activities = [
            node for node in manifest.iter("activity")
            if node.get(f"{ANDROID}name") == ".ui.AdvancedTcpRetryActivity"
        ]
        self.assertEqual(1, len(activities))
        self.assertEqual("false", activities[0].get(f"{ANDROID}exported"))

    def test_localized_prompts_and_explicit_budget_confirm(self):
        names = []
        for lang in ("values", "values-fa"):
            resources = ET.parse(ROOT / "res" / lang / "advanced_retry_strings.xml")
            localized = {node.get("name") for node in resources.findall(".//string")}
            self.assertGreaterEqual(len(localized), 20)
            names.append(localized)
        self.assertEqual(names[0], names[1])
        ui = (MAIN / "ui" / "AdvancedTcpRetryActivity.kt").read_text()
        self.assertIn("showBudgetConfirmation()", ui)
        self.assertIn("advanced_retry_budget", ui)
        self.assertIn("model.startPrepared()", ui)

    def test_run_does_not_modify_storage_or_trigger_delete(self):
        for filename in (
            MAIN / "util" / "AdvancedRetryScheduler.kt",
            MAIN / "util" / "AdvancedTcpRetrySession.kt",
            MAIN / "viewmodel" / "AdvancedTcpRetryViewModel.kt",
            MAIN / "ui" / "AdvancedTcpRetryActivity.kt",
        ):
            source = filename.read_text()
            self.assertNotRegex(source, r"MmkvManager\.(?:remove|encode|clear|sort)")
            self.assertNotIn("removeConfirmedFailedServers", source)
            self.assertNotIn("removeAllServer", source)

    def test_retry_run_snapshots_hashed_revisions_not_raw_credentials(self):
        viewmodel = (MAIN / "viewmodel" / "AdvancedTcpRetryViewModel.kt").read_text()
        self.assertIn("ProfileRevisionDigest.fromSerializedConfig(gson.toJson(config))", viewmodel)
        self.assertIn("ProfileRevisionDigest.fromSerializedConfig(Gson().toJson(it))", viewmodel)
        self.assertNotIn("AdvancedRetryTarget(guid, gson.toJson(config)", viewmodel)
        self.assertIn("currentRevision = lookupRevision", viewmodel)

    def test_network_handover_guard_is_registered_and_released(self):
        observer = (MAIN / "util" / "RunNetworkObserver.kt").read_text()
        viewmodel = (MAIN / "viewmodel" / "AdvancedTcpRetryViewModel.kt").read_text()
        self.assertIn("registerDefaultNetworkCallback(observer)", observer)
        self.assertIn("registerNetworkCallback(request, observer)", observer)
        self.assertIn("gate.onAvailable(network)", observer)
        self.assertIn("gate.onLost(network)", observer)
        self.assertIn("gate.invalidate()", observer)
        self.assertIn("unregisterNetworkCallback(callback)", observer)
        self.assertIn("RunNetworkObserver.register(app)", viewmodel)
        self.assertIn("networkStillCurrent = { observer.isCurrent() }", viewmodel)
        self.assertIn("networkObserver?.close()", viewmodel)
        self.assertIn("RetryRunPhase.FINISHED", viewmodel)
        self.assertNotIn("initialNetwork != null &&", viewmodel)

if __name__ == "__main__":
    unittest.main()
