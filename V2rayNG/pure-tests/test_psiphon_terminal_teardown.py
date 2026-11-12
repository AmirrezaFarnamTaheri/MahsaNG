"""Racing stop/start/callbacks must never create a late VPN routing worker."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1] / "app/src/main/kotlin/com/v2ray/ang/service"
SERVICE = (ROOT / "PsiphonVpnService.kt").read_text(encoding="utf-8")
GATE = (ROOT / "PsiphonStartGate.kt").read_text(encoding="utf-8")


class TerminalPsiphonStartContractTest(unittest.TestCase):
    def test_native_start_guard_is_terminal_after_stop(self):
        self.assertIn("if (active || terminal) return null", GATE)
        self.assertIn("terminal = true", GATE)
        self.assertIn("synchronized(startGate)", SERVICE)

    def test_teardown_marks_terminal_under_the_worker_registration_lock(self):
        teardown = SERVICE.split("private fun stopAll(", 1)[1].split(
            "override fun loadLibrary(", 1
        )[0]
        self.assertRegex(teardown, r"(?s)synchronized\(startGate\)\s*\{.*?teardownStarted\.compareAndSet\(false, true\).*?startGate\.stop\(\)")
        worker = SERVICE.split("private fun startTun2socks(socksPort: Int)", 1)[1].split(
            "private fun startForegroundNotification()", 1
        )[0]
        self.assertIn("synchronized(startGate)", worker)
        self.assertIn("iface.dup().detachFd()", worker)
        self.assertIn("tun2socksThread = worker", worker)
        self.assertIn("ParcelFileDescriptor.adoptFd(tunFd).close()", worker)

    def test_native_stop_handshake_is_armed_before_worker_start(self):
        worker = SERVICE.split("private fun startTun2socks(socksPort: Int)", 1)[1].split(
            "private fun startForegroundNotification()", 1
        )[0]
        self.assertIn("PsiphonNativeWorkerGate.acquire", worker)
        self.assertIn("Tun2SocksJniLoader.prepareTun2Socks()", worker)
        self.assertIn("PsiphonNativeWorkerGate.release()", worker)
        self.assertLess(worker.index("prepareTun2Socks()"), worker.index("worker.start()"))

    def test_native_worker_cannot_claim_a_verified_connection_on_launch(self):
        routing = SERVICE.split("private fun startTun2socksRouting(port: Int)", 1)[1].split(
            "private fun startTun2socks(", 1
        )[0]
        self.assertNotIn("MSG_STATE_START_SUCCESS", routing)
        self.assertNotIn("isPsiphonRunning.set(true)", routing)
        self.assertIn("connectivity unverified", routing)
        worker = SERVICE.split("private fun startTun2socks(socksPort: Int)", 1)[1].split(
            "private fun startForegroundNotification()", 1
        )[0]
        self.assertIn("Thread { stopAll() }.start()", worker)


if __name__ == "__main__":
    unittest.main()
