"""Guard against silently losing one merged feature during conflict resolution."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "app/src/main"
MAIN = SRC / "kotlin/com/v2ray/ang/ui/MainActivity.kt"
ANDROID = "{http://schemas.android.com/apk/res/android}"

class CombinedMergeContract(unittest.TestCase):
    def test_main_activity_retains_all_three_prs(self):
        source = MAIN.read_text(encoding="utf-8")
        for marker in (
            "R.id.dns_diagnostics ->",
            "R.id.https_evidence ->",
            "R.id.advanced_tcp_retry ->",
            "R.id.action_contextual_help ->",
            "mainViewModel.updateListBatchAction.observe(this)",
            "Subscription URLs may contain access tokens",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, source)
        section = source.split("fun importConfigViaSub()", 1)[1].split("show file chooser", 1)[0]
        self.assertNotIn("Log.d(ANG_PACKAGE, url)", section)
        self.assertNotIn("printStackTrace()", section)

    def test_manifest_registers_all_diagnostic_screens_as_internal(self):
        root = ET.parse(SRC / "AndroidManifest.xml")
        activities = {
            el.get(ANDROID + "name"): el.get(ANDROID + "exported")
            for el in root.iter("activity")
        }
        for name in (".ui.DnsDiagnosticsActivity", ".ui.HttpsEvidenceActivity",
                     ".ui.AdvancedTcpRetryActivity"):
            self.assertEqual("false", activities[name])

    def test_menu_and_pure_kotlin_helpers_are_union_not_either_side(self):
        menu = ET.parse(SRC / "res/menu/menu_main.xml")
        ids = {el.get(ANDROID + "id") for el in menu.iter("item")}
        for id in ("dns_diagnostics", "https_evidence", "advanced_tcp_retry"):
            self.assertIn("@+id/" + id, ids)
        gradle = (ROOT / "pure-tests/build.gradle.kts").read_text(encoding="utf-8")
        for helper in ("DnsWire", "TlsHandshakeProbe", "TcpRowBatch",
                       "AdvancedRetryScheduler", "AdvancedTcpRetrySession"):
            self.assertIn('"' + helper + '"', gradle)

if __name__ == "__main__":
    unittest.main()
