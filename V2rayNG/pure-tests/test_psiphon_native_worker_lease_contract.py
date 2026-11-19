"""The process-wide Psiphon JNI worker gate must reject stale releases.

This is a local Java/Kotlin admission barrier, NOT native completion, a
trustworthy cross-process token or proof that duplicated TUN FDs closed.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "app/src/main/kotlin/com/v2ray/ang/service/PsiphonVpnService.kt"
GATE = ROOT / "app/src/main/kotlin/com/v2ray/ang/service/PsiphonNativeWorkerGate.kt"
PURE_GRADLE = ROOT / "pure-tests/build.gradle.kts"


class PsiphonNativeWorkerLeaseContract(unittest.TestCase):
    def test_gate_releases_only_same_object_identity(self):
        gate = GATE.read_text(encoding="utf-8")
        self.assertIn("private var activeLease: Lease?", gate)
        self.assertIn("fun acquire(prepareNative: () -> Unit): Lease?", gate)
        self.assertIn("fun release(lease: Lease): Boolean", gate)
        self.assertIn("if (activeLease !== lease) return false", gate)
        self.assertIn("activeLease = null", gate)
        self.assertNotIn("private var workerInFlight = false", gate)
        self.assertNotIn("fun release()", gate)

    def test_service_uses_acquired_lease_in_worker_and_failed_start_cleanup(self):
        code = SERVICE.read_text(encoding="utf-8")
        launch = code.split("private fun startTun2socks(socksPort: Int) {", 1)[1].split(
            "// =========================================================================", 1
        )[0]
        self.assertIn("val acquiredLease = PsiphonNativeWorkerGate.acquire", launch)
        self.assertIn("Tun2SocksJniLoader.prepareTun2Socks()", launch)
        self.assertIn("nativeLease = acquiredLease", launch)
        self.assertIn("PsiphonNativeWorkerGate.release(acquiredLease)", launch)
        self.assertIn("nativeLease?.let { PsiphonNativeWorkerGate.release(it) }", launch)
        self.assertNotIn("PsiphonNativeWorkerGate.release()", launch)
        self.assertLess(launch.index("nativeLease = acquiredLease"), launch.index("worker.start()"))

    def test_real_pure_junit_suite_includes_native_gate_and_tests(self):
        build = PURE_GRADLE.read_text(encoding="utf-8")
        self.assertIn('"PsiphonNativeWorkerGate",', build)
        junit = ROOT / "app/src/test/kotlin/com/v2ray/ang/service/PsiphonNativeWorkerGateTest.kt"
        self.assertIn("duplicateReleaseMustNotClearSuccessorNativeWorker", junit.read_text(encoding="utf-8"))
        self.assertIn("unrelatedThreadCannotReleaseAnotherNativeWorker", junit.read_text(encoding="utf-8"))

    def test_no_generation_scoped_native_receipt_is_fabricated(self):
        code = SERVICE.read_text(encoding="utf-8")
        self.assertNotIn("VpnNativeStopEvidence.Psiphon(", code)
        self.assertIn("psiphonNativeStopAcknowledged = false", code)


if __name__ == "__main__":
    unittest.main()
