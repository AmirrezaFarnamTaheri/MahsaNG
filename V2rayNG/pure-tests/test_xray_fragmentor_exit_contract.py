"""Xray local Stop Success must not precede observed fragmentor listener exit.

This is only a legacy local status guard, NOT a native cross-process receipt.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MANAGER = ROOT / "app/src/main/kotlin/com/v2ray/ang/service/V2RayServiceManager.kt"
BACKSERV = ROOT / "app/src/main/kotlin/com/v2ray/ang/gfwknocker/BackServ.kt"


class XrayFragmentorExitContract(unittest.TestCase):
    def test_backserv_requests_both_stops_before_waiting_for_exit(self):
        code = BACKSERV.read_text(encoding="utf-8")
        section = code.split("fun stopAndAwaitListeners(", 1)[1]
        self.assertIn("stop_HTTPS_service()", section)
        self.assertIn("stop_TLS_service()", section)
        self.assertIn("FragmentorListenerExit.allExitedWithin(", section)
        self.assertLess(section.index("stop_HTTPS_service()"), section.index("FragmentorListenerExit.allExitedWithin("))
        self.assertLess(section.index("stop_TLS_service()"), section.index("FragmentorListenerExit.allExitedWithin("))

    def test_manager_only_reports_local_stop_after_fragmentor_exit(self):
        code = MANAGER.read_text(encoding="utf-8")
        stop = code.split("fun stopV2rayPoint() {", 1)[1].split("private class ReceiveMessageHandler", 1)[0]
        self.assertIn("stopAndAwaitListeners(", stop)
        self.assertIn("val stopped = coreStopped && fragmentorStopped", stop)
        self.assertLess(stop.index("val stopped = coreStopped && fragmentorStopped"), stop.index("MSG_STATE_STOP_SUCCESS"))
        self.assertIn("coreStopGate.completeStop(stopToken, stopped)", stop)

    def test_unverified_fragmentor_keeps_ownership_and_suppresses_not_running(self):
        code = MANAGER.read_text(encoding="utf-8")
        stop = code.split("fun stopV2rayPoint() {", 1)[1].split("private class ReceiveMessageHandler", 1)[0]
        self.assertIn("if (!fragmentorStopped && fragmentor != null && TLS_serv == null)", stop)
        self.assertIn("TLS_serv = fragmentor", stop)
        self.assertNotIn("AppConfig.MSG_STATE_NOT_RUNNING", stop)


if __name__ == "__main__":
    unittest.main()
