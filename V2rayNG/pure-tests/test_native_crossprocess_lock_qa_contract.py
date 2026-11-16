"""Debug-only Android IPC lock contention must be exercised by real emulator smoke."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app/src"
ANDROID = "{http://schemas.android.com/apk/res/android}"

class NativeCrossProcessLockContract(unittest.TestCase):
    def test_debug_only_separate_process_receivers(self):
        debug = ET.parse(APP / "debug/AndroidManifest.xml")
        receivers = [x for x in debug.iter("receiver")
                     if "IndexLease" in x.attrib.get(ANDROID + "name", "")]
        self.assertEqual(2, len(receivers))
        processes = {x.attrib.get(ANDROID + "process") for x in receivers}
        self.assertEqual({":qa_lock_owner", ":qa_lock_contender"}, processes)
        self.assertTrue(all(x.attrib.get(ANDROID + "exported") == "true" for x in receivers))
        main = (APP / "main/AndroidManifest.xml").read_text()
        self.assertNotIn("IndexLeaseOwnerReceiver", main)
        self.assertNotIn("IndexLeaseContenderReceiver", main)

    def test_qa_uses_native_mmkv_lock_not_mock_and_releases_in_finally(self):
        code = (APP / "debug/kotlin/com/v2ray/ang/qa/IndexLeaseProbeReceiver.kt").read_text()
        self.assertIn("MMKV.MULTI_PROCESS_MODE", code)
        self.assertIn("main.tryLock()", code)
        self.assertIn("main.unlock()", code)
        self.assertIn("finally", code)
        self.assertIn("goAsync()", code)
        self.assertIn("BuildConfig.DEBUG", code)
        self.assertNotIn("KEY_ANG_CONFIGS", code)
        self.assertNotIn("decodeServerConfig", code)
        self.assertNotIn("Log.d(", code)

    def test_emulator_runner_requires_denial_then_success_after_release(self):
        smoke = (ROOT / "pure-tests/smoke-android-emulator.sh").read_text()
        self.assertIn("test-mmkv-crossprocess-emulator.sh", smoke)
        qa = (ROOT / "pure-tests/test-mmkv-crossprocess-emulator.sh").read_text()
        self.assertIn("OWNER LOCKED", qa)
        self.assertIn("CONTENDER DENIED", qa)
        self.assertIn("OWNER RELEASED", qa)
        self.assertIn("CONTENDER GRANTED", qa)
        self.assertIn("wait_for", qa)
        self.assertIn("adb shell am broadcast", qa)
        self.assertNotIn("mmkvWithID", qa)

if __name__ == "__main__":
    unittest.main()
