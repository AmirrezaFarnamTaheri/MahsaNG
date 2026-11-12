"""Verify opt-in Psiphon mode and non-exported internal cross-process broadcasts."""
from pathlib import Path
from xml.etree import ElementTree as ET
import unittest

ROOT = Path(__file__).resolve().parents[1] / "app/src/main"
SOURCE = ROOT / "kotlin/com/v2ray/ang"


class PsiphonModeIntegrationContract(unittest.TestCase):
    def test_mode_entries_and_values_match(self):
        values = ET.parse(ROOT / "res/values/arrays.xml").getroot()
        labels = ET.parse(ROOT / "res/values/strings.xml").getroot()
        choices = [x.text for x in values.find("./string-array[@name='mode_value']")]
        titles = [x.text for x in labels.find("./string-array[@name='mode_entries']")]
        self.assertEqual(3, len(choices))
        self.assertEqual(3, len(titles))
        self.assertEqual("Psiphon via V2Ray", choices[2])
        self.assertIn("experimental", titles[2])

    def test_start_checks_permission_and_starts_both_processes(self):
        manager = (SOURCE / "service/V2RayServiceManager.kt").read_text()
        main = (SOURCE / "ui/MainActivity.kt").read_text()
        start = manager.split("fun startV2Ray(context: Context)", 1)[1].split(
            "private class V2RayCallback", 1
        )[0]
        self.assertIn("VpnService.prepare(context)", start)
        self.assertIn("VpnModeSelection.startsProxyProcess(mode)", start)
        self.assertIn("PsiphonVpnService::class.java", start)
        self.assertIn("VpnModeSelection.requiresVpnPermission", main)

    def test_psiphon_receives_stop_and_closes_upstream(self):
        psi = (SOURCE / "service/PsiphonVpnService.kt").read_text()
        self.assertIn("IntentFilter(AppConfig.BROADCAST_ACTION_SERVICE)", psi)
        self.assertIn("AppConfig.MSG_STATE_STOP", psi)
        self.assertIn("registerReceiver(stopReceiver, filter, Context.RECEIVER_NOT_EXPORTED)", psi)
        self.assertIn("unregisterReceiver(stopReceiver)", psi)
        self.assertIn("stopService(Intent(this, V2RayProxyOnlyService::class.java))", psi)
        self.assertIn("VpnService.prepare(this)", psi)
        self.assertIn("usesUpstreamProxy", psi)

    def test_internal_receivers_reject_external_broadcasts(self):
        manager = (SOURCE / "service/V2RayServiceManager.kt").read_text()
        vm = (SOURCE / "viewmodel/MainViewModel.kt").read_text()
        self.assertIn("service.registerReceiver(mMsgReceive, filter, Context.RECEIVER_NOT_EXPORTED)", manager)
        self.assertIn("app.registerReceiver(mMsgReceiver, filter, Context.RECEIVER_NOT_EXPORTED)", vm)
        self.assertIn("if (broadcastRegistered) return", vm)
        self.assertIn("if (broadcastRegistered) {", vm)
        self.assertIn("Build.VERSION_CODES.TIRAMISU", manager)
        self.assertIn("Build.VERSION_CODES.TIRAMISU", vm)


if __name__ == "__main__":
    unittest.main()
