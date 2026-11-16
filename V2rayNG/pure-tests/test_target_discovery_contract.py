"""Target-first scanner is opt-in, bounded, cancellable and separate from VPN state."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1] / "app/src/main"
UI = ROOT / "kotlin/com/v2ray/ang/ui"
VM = ROOT / "kotlin/com/v2ray/ang/viewmodel"
ANDROID = "{http://schemas.android.com/apk/res/android}"


class TargetDiscoveryContractTest(unittest.TestCase):
    def test_new_activity_is_private_and_launched_only_on_user_menu_action(self):
        manifest = ET.parse(ROOT / "AndroidManifest.xml")
        activities = [node for node in manifest.iter("activity")
            if node.attrib.get(f"{ANDROID}name") == ".ui.TargetDiscoveryActivity"]
        self.assertEqual(1, len(activities))
        self.assertEqual("false", activities[0].attrib.get(f"{ANDROID}exported"))
        menu = (ROOT / "res/menu/menu_main.xml").read_text()
        main = (UI / "MainActivity.kt").read_text()
        self.assertIn('@+id/target_discovery_scan', menu)
        self.assertIn("R.id.target_discovery_scan ->", main)
        self.assertIn("Intent(this, TargetDiscoveryActivity::class.java)", main)

    def test_scanner_uses_bounded_workers_and_network_epoch_gate(self):
        source = (UI / "TargetDiscoveryActivity.kt").read_text()
        self.assertIn("BoundedProbeQueue(", source)
        self.assertIn("RunNetworkObserver.register(", source)
        self.assertIn("observer.isCurrent()", source)
        self.assertIn("TargetSocketLease()", source)
        self.assertIn("lease?.stop()", source)
        self.assertIn("owner.stop()", source)
        self.assertIn("job?.cancel()", source)
        self.assertIn("lifecycleScope.launch", source)
        self.assertIn("TargetDiscoveryPlanner.plan(", source)

    def test_ui_does_not_change_profile_selection_or_vpn_service_state(self):
        source = (UI / "TargetDiscoveryActivity.kt").read_text()
        for unsafe in ("KEY_SELECTED_SERVER", "startV2Ray(", "stopVService(",
                       "MmkvManager.encodeServer", "VpnService.protect("):
            self.assertNotIn(unsafe, source)

    def test_scanner_has_offline_localized_help(self):
        source = (UI / "ContextualHelp.kt").read_text()
        self.assertIn("R.id.target_discovery_scan to HelpTopic(", source)
        self.assertIn("R.id.target_discovery_scan,", source)
        for locale in ("values", "values-fa"):
            xml = ET.parse(ROOT / "res" / locale / "contextual_help.xml")
            blocks = [node for node in xml.findall("string-array")
                      if node.attrib.get("name") == "help_target_discovery"]
            self.assertEqual(1, len(blocks), locale)
            self.assertEqual(5, len(blocks[0]))


if __name__ == "__main__":
    unittest.main()
