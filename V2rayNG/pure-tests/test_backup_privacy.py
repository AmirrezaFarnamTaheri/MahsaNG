"""VPN profiles and credentials must not be included in platform backups."""
from pathlib import Path
from xml.etree import ElementTree as ET
import unittest

ROOT = Path(__file__).resolve().parents[1] / "app/src/main"
ANDROID = "{http://schemas.android.com/apk/res/android}"
TOOLS = "{http://schemas.android.com/tools}"


class BackupExclusionsTest(unittest.TestCase):
    def test_app_disables_automatic_backup_and_has_version_specific_rules(self):
        app = ET.parse(ROOT / "AndroidManifest.xml").getroot().find("application")
        self.assertEqual("false", app.get(ANDROID + "allowBackup"))
        self.assertIn("android:allowBackup", app.get(TOOLS + "replace", "").split(","))
        self.assertEqual("@xml/no_backup_legacy", app.get(ANDROID + "fullBackupContent"))
        self.assertEqual("@xml/no_backup_extraction", app.get(ANDROID + "dataExtractionRules"))

    def test_pre_android12_rules_exclude_all_credential_and_device_storage(self):
        root = ET.parse(ROOT / "res/xml/no_backup_legacy.xml").getroot()
        self.assertEqual("full-backup-content", root.tag)
        exclusions = {(e.get("domain"), e.get("path")) for e in root.findall("exclude")}
        self.assertIn(("root", "."), exclusions)
        self.assertIn(("device_root", "."), exclusions)

    def test_android12_plus_rules_exclude_cloud_and_device_transfer(self):
        root = ET.parse(ROOT / "res/xml/no_backup_extraction.xml").getroot()
        self.assertEqual("data-extraction-rules", root.tag)
        for mode in ("cloud-backup", "device-transfer"):
            with self.subTest(mode=mode):
                section = root.find(mode)
                self.assertIsNotNone(section)
                exclusions = {(e.get("domain"), e.get("path")) for e in section.findall("exclude")}
                self.assertIn(("root", "."), exclusions)
                self.assertIn(("device_root", "."), exclusions)


if __name__ == "__main__":
    unittest.main()
