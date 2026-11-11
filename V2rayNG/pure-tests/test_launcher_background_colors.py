"""Protect launcher adaptive-icon background color references.

Historical upstream files incorrectly placed <resources> in res/color/, which
expects a color state-list. The integration PR removed those files without
replacing their @color names, breaking both adaptive launcher images.
"""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

RES = Path(__file__).resolve().parents[1] / "app/src/main/res"

class LauncherBackgroundColorTests(unittest.TestCase):
    def test_both_adaptive_icon_backgrounds_resolve_to_values_colors(self):
        defined = {}
        for path in (RES / "values").glob("*.xml"):
            root = ET.parse(path).getroot()
            if root.tag == "resources":
                for entry in root.findall("color"):
                    defined[entry.get("name")] = (entry.text or "").strip()
        for icon, color in (
            ("ic_launcher", "ic_launcher_background"),
            ("ic_banner", "ic_banner_background"),
        ):
            with self.subTest(icon=icon):
                root = ET.parse(RES / "mipmap-anydpi-v26" / (icon + ".xml")).getroot()
                android = "{http://schemas.android.com/apk/res/android}"
                backgrounds = root.findall("background")
                self.assertEqual(1, len(backgrounds))
                self.assertEqual("@color/" + color, backgrounds[0].get(android + "drawable"))
                self.assertIn(color, defined)
                self.assertEqual("#FFFFFF", defined[color])

    def test_color_resources_are_not_misplaced_in_drawable_color_directory(self):
        for name in ("ic_launcher_background", "ic_banner_background"):
            with self.subTest(resource=name):
                self.assertFalse((RES / "color" / (name + ".xml")).exists())

if __name__ == "__main__":
    unittest.main()
