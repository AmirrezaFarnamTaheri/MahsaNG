"""Live Xray legacy Stop Success must wait for *observed* tun2socks exit.

This is local subprocess evidence, not an authoritative session-native receipt.
"""
from pathlib import Path
import unittest

BASE = Path(__file__).resolve().parents[1] / "app/src/main/kotlin/com/v2ray/ang/service"
VPN = BASE / "V2RayVpnService.kt"
MANAGER = BASE / "V2RayServiceManager.kt"

class XrayTun2SocksExitContract(unittest.TestCase):
    def test_every_spawn_is_accounted_even_when_stop_wins_during_start(self):
        code = VPN.read_text(encoding="utf-8")
        start = code.split("private fun runTun2socks(", 1)[1].split("private fun sendFd(", 1)[0]
        self.assertIn("tunExitTracker.beginLaunch()", start)
        self.assertIn("tunExitTracker.registered(child)", start)
        self.assertIn("tunExitTracker.launchFailed()", start)
        self.assertIn("tunExitTracker.observedExit(child)", start)
        self.assertIn("child.waitFor()", start)
        self.assertLess(start.index("tunExitTracker.registered(child)"), start.index("tunProcesses.adopt(generation, child)"))
        self.assertLess(start.index("child.waitFor()"), start.index("tunExitTracker.observedExit(child)"))

    def test_owned_stop_requests_destruction_without_main_thread_join(self):
        code = VPN.read_text(encoding="utf-8")
        destroy = code.split("override fun onDestroy() {", 1)[1].split("private fun setup()", 1)[0]
        stop = code.split("private fun stopV2Ray(", 1)[1].split("override fun getService()", 1)[0]
        self.assertIn("stopOwnedTun2socks()", destroy)
        self.assertIn("stopOwnedTun2socks()", stop)
        self.assertIn("tunProcesses.stop()", code)
        self.assertIn("tunExitTracker.requestStop()", code)
        self.assertIn("child.destroy()", code)
        self.assertIn("internal fun stopAndAwaitTun2socksExit()", code)
        self.assertIn("tunExitTracker.awaitStopped(", code)
        self.assertNotIn("Process.waitFor(", destroy)
        self.assertNotIn("Thread.sleep(", destroy)

    def test_local_stop_success_requires_tun2socks_exit_after_core_and_fragmentor_stop(self):
        code = MANAGER.read_text(encoding="utf-8")
        stop = code.split("fun stopV2rayPoint() {", 1)[1].split("private class ReceiveMessageHandler", 1)[0]
        self.assertIn("is V2RayVpnService -> service.stopAndAwaitTun2socksExit()", stop)
        self.assertIn("val stopped = coreStopped && fragmentorStopped && tunStopped", stop)
        self.assertLess(stop.index("val stopped = coreStopped && fragmentorStopped && tunStopped"),
                        stop.index("AppConfig.MSG_STATE_STOP_SUCCESS"))
        self.assertIn("coreStopGate.completeStop(stopToken, stopped)", stop)
        self.assertNotIn("VpnNativeStopEvidence", stop)

    def test_java_api_compatibility_uses_waiter_not_api26_process_methods(self):
        code = VPN.read_text(encoding="utf-8")
        self.assertNotIn("destroyForcibly(", code)
        self.assertNotIn(".isAlive", code)
        self.assertNotIn("waitFor(3", code)


if __name__ == "__main__":
    unittest.main()
