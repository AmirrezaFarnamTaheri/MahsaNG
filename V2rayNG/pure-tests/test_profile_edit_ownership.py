"""A saved edit must synchronously retire in-flight test ownership."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / "app/src/main/kotlin/com/v2ray/ang"

class EditedProfileTestOwnershipTest(unittest.TestCase):
    def test_save_invalidates_stale_results_after_persisting_new_endpoint(self):
        activity = (ROOT / "ui/ServerActivity.kt").read_text(encoding="utf-8")
        saved = activity.split("MmkvManager.encodeServerConfig(editGuid, config)", 1)[1]
        self.assertIn("TestRunTracker.forgetProfile(editGuid)", saved)
        self.assertLess(saved.index("TestRunTracker.forgetProfile(editGuid)"), saved.index("toast(R.string.toast_success)"))
        self.assertIn("MmkvManager.clearTestDelayResults(listOf(editGuid))", saved)
        self.assertLess(
            saved.index("TestRunTracker.forgetProfile(editGuid)"),
            saved.index("MmkvManager.clearTestDelayResults(listOf(editGuid))"),
        )
        self.assertLess(
            saved.index("MmkvManager.clearTestDelayResults(listOf(editGuid))"),
            saved.index("toast(R.string.toast_success)"),
        )

    def test_shared_ownership_gate_does_not_reuse_old_profile_results(self):
        source = (ROOT / "util/TestRunTracker.kt").read_text(encoding="utf-8")
        self.assertIn("run.copy(guids = run.guids - guid)", source)
        self.assertIn("fun forgetProfile(guid: String)", source)

if __name__ == "__main__":
    unittest.main()
