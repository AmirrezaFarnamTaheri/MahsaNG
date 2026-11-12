"""Lock Psiphon settings selectors to the only defaults proven by source.

Do not synthesize unknown protocol codes or region IDs: the original option
arrays are absent in the published upstream and fork base. These known values
are explicitly consumed by GFW_psiphonSettings_Activity.
"""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

APP = Path(__file__).resolve().parents[1] / "app/src/main"
ACTIVITY = APP / "java/com/v2ray/ang/GFW_psiphonSettings_Activity.java"
LAYOUT = APP / "res/layout/activity_gfw_psiphon_settings.xml"
ARRAYS = APP / "res/values/psiphon_verified_defaults.xml"
ANDROID = "{http://schemas.android.com/apk/res/android}"

class PsiphonSettingsContractTest(unittest.TestCase):
    def test_backed_activity_and_layout_exist(self):
        self.assertTrue(ACTIVITY.is_file())
        self.assertTrue(LAYOUT.is_file())
        activity = ACTIVITY.read_text(encoding="utf-8")
        self.assertIn('setContentView(R.layout.activity_gfw_psiphon_settings)', activity)

    def test_values_are_only_source_verified_defaults(self):
        activity = ACTIVITY.read_text(encoding="utf-8")
        expected = {
            "psiphon_country_list": ("Auto", "psiphon_country_code"),
            "psiphon_protocol_list": ("auto", "psiphon_protocol"),
            "psiphon_aggressive_list": ("OFF", "psiphon_aggressive"),
        }
        root = ET.parse(ARRAYS).getroot()
        arrays = {element.get("name"): [n.text for n in element.findall("item")]
                  for element in root.findall("string-array")}
        layout = ET.parse(LAYOUT).getroot()
        entries = {node.get(ANDROID + "entries") for node in layout.iter()}
        for name, (value, pref) in expected.items():
            with self.subTest(name=name):
                self.assertIn('@array/' + name, entries)
                self.assertEqual([value], arrays[name])
                self.assertIn('get_value("' + pref + '","' + value + '")', activity)

if __name__ == "__main__":
    unittest.main()
