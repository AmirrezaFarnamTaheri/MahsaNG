"""Source-contract checks: every public drawer/menu action has offline localized help."""
import pathlib
import re
import unittest
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1] / "app" / "src" / "main"
UI = ROOT / "kotlin" / "com" / "v2ray" / "ang" / "ui"
ANDROID = "{http://schemas.android.com/apk/res/android}"


class ContextualHelpContractTest(unittest.TestCase):
    def test_every_visible_drawer_and_main_menu_action_has_a_help_topic(self):
        source = (UI / "ContextualHelp.kt").read_text(encoding="utf-8")
        mapped = set(re.findall(r"R\.id\.(\w+)\s+to\s+HelpTopic\(", source))
        for filename in ("menu_drawer.xml", "menu_main.xml"):
            menu = ET.parse(ROOT / "res" / "menu" / filename)
            visible_ids = {
                item.attrib[f"{ANDROID}id"].split("/")[-1]
                for item in menu.iter("item")
                if f"{ANDROID}id" in item.attrib
            }
            self.assertFalse(
                visible_ids - mapped,
                f"{filename}: help missing for {visible_ids - mapped}",
            )

    def test_english_and_persian_have_the_same_five_help_blocks(self):
        all_topics = []
        for lang in ("values", "values-fa"):
            xml = ET.parse(ROOT / "res" / lang / "contextual_help.xml")
            arrays = {
                node.attrib["name"]: list(node)
                for node in xml.findall(".//string-array")
            }
            self.assertGreaterEqual(len(arrays), 15)
            for name, values in arrays.items():
                self.assertEqual(5, len(values), f"{lang}/{name}")
                self.assertTrue(all((value.text or "").strip() for value in values))
            all_topics.append(set(arrays))
        self.assertEqual(all_topics[0], all_topics[1])

    def test_every_drawer_destination_exposes_toolbar_help(self):
        for activity in (
            "SubSettingActivity", "SettingsActivity",
            "UserAssetActivity", "LogcatActivity",
        ):
            source = (UI / f"{activity}.kt").read_text(encoding="utf-8")
            self.assertIn("R.id.action_contextual_help", source, activity)
            self.assertIn("ContextualHelp.show(", source, activity)
            self.assertIn("R.menu.menu_contextual_help", source, activity)

    def test_main_actions_and_destructive_dialogs_link_to_correct_help(self):
        source = (UI / "MainActivity.kt").read_text(encoding="utf-8")
        self.assertIn("ContextualHelp.showIndex(this)", source)
        for action in (
            "del_all_config", "del_duplicate_config", "del_invalid_config"
        ):
            self.assertIn(
                f"ContextualHelp.show(this@MainActivity, R.id.{action})",
                source,
            )
        self.assertEqual(3, source.count(".setNeutralButton(R.string.help_action)"))


if __name__ == "__main__":
    unittest.main()
