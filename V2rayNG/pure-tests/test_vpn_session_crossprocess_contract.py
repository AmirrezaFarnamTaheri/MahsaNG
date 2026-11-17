"""Static and shell-syntax contract for real debug Android session fencing QA."""
from pathlib import Path
import subprocess
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app/src"
SERVICE = APP / "main/kotlin/com/v2ray/ang/service"
ANDROID = "{http://schemas.android.com/apk/res/android}"
QA = ROOT / "pure-tests/test-vpn-session-crossprocess-emulator.sh"


class VpnSessionCrossProcessContractTest(unittest.TestCase):
    def test_debug_only_dump_restricted_two_process_receivers(self):
        manifest = ET.parse(APP / "debug/AndroidManifest.xml")
        entries = [node for node in manifest.iter("receiver")
                   if "VpnSessionQa" in node.attrib.get(ANDROID + "name", "")]
        self.assertEqual(2, len(entries))
        self.assertEqual({":qa_lock_owner", ":qa_lock_contender"},
                         {node.attrib.get(ANDROID + "process") for node in entries})
        for node in entries:
            self.assertEqual("true", node.attrib.get(ANDROID + "exported"))
            self.assertEqual("android.permission.DUMP",
                             node.attrib.get(ANDROID + "permission"))
        main = (APP / "main/AndroidManifest.xml").read_text(encoding="utf-8")
        self.assertNotIn("VpnSessionQaOwnerReceiver", main)
        self.assertNotIn("VpnSessionQaContenderReceiver", main)

    def test_native_adapter_does_not_bootstrap_or_share_live_storage(self):
        adapter = (SERVICE / "VpnSessionMmkvRecordIO.kt").read_text(encoding="utf-8")
        self.assertIn("MMKV.MULTI_PROCESS_MODE", adapter)
        self.assertIn("mmkv.tryLock()", adapter)
        self.assertIn("mmkv.unlock()", adapter)
        self.assertIn("mmkv.decodeString(KEY)", adapter)
        self.assertIn("mmkv.encode(KEY, value)", adapter)
        self.assertIn("VPN_SESSION_FENCE_DEBUG_QA_V1", adapter)
        self.assertNotIn("ID_MAIN", adapter)
        self.assertNotIn("KEY_ANG_CONFIGS", adapter)
        self.assertNotIn("VpnSessionFence.empty()", adapter)
        for live in ("V2RayVpnService.kt", "PsiphonVpnService.kt",
                     "V2RayServiceManager.kt", "V2RayProxyOnlyService.kt"):
            self.assertNotIn("VpnSessionRecordStore(",
                             (SERVICE / live).read_text(encoding="utf-8"))

    def test_debug_receiver_uses_real_transaction_and_no_private_logs(self):
        receiver = (APP / "debug/kotlin/com/v2ray/ang/qa/VpnSessionFenceQaReceiver.kt"
                    ).read_text(encoding="utf-8")
        self.assertIn("BuildConfig.DEBUG", receiver)
        self.assertIn("goAsync()", receiver)
        self.assertIn("VpnSessionRecordStore(io)", receiver)
        self.assertIn("VpnSessionFence.begin(", receiver)
        self.assertIn("VpnSessionFence.release(", receiver)
        self.assertIn("VpnSessionFence.stop(", receiver)
        self.assertIn("io.tryLock()", receiver)
        self.assertIn("io.unlock()", receiver)
        for line in receiver.splitlines():
            if "Log." in line:
                self.assertNotIn("$id", line)
                self.assertNotIn("$generation", line)
                self.assertNotIn("decodeString(", line)

    def test_emulator_script_is_syntax_valid_and_invoked_with_real_adb(self):
        result = subprocess.run(["bash", "-n", str(QA)], capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        script = QA.read_text(encoding="utf-8")
        smoke = (ROOT / "pure-tests/smoke-android-emulator.sh").read_text(
            encoding="utf-8")
        self.assertIn("test-vpn-session-crossprocess-emulator.sh", smoke)
        for event in ("OWNER SEED ACCEPTED", "CONTENDER ATTACH ACCEPTED",
                      "CONTENDER CHECK ACTIVE PASS", "OWNER CHECK STOPPING PASS",
                      "CONTENDER BEGIN REJECTED", "OWNER STOP REJECTED",
                      "CONTENDER CHECK STARTING PASS", "OWNER HOLD LOCKED",
                      "CONTENDER PROBE UNAVAILABLE", "OWNER CORRUPT ACCEPTED"):
            self.assertIn(event, script)
        self.assertIn("adb shell am broadcast", script)
        self.assertIn("adb shell pidof", script)
        self.assertIn("wait_for", script)
        self.assertNotIn("mmkvWithID(", script)
        self.assertNotIn("KEY_ANG_CONFIGS", script)


if __name__ == "__main__":
    unittest.main()
