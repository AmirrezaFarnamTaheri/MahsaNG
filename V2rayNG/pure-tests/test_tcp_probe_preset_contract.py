"""Contract: TCP presets affect socket connect only, never native proxy tests."""
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KOTLIN = ROOT / "app/src/main/kotlin/com/v2ray/ang"
RES = ROOT / "app/src/main/res"
ANDROID_NS = "{http://schemas.android.com/apk/res/android}"


class TcpProbePresetIntegrationTest(unittest.TestCase):
    def test_user_preset_is_wired_into_settings_storage_and_tcp_socket(self):
        tree = ET.parse(RES / "xml/pref_settings.xml")
        choices = [
            node for node in tree.getroot().iter("ListPreference")
            if node.get(ANDROID_NS + "key") == "pref_tcp_probe_preset"
        ]
        self.assertEqual(len(choices), 1)
        self.assertEqual(choices[0].get(ANDROID_NS + "defaultValue"), "balanced")
        app = (KOTLIN / "AppConfig.kt").read_text(encoding="utf-8")
        vm = (KOTLIN / "viewmodel/SettingsViewModel.kt").read_text(encoding="utf-8")
        speed = (KOTLIN / "util/SpeedtestUtil.kt").read_text(encoding="utf-8")
        self.assertIn('PREF_TCP_PROBE_PRESET = "pref_tcp_probe_preset"', app)
        self.assertIn("AppConfig.PREF_TCP_PROBE_PRESET,", vm)
        self.assertIn("TcpProbePreset.fromStored(", speed)
        self.assertIn("timeoutMs = timeoutMs,", speed)

    def test_udp_and_custom_profiles_are_skipped_before_tcp_connect(self):
        main = (KOTLIN / "viewmodel/MainViewModel.kt").read_text(encoding="utf-8")
        code = main.split("fun testAllTcping() {", 1)[1].split("fun testAllRealPing()", 1)[0]
        self.assertIn("TcpProbeEligibility.supportsTcpConnect(", code)
        self.assertLess(code.index("TcpProbeEligibility.supportsTcpConnect("),
                        code.index("SpeedtestUtil.tcping("))
        self.assertIn("MmkvManager.clearTestDelayResults(visibleGuids)", main)

    def test_native_http_and_proxy_methods_are_not_relabelled_as_tcp(self):
        speed = (KOTLIN / "util/SpeedtestUtil.kt").read_text(encoding="utf-8")
        native = speed.split("fun realPing(config: String)", 1)[1].split(
            "fun ping(url:", 1
        )[0]
        self.assertNotIn("TcpProbePreset", native)
        self.assertIn("Libv2ray.measureOutboundDelay(", native)

    def test_primary_language_resources_and_preset_values(self):
        for folder in ("values", "values-fa"):
            resources = ET.parse(RES / folder / "strings.xml")
            names = {x.attrib.get("name") for x in resources.getroot().findall("string")}
            for key in ("title_tcp_probe_preset", "tcp_probe_quick",
                        "tcp_probe_balanced", "tcp_probe_diagnostic"):
                self.assertIn(key, names)
        arrays = ET.parse(RES / "values/arrays.xml")
        values = next(node for node in arrays.getroot().findall("string-array")
                      if node.attrib.get("name") == "tcp_probe_preset_values")
        self.assertEqual([x.text for x in values.findall("item")],
                         ["quick", "balanced", "diagnostic"])


if __name__ == "__main__":
    unittest.main()
