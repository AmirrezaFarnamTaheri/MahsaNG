"""Verify bounded workers are wired to MahsaNG's actual bulk TCP path."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app/src/main"
NS = "{http://schemas.android.com/apk/res/android}"


class TcpBoundedBatchContract(unittest.TestCase):
    def test_bulk_tcp_testing_launches_only_fixed_workers(self):
        source = (APP / "kotlin/com/v2ray/ang/viewmodel/MainViewModel.kt").read_text(encoding="utf-8")
        method = source.split("fun testAllTcping() {", 1)[1].split("fun testAllRealPing()", 1)[0]
        self.assertIn("BoundedProbeQueue(", method)
        self.assertIn("repeat(queue.workerCount)", method)
        self.assertIn("queue.claim()", method)
        self.assertIn("testRuns.accepts(runId,", method)
        self.assertIn("MmkvManager.encodeServerTestDelayMillis(", method)
        self.assertIn("testRuns.publishIfCurrent(runId, guid)", method)
        self.assertIn("testRuns.publishIfCurrent(result.runId, result.guid)", source)
        self.assertNotIn("for (item in snapshot) {\n", method)

    def test_concurrency_is_a_saved_tcp_only_setting(self):
        source = (APP / "kotlin/com/v2ray/ang/viewmodel/MainViewModel.kt").read_text(encoding="utf-8")
        self.assertIn("PREF_TCP_PROBE_CONCURRENCY", source)
        settings = (APP / "kotlin/com/v2ray/ang/viewmodel/SettingsViewModel.kt").read_text(encoding="utf-8")
        self.assertIn("AppConfig.PREF_TCP_PROBE_CONCURRENCY,", settings)
        prefs = ET.parse(APP / "res/xml/pref_settings.xml").getroot()
        controls = [node for node in prefs.iter("ListPreference")
                    if node.get(NS + "key") == "pref_tcp_probe_concurrency"]
        self.assertEqual(len(controls), 1)
        self.assertEqual(controls[0].get(NS + "defaultValue"), "8")

    def test_no_unrelated_udp_or_native_probe_concurrency_setting(self):
        source = (APP / "kotlin/com/v2ray/ang/viewmodel/MainViewModel.kt").read_text(encoding="utf-8")
        real = source.split("fun testAllRealPing() {", 1)[1].split("fun testCurrentServerRealPing()", 1)[0]
        self.assertNotIn("PREF_TCP_PROBE_CONCURRENCY", real)
        self.assertNotIn("BoundedProbeQueue", real)


if __name__ == "__main__":
    unittest.main()
