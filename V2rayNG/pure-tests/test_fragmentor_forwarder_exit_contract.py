"""Fragmentor Stop Success requires observed per-client worker exit.

Source contracts supplement pure worker lifecycle tests; Android/TUN/native
completion is outside this policy's scope.
"""
from pathlib import Path
import unittest

APP = Path(__file__).resolve().parents[1] / "app/src/main/kotlin/com/v2ray/ang"
TLS = APP / "gfwknocker/TLS_Fragmentor.kt"
HTTPS = APP / "gfwknocker/HTTPS_Fragmentor.kt"
BACK = APP / "gfwknocker/BackServ.kt"
MANAGER = APP / "service/V2RayServiceManager.kt"


class ForwarderExitContract(unittest.TestCase):
    def test_both_listener_types_track_upstream_before_start_and_stop_all_workers(self):
        for path in (TLS, HTTPS):
            with self.subTest(path=path.name):
                code = path.read_text(encoding="utf-8")
                listener = code.split("class ", 1)[1].split("internal class My_upstream", 1)[0]
                self.assertIn("private val forwarders = FragmentorForwardingWorkers()", listener)
                self.assertIn("forwarders.start(up_thread, accepted)", listener)
                self.assertIn("forwarders.stop()", listener)
                self.assertIn("fun awaitForwardersExited(", listener)
                self.assertIn("forwarders.awaitExited(", listener)
                self.assertIn("if (!forwarders.start(up_thread, accepted))", listener)
                self.assertIn("runCatching { accepted.close() }", listener)
                self.assertNotIn("FragmentorSocketBinding.closeQuietly(accepted)", listener)

    def test_upstreams_track_backend_sockets_and_downstream_threads(self):
        for path in (TLS, HTTPS):
            with self.subTest(path=path.name):
                code = path.read_text(encoding="utf-8")
                up = code.split("internal class My_upstream", 1)[1].split(
                    "internal class My_downstream", 1
                )[0]
                self.assertIn("forwarders: FragmentorForwardingWorkers", up)
                self.assertIn("forwarders.track(this, backend_sock!!)", up)
                self.assertIn("forwarders.start(down_thread", up)
                self.assertNotIn("down_thread.start()", up)

    def test_stop_outcome_requires_all_listeners_and_client_threads_to_exit(self):
        code = BACK.read_text(encoding="utf-8")
        stop = code.split("fun stopAndAwaitListeners(", 1)[1]
        self.assertIn("stop_HTTPS_service()", stop)
        self.assertIn("stop_TLS_service()", stop)
        self.assertIn("FragmentorListenerExit.allExitedWithin(", stop)
        self.assertIn("HTTPS_serv?.awaitForwardersExited(", stop)
        self.assertIn("TLS_serv?.awaitForwardersExited(", stop)
        self.assertIn("val allExited = listenersExited && httpsForwardersExited && tlsForwardersExited", stop)
        self.assertIn("return httpsStopReturned && tlsStopReturned && allExited", stop)

    def test_native_manager_keeps_existing_fail_closed_fragmentor_gate(self):
        code = MANAGER.read_text(encoding="utf-8")
        cleanup = code.split("fun stopV2rayPoint() {", 1)[1].split(
            "private class ReceiveMessageHandler", 1
        )[0]
        self.assertIn("fragmentor?.stopAndAwaitListeners()", cleanup)
        self.assertIn("val stopped = coreStopped && fragmentorStopped && tunStopped && tunDescriptorClosed", cleanup)
        self.assertIn("coreStopGate.completeStop(stopToken, stopped)", cleanup)
        self.assertLess(cleanup.index("fragmentor?.stopAndAwaitListeners()"), cleanup.index("MSG_STATE_STOP_SUCCESS"))


if __name__ == "__main__":
    unittest.main()
