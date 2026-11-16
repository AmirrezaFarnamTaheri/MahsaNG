"""SAF-only profile-link backups must never expose plaintext via clipboard or logs."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1] / "app/src/main"
BASE = ROOT / "kotlin/com/v2ray/ang"
ANDROID = "{http://schemas.android.com/apk/res/android}"

class ProtectedProfileFilesContractTest(unittest.TestCase):
    def test_ui_uses_private_activity_and_document_provider_only(self):
        manifest = ET.parse(ROOT / "AndroidManifest.xml")
        activities = [el for el in manifest.iter("activity")
                      if el.attrib.get(ANDROID + "name") == ".ui.ProtectedProfileFilesActivity"]
        self.assertEqual(1, len(activities))
        self.assertEqual("false", activities[0].attrib.get(ANDROID + "exported"))
        screen = (BASE / "ui/ProtectedProfileFilesActivity.kt").read_text()
        self.assertIn("ActivityResultContracts.CreateDocument", screen)
        self.assertIn("ActivityResultContracts.OpenDocument", screen)
        self.assertIn("PasswordProtectedLinkArchive.encrypt(", screen)
        self.assertIn("PasswordProtectedLinkArchive.decrypt(", screen)
        self.assertIn("ProfileLinkBundle.parse(", screen)
        self.assertIn("AngConfigManager.exportPortableProfileLinks(", screen)
        for unsafe in ("Utils.setClipboard(", "Log.d(", "Log.e(", "FileOutputStream(",
                       "Environment.getExternalStorageDirectory(", "startV2Ray("):
            self.assertNotIn(unsafe, screen)

    def test_import_only_whitelisted_file_lines_and_no_automatic_subscriptions(self):
        screen = (BASE / "ui/ProtectedProfileFilesActivity.kt").read_text()
        self.assertIn("AngConfigManager.importBatchConfig(links, \"\", true)", screen)
        self.assertIn("MAX_ARCHIVE_BYTES", screen)
        self.assertIn("input.read(", screen)
        self.assertIn("bytes.fill(0)", screen)

    def test_export_count_matches_actual_distinct_links_saved(self):
        manager = (BASE / "util/AngConfigManager.kt").read_text()
        self.assertIn("val normalized = ProfileLinkBundle.parse(links.joinToString", manager)
        self.assertIn("PortableLinkExport(normalized.joinToString", manager)

    def test_localized_help_and_menu_wiring(self):
        menu = (ROOT / "res/menu/menu_main.xml").read_text()
        main = (BASE / "ui/MainActivity.kt").read_text()
        help_file = (BASE / "ui/ContextualHelp.kt").read_text()
        self.assertIn('id="@+id/protected_profile_files"', menu)
        self.assertIn("R.id.protected_profile_files ->", main)
        self.assertIn("R.id.protected_profile_files to HelpTopic(", help_file)
        self.assertIn("R.id.protected_profile_files,", help_file)
        for loc in ("values", "values-fa"):
            values = ET.parse(ROOT / "res" / loc / "protected_profile_files.xml")
            self.assertTrue(any(el.attrib.get("name") == "protected_profile_title"
                                for el in values.findall("string")))
            help_xml = ET.parse(ROOT / "res" / loc / "contextual_help.xml")
            blocks = [el for el in help_xml.findall("string-array")
                      if el.attrib.get("name") == "help_protected_profile_files"]
            self.assertEqual(1, len(blocks))
            self.assertEqual(5, len(blocks[0]))

if __name__ == "__main__":
    unittest.main()
