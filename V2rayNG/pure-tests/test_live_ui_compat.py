"""Guard source-backed Android UI assets without manufacturing protocol options."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

RES = Path(__file__).resolve().parents[1] / "app/src/main/res"
ANDROID = "{http://schemas.android.com/apk/res/android}"

class LiveUiCompatibilityTests(unittest.TestCase):
    def test_snackbar_palette_and_icons_exist(self):
        palette = RES / "values/snackbar_compat.xml"
        names = {e.get("name") for e in ET.parse(palette).getroot().findall("color")}
        for name in ("snackbar_surface", "snackbar_success", "snackbar_title_text",
                     "snackbar_subtitle_text"):
            self.assertIn(name, names)
        for icon in ("ic_check", "ic_close"):
            root = ET.parse(RES / "drawable" / (icon + ".xml")).getroot()
            self.assertEqual("vector", root.tag)
            self.assertTrue(root.findall("path"))

    def test_captcha_ui_icons_are_nontextual_placeholders(self):
        for icon in ("sample_captcha", "refresh_captcha"):
            root = ET.parse(RES / "drawable" / (icon + ".xml")).getroot()
            self.assertEqual("vector", root.tag)
            self.assertTrue(root.findall("path"))

    def test_tv_about_uses_source_available_banner_and_button_shape(self):
        root = ET.parse(RES / "layout-television/activity_about.xml").getroot()
        references = {value for node in root.iter() for value in node.attrib.values()}
        self.assertIn("@mipmap/ic_banner", references)
        self.assertNotIn("@drawable/mahsa_banner", references)
        shape = ET.parse(RES / "drawable/bg_button_theme.xml").getroot()
        self.assertEqual("shape", shape.tag)

if __name__ == "__main__":
    unittest.main()
