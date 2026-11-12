"""Source contracts for Psiphon service cancellation and resource cleanup."""
from pathlib import Path
import re
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "app/src/main/kotlin/com/v2ray/ang/service/PsiphonVpnService.kt"


class PsiphonLifecycleContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = SOURCE.read_text(encoding="utf-8")

    def test_android_destroy_releases_native_resources(self):
        self.assertRegex(self.text, r"override fun onDestroy\(\)\s*\{\s*stopAll\(isForced = false\)")
        stop = self.text.split("private fun stopAll(", 1)[1].split("override fun loadLibrary(", 1)[0]
        self.assertIn("startGate.stop()", stop)
        self.assertIn("teardownStarted.compareAndSet(false, true)", stop)
        self.assertIn("mInterface?.close()", stop)
        self.assertIn("mInterface = null", stop)

    def test_port_wait_cancels_when_service_stops(self):
        self.assertRegex(self.text, r"while \(System.currentTimeMillis\(\) < deadline && startGate.isCurrent\(attempt\)\)")
        self.assertIn("startPsiphonTunnelAsync(attempt)", self.text)

    def test_tun_setup_does_not_claim_psiphon_is_connected(self):
        setup = self.text.split("private fun establishVpnInterface()", 1)[1].split("private fun startTun2socksRouting()", 1)[0]
        routing = self.text.split("private fun startTun2socksRouting()", 1)[1].split("private fun startTun2socks(", 1)[0]
        self.assertNotIn("isPsiphonRunning.set(true)", setup)
        self.assertIn("isPsiphonRunning.set(true)", routing)
        self.assertIn("teardownStarted.get()", routing)


if __name__ == "__main__":
    unittest.main()
