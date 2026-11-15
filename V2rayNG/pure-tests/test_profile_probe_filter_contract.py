"""In-scope, non-destructive result filtering for the existing profile view."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1] / "app/src/main"
VM = ROOT / "kotlin/com/v2ray/ang/viewmodel/MainViewModel.kt"

class ProfileProbeFilterContract(unittest.TestCase):
    def test_filter_keeps_existing_group_keyword_and_saved_test_semantics(self):
        code = VM.read_text()
        self.assertIn("subscriptionId.isNotEmpty()", code)
        self.assertIn("config.remarks.contains(keywordFilter)", code)
        self.assertIn("ProfileProbeFilter.matches(delay, profileProbeStatus, profileMaxLatencyMs)", code)
        self.assertIn("MmkvManager.decodeServerAffiliationInfo(guid)?.testDelayMillis", code)
        self.assertIn("parsedLatency !in 1..60_000", code)

    def test_results_refresh_visible_membership_at_start_and_completion(self):
        code = VM.read_text()
        self.assertIn('if (probeFilterActive()) updateCache()', code)
        self.assertIn('if (probeFilterActive()) {', code)
        self.assertIn('updateListAction.value = -1', code)

    def test_spinner_and_localized_options(self):
        layout = ET.parse(ROOT / "res/layout/dialog_config_filter.xml")
        namespace = "{http://schemas.android.com/apk/res/android}"
        ids = {node.attrib.get(namespace+"id") for node in layout.iter()}
        self.assertIn("@+id/sp_test_status", ids)
        self.assertIn("@+id/et_max_latency", ids)
        locale_names = []
        for locale in ("values", "values-fa"):
            tree = ET.parse(ROOT / "res" / locale / "profile_probe_filter.xml")
            names = {node.attrib.get("name") for node in tree.getroot()}
            options = tree.find("string-array[@name='profile_probe_statuses']")
            self.assertEqual(4, len(options.findall("item")))
            locale_names.append(names)
        self.assertEqual(locale_names[0], locale_names[1])

if __name__ == "__main__":
    unittest.main()
