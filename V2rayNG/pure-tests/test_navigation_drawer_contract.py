"""The drawer should expose only destinations handled by MainActivity."""
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "app/src/main/res"
ACTIVITY = ROOT / "app/src/main/kotlin/com/v2ray/ang/ui/MainActivity.kt"
ANDROID = "{http://schemas.android.com/apk/res/android}"
DESTINATIONS = {"sub_setting", "settings", "user_asset_setting", "logcat"}


class NavigationDrawerTests(unittest.TestCase):
    def test_every_drawer_item_has_a_real_main_activity_handler(self):
        root = ET.parse(RES / "menu/menu_drawer.xml").getroot()
        choices = {
            element.get(ANDROID + "id", "").removeprefix("@+id/")
            for element in root.iter("item")
        }
        self.assertEqual(DESTINATIONS, choices)
        code = ACTIVITY.read_text(encoding="utf-8")
        navigation = code[code.index("override fun onNavigationItemSelected"): ]
        for item in choices:
            self.assertRegex(navigation, r"R\\.id\\." + re.escape(item) + r"\\s*->")

    def test_archived_original_remains_available_for_full_feature_restoration(self):
        archived = ROOT / "docs/unimplemented-ui/menu-orphans/menu_drawer_original.xml"
        self.assertTrue(archived.is_file())
        root = ET.parse(archived).getroot()
        self.assertGreaterEqual(sum(1 for _ in root.iter("item")), 20)


if __name__ == "__main__":
    unittest.main()
