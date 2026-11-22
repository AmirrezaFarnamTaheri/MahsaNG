"""Static contracts for debug-only, generation-fenced Start QA on Android."""
from pathlib import Path
import subprocess
import unittest
from shell_test_utils import find_bash

ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "app/src/main/kotlin/com/v2ray/ang/service"
QA = ROOT / "app/src/debug/kotlin/com/v2ray/ang/qa/VpnSessionFenceQaReceiver.kt"
SCRIPT = ROOT / "pure-tests/test-vpn-start-command-emulator.sh"
SMOKE = ROOT / "pure-tests/smoke-android-emulator.sh"


class VpnStartCommandAndroidContract(unittest.TestCase):
    def test_receiver_uses_only_locked_debug_qa_record(self):
        source = QA.read_text(encoding="utf-8")
        self.assertIn('"START_RESERVE"', source)
        self.assertIn('"START_CHECK"', source)
        self.assertIn("VpnStartCommandCodec.decode(", source)
        self.assertIn("VpnStartCommandGate.reserve(", source)
        self.assertIn("VpnStartCommandGate.stillAttached(", source)
        self.assertIn("VpnSessionMmkvRecordIO.openDebugQa()", source)
        self.assertIn("VpnSessionRecordStore(io)", source)
        self.assertIn("BuildConfig.DEBUG", source)
        for line in source.splitlines():
            if "Log." in line:
                self.assertNotIn("$wire", line)
                self.assertNotIn("$id", line)
                self.assertNotIn("$generation", line)
        for filename in (
            "V2RayServiceManager.kt", "V2RayVpnService.kt",
            "V2RayProxyOnlyService.kt", "PsiphonVpnService.kt",
        ):
            production = (SERVICE / filename).read_text(encoding="utf-8")
            self.assertNotIn("VpnStartCommandGate", production)
            self.assertNotIn("VpnStartCommandCodec", production)

    def test_real_emulator_qa_gate_is_wired_and_syntax_valid(self):
        status = subprocess.run(
            [find_bash(), "-n", str(SCRIPT)], capture_output=True, text=True, timeout=10
        )
        self.assertEqual(0, status.returncode, status.stderr)
        script = SCRIPT.read_text(encoding="utf-8")
        smoke = SMOKE.read_text(encoding="utf-8")
        self.assertIn("test-vpn-start-command-emulator.sh", smoke)
        self.assertIn("adb shell pidof", script)
        self.assertIn("adb shell am broadcast", script)
        self.assertIn("qa_lock_owner", script)
        self.assertIn("qa_lock_contender", script)
        self.assertIn("START_RESERVE REJECTED", script)
        self.assertIn("START_RESERVE ACCEPTED", script)
        self.assertIn("START_CHECK REJECTED", script)
        self.assertIn("START_CHECK ACCEPTED", script)
        self.assertIn("CMD_REQUEST ACCEPTED", script)
        self.assertIn("BEGIN_NEXT REJECTED", script)
        self.assertIn("BEGIN_NEXT ACCEPTED", script)
        self.assertIn("CHECK ACTIVE PASS", script)
        self.assertIn('"v1.$first.2.XRAY_VPN.XRAY"', script)
        self.assertIn("step=$((step+1))", script)
        self.assertIn('local token="${base}N${step}"', script)
        self.assertNotIn("am startservice", script)
        self.assertNotIn("stopService(", script)

    def test_fake_smoke_requires_new_qa_step(self):
        fake = (ROOT / "pure-tests/test_emulator_smoke_behavior.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("fake-start-command-qa-invoked", fake)
        self.assertIn("test-vpn-start-command-emulator.sh", fake)


if __name__ == "__main__":
    unittest.main()
