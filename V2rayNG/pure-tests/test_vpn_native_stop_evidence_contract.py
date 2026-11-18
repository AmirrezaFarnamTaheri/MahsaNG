"""Only generation-matched, role-specific observations can release a Stop role.

The debug QA inputs are simulations, not native completion acknowledgements.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SERVICES = ROOT / "app/src/main/kotlin/com/v2ray/ang/service"
QA = ROOT / "app/src/debug/kotlin/com/v2ray/ang/qa/VpnSessionFenceQaReceiver.kt"


class NativeStopEvidenceContract(unittest.TestCase):
    def test_gate_has_no_raw_native_stopped_boolean_bypass(self):
        code = (SERVICES / "VpnStopCommandGate.kt").read_text(encoding="utf-8")
        self.assertIn("evidence: VpnNativeStopEvidence", code)
        self.assertNotIn("nativeStopped: Boolean", code)
        self.assertIn("evidence.sessionId != command.sessionId", code)
        self.assertIn("evidence.generation != command.generation", code)
        self.assertIn("evidence.isComplete()", code)
        self.assertIn("mayStopNative(state, command, evidence.role)", code)

    def test_role_evidence_requires_separate_native_observations(self):
        code = (SERVICES / "VpnNativeStopEvidence.kt").read_text(encoding="utf-8")
        for marker in (
            "stopLoopReturned", "coreNotRunning", "tun2socksProcessExited",
            "fragmentorListenersExited", "tunDescriptorClosed",
            "routingWorkerExited", "psiphonNativeShutdownAcknowledged",
        ):
            self.assertIn(marker, code)
        self.assertIn("VpnSessionRole.XRAY", code)
        self.assertIn("VpnSessionRole.PSIPHON", code)

    def test_qa_boolean_stays_debug_only_and_never_becomes_live_evidence(self):
        code = QA.read_text(encoding="utf-8")
        self.assertIn('"CMD_SIM_ACK"', code)
        self.assertIn('intent.getBooleanExtra("complete", false)', code)
        self.assertIn("VpnNativeStopEvidence.Xray(", code)
        self.assertIn("VpnNativeStopEvidence.Psiphon(", code)
        self.assertIn("VpnStopCommandGate.acknowledgeStopped(", code)
        for service in (
            "V2RayServiceManager.kt", "V2RayVpnService.kt",
            "V2RayProxyOnlyService.kt", "PsiphonVpnService.kt",
        ):
            live = (SERVICES / service).read_text(encoding="utf-8")
            self.assertNotIn("VpnNativeStopEvidence", live)
            self.assertNotIn("VpnStopCommandGate.acknowledgeStopped(", live)


if __name__ == "__main__":
    unittest.main()
