"""Xray failed startup must not orphan fragmentor handlers or bypass Stop gate.

This verifies the live exception path delegates to already-existing bounded
local cleanup. No test here proves native FD aliases or a cross-process receipt.
"""
from pathlib import Path
import unittest

MANAGER = (
    Path(__file__).resolve().parents[1] /
    "app/src/main/kotlin/com/v2ray/ang/service/V2RayServiceManager.kt"
)


class XrayStartFailureTeardownContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        code = MANAGER.read_text(encoding="utf-8")
        cls.start = code.split("fun startV2rayPoint() {", 1)[1].split(
            "fun stopV2rayPointIfOwner(", 1
        )[0]
        cls.stop = code.split("fun stopV2rayPoint() {", 1)[1].split(
            "private class ReceiveMessageHandler", 1
        )[0]

    def test_failed_native_start_uses_observed_shutdown_gate(self):
        start = self.start
        self.assertIn("catch (failure: Exception)", start)
        self.assertIn("cleanupFailedStartup(service, fragmentor, receiverRegistered, failure)", start)
        self.assertIn("stopV2rayPoint()", start)
        self.assertLess(start.index("TLS_serv = fragmentor"), start.index("stopV2rayPoint()"))
        self.assertNotIn("if (TLS_serv === fragmentor) TLS_serv = null", start)

    def test_linkage_errors_follow_the_same_cleanup_path(self):
        start = self.start
        self.assertIn("catch (failure: LinkageError)", start)
        self.assertGreaterEqual(
            start.count("cleanupFailedStartup(service, fragmentor, receiverRegistered, failure)"),
            2,
        )

    def test_failure_cleanup_requests_immediate_stop_then_keeps_listener_for_observation(self):
        helper = self.start.split("private fun cleanupFailedStartup(", 1)[1]
        helper = helper.split("fun stopV2rayPointIfOwner(", 1)[0]
        self.assertIn("fragmentor?.stop_HTTPS_service()", helper)
        self.assertIn("fragmentor?.stop_TLS_service()", helper)
        self.assertIn("if (fragmentor != null) TLS_serv = fragmentor", helper)
        self.assertIn("stopV2rayPoint()", helper)
        self.assertIn("AppConfig.MSG_STATE_START_FAILURE", helper)
        self.assertLess(helper.index("if (fragmentor != null) TLS_serv = fragmentor"),
                        helper.index("stopV2rayPoint()"))
        self.assertLess(helper.index("stopV2rayPoint()"),
                        helper.index("AppConfig.MSG_STATE_START_FAILURE"))
        self.assertNotIn("fragmentor?.stopAndAwaitListeners()", helper)  # no main-thread join

    def test_existing_async_stop_still_requires_every_local_resource_exit(self):
        stop = self.stop
        self.assertIn("val stopToken = coreStopGate.beginStop()", stop)
        self.assertIn("val fragmentor = TLS_serv", stop)
        self.assertIn("fragmentor?.stopAndAwaitListeners()", stop)
        self.assertIn("service.stopAndAwaitTunDescriptorClose()", stop)
        self.assertIn("service.stopAndAwaitTun2socksExit()", stop)
        self.assertIn(
            "val stopped = coreStopped && fragmentorStopped && tunStopped && tunDescriptorClosed",
            stop
        )
        self.assertIn("coreStopGate.completeStop(stopToken, stopped)", stop)
        self.assertIn("if (!fragmentorStopped && fragmentor != null && TLS_serv == null)", stop)
        self.assertLess(stop.index("fragmentor?.stopAndAwaitListeners()"),
                        stop.index("MSG_STATE_STOP_SUCCESS"))


if __name__ == "__main__":
    unittest.main()
