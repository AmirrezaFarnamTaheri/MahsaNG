"""Contracts for the debug-only, two-process Stop envelope QA gate."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "app/src/main/kotlin/com/v2ray/ang/service"
QA_RECEIVER = ROOT / "app/src/debug/kotlin/com/v2ray/ang/qa/VpnSessionFenceQaReceiver.kt"
STOP_QA = ROOT / "pure-tests/test-vpn-stop-command-emulator.sh"
SMOKE = ROOT / "pure-tests/smoke-android-emulator.sh"


class StopCommandGateContract(unittest.TestCase):
    def test_real_stop_envelope_is_pure_and_transaction_bound(self):
        helper = (SERVICE / "VpnStopCommandGate.kt").read_text(encoding="utf-8")
        self.assertIn("VpnStopCommandCodec", helper)
        self.assertIn("fun requestStop(", helper)
        self.assertIn("fun mayStopNative(", helper)
        self.assertIn("fun acknowledgeStopped(", helper)
        self.assertIn("evidence: VpnNativeStopEvidence", helper)
        self.assertNotIn("nativeStopped: Boolean", helper)
        self.assertIn("VpnSessionFence.stop(", helper)
        self.assertIn("VpnSessionFence.release(", helper)
        self.assertIn("state.phase == VpnSessionPhase.STOPPING", helper)
        self.assertNotIn("Thread.sleep", helper)
        self.assertNotIn("MMKV.", helper)

    def test_qa_receivers_only_use_disposable_debug_store(self):
        source = QA_RECEIVER.read_text(encoding="utf-8")
        for marker in ('"CMD_REQUEST"', '"CMD_CHECK"', '"CMD_SIM_ACK"',
                       '"CMD_ROLE_LEFT"', '"BEGIN_NEXT"'):
            self.assertIn(marker, source)
        self.assertIn("VpnSessionMmkvRecordIO.openDebugQa()", source)
        self.assertIn("BuildConfig.DEBUG", source)
        self.assertIn("VpnSessionRecordStore(io)", source)
        self.assertIn("VpnStopCommandCodec.decode(", source)
        self.assertIn("VpnStopCommandGate.requestStop(", source)
        self.assertIn("VpnStopCommandGate.mayStopNative(", source)
        self.assertIn("VpnStopCommandGate.acknowledgeStopped(", source)
        self.assertIn('intent.getBooleanExtra("complete", false)', source)
        for line in source.splitlines():
            if "Log." in line:
                self.assertNotIn("$wire", line)
                self.assertNotIn("$id", line)
                self.assertNotIn("$generation", line)
        for filename in ("V2RayServiceManager.kt", "V2RayVpnService.kt",
                         "V2RayProxyOnlyService.kt", "PsiphonVpnService.kt"):
            live = (SERVICE / filename).read_text(encoding="utf-8")
            self.assertNotIn("VpnStopCommandGate", live)
            self.assertNotIn("VpnStopCommandCodec", live)

    def test_script_runs_real_two_process_qa_without_claiming_native_ack(self):
        process = subprocess.run(["bash", "-n", str(STOP_QA)],
                                 text=True, capture_output=True, timeout=10)
        self.assertEqual(0, process.returncode, process.stderr)
        script = STOP_QA.read_text(encoding="utf-8")
        smoke = SMOKE.read_text(encoding="utf-8")
        self.assertIn("test-vpn-stop-command-emulator.sh", smoke)
        self.assertIn("adb shell pidof", script)
        self.assertIn("adb shell am broadcast", script)
        # The wire is passed through adb shell and cannot contain shell pipes.
        self.assertIn('current_wire="v1.$first.1"', script)
        self.assertIn('wrong_wire="v1.$second.1"', script)
        self.assertNotIn('current_wire="v1|', script)
        self.assertIn("qa_lock_owner", script)
        self.assertIn("qa_lock_contender", script)
        self.assertIn('token="', script)
        self.assertEqual(1, script.count('token="'))
        for status in (
            "OWNER CMD_REQUEST REJECTED", "OWNER CMD_REQUEST ACCEPTED",
            "CONTENDER CMD_CHECK ACCEPTED", "CONTENDER CMD_SIM_ACK REJECTED",
            "OWNER CMD_SIM_ACK ACCEPTED", "CONTENDER CMD_ROLE_LEFT ACCEPTED",
            "OWNER BEGIN_NEXT REJECTED", "CONTENDER CMD_SIM_ACK ACCEPTED",
            "OWNER BEGIN_NEXT ACCEPTED", "OWNER CMD_CHECK REJECTED",
            "CONTENDER CMD_REQUEST REJECTED", "OWNER CMD_SIM_ACK REJECTED",
            "CONTENDER CHECK STARTING PASS"
        ):
            self.assertIn(status, script)
        self.assertIn("--ez complete false", script)
        self.assertIn("--ez complete true", script)
        self.assertNotIn("stopService(", script)
        self.assertNotIn("terminateTun2Socks", script)

    def test_existing_live_global_stop_remains_unchanged(self):
        manager = (SERVICE / "V2RayServiceManager.kt").read_text(encoding="utf-8")
        psiphon = (SERVICE / "PsiphonVpnService.kt").read_text(encoding="utf-8")
        self.assertIn("AppConfig.MSG_STATE_STOP -> {", manager)
        self.assertIn("serviceControl.stopService()", manager)
        self.assertIn("intent.getIntExtra(\"key\", 0) == AppConfig.MSG_STATE_STOP", psiphon)
        self.assertIn("Thread { stopAll() }.start()", psiphon)


if __name__ == "__main__":
    unittest.main()
