"""Smart selection may use only fresh native real-ping evidence, never TCP reachability."""
from pathlib import Path
import unittest

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE / "app/src/main"
KOTLIN = ROOT / "kotlin/com/v2ray/ang"


class SmartRecommendationWiringTest(unittest.TestCase):
    def test_native_result_carries_the_exact_tested_profile_revision(self):
        dto = (KOTLIN / "dto/ConfigTestMessage.kt").read_text()
        service = (KOTLIN / "service/V2RayTestService.kt").read_text()
        model = (KOTLIN / "viewmodel/MainViewModel.kt").read_text()
        self.assertIn("profileRevision", dto)
        self.assertIn("request.profileRevision", service)
        self.assertIn("MmkvManager.encodeServerRealPingEvidence(", model)
        self.assertIn("result.profileRevision", model)

    def test_tcp_probe_updates_only_legacy_delay_not_smart_evidence(self):
        model = (KOTLIN / "viewmodel/MainViewModel.kt").read_text()
        tcp = model.split("fun testAllTcping()", 1)[1].split("fun testAllRealPing()", 1)[0]
        self.assertIn("MmkvManager.encodeServerTestDelayMillis(guid, delay)", tcp)
        self.assertNotIn("encodeServerRealPingEvidence", tcp)

    def test_user_chooses_from_visible_profiles_with_explicit_confirmation(self):
        activity = (KOTLIN / "ui/MainActivity.kt").read_text()
        menu = (ROOT / "res/menu/menu_main.xml").read_text()
        self.assertIn('@+id/recommend_tested_server', menu)
        section = activity.split("R.id.recommend_tested_server -> {", 1)[1].split(
            "R.id.filter_config ->", 1
        )[0]
        self.assertIn("mainViewModel.serversCache.map { it.guid }", section)
        self.assertIn("mainViewModel.isRunning.value == true", section)
        self.assertIn("AlertDialog.Builder(", section)
        self.assertIn("MmkvManager.confirmSmartRecommendation(", section)
        self.assertNotIn("V2RayServiceManager.startV2Ray", section)
        self.assertNotIn("Utils.stopVService", section)

    def test_clear_all_results_removes_smart_history_but_new_test_run_preserves_it(self):
        manager = (KOTLIN / "util/MmkvManager.kt").read_text()
        clear_all = manager.split("fun clearAllTestDelayResults()", 1)[1].split(
            "fun clearTestDelayResults(", 1
        )[0]
        self.assertIn("realPingEvidence = null", clear_all)
        clear_for_new_run = manager.split("fun clearTestDelayResults(", 1)[1].split(
            "fun importUrlAsSubscription(", 1
        )[0]
        self.assertNotIn("realPingEvidence = null", clear_for_new_run)


if __name__ == "__main__":
    unittest.main()
