"""MainActivity must bind a real determinate/indeterminate progress control."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1] / "app/src/main"
ANDROID = "{http://schemas.android.com/apk/res/android}"

class MainProgressContractTest(unittest.TestCase):
    def test_main_layout_supplies_real_loading_spinner(self):
        root = ET.parse(ROOT / "res/layout/activity_main.xml").getroot()
        controls = [n for n in root.iter()
                    if n.get(ANDROID+"id") == "@+id/fab_progress_circle"]
        self.assertEqual(1, len(controls))
        self.assertEqual("ProgressBar", controls[0].tag)
        self.assertEqual("gone", controls[0].get(ANDROID+"visibility"))

    def test_main_activity_toggles_spinner_visibility(self):
        text = (ROOT / "kotlin/com/v2ray/ang/ui/MainActivity.kt").read_text(encoding="utf-8")
        self.assertIn("binding.fabProgressCircle.visibility = View.VISIBLE", text)
        self.assertIn("binding.fabProgressCircle.visibility = View.GONE", text)

if __name__ == "__main__":
    unittest.main()
