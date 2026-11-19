"""An OS process death cannot impersonate a generation-scoped native Stop ACK.

This is deliberately pure and UNWIRED; neither a PID nor an elapsed timeout
is evidence that native work, the TUN or duplicated descriptors stopped.
"""
from pathlib import Path
import unittest

SERVICES = Path(__file__).resolve().parents[1] / "app/src/main/kotlin/com/v2ray/ang/service"
QUARANTINE = SERVICES / "VpnProcessDeathQuarantine.kt"
STORE = SERVICES / "VpnSessionRecordStore.kt"
PSIPHON = SERVICES / "PsiphonVpnService.kt"
XRAY = SERVICES / "V2RayServiceManager.kt"


class VpnProcessDeathQuarantineContract(unittest.TestCase):
    def test_quarantine_requires_exact_persisted_role_membership(self):
        code = QUARANTINE.read_text(encoding="utf-8")
        self.assertIn("VpnSessionFence.canAct(state, report.sessionId, report.generation, report.role)", code)
        self.assertIn("VpnSessionPhase.STOPPING -> state", code)
        self.assertIn("VpnSessionFence.stop(state, report.sessionId, report.generation)", code)

    def test_death_never_releases_a_role_or_fabricates_native_receipt(self):
        code = QUARANTINE.read_text(encoding="utf-8")
        self.assertNotIn("VpnSessionFence.release(", code)
        self.assertNotIn("VpnNativeStopEvidence.Xray(", code)
        self.assertNotIn("VpnNativeStopEvidence.Psiphon(", code)
        self.assertNotIn("System.currentTimeMillis(", code)
        self.assertNotIn("Process.isAlive(", code)

    def test_no_live_vpn_service_invokes_untrusted_quarantine_policy(self):
        for path in (PSIPHON, XRAY):
            with self.subTest(path=path.name):
                code = path.read_text(encoding="utf-8")
                self.assertNotIn("VpnProcessDeathQuarantine.markLost(", code)
                self.assertNotIn("VpnProcessDeathReport(", code)
        store = STORE.read_text(encoding="utf-8")
        self.assertIn("io.tryLock()", store)
        self.assertNotIn("fun recoverAfterTimeout(", store)

if __name__ == "__main__":
    unittest.main()
