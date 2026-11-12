"""Psiphon routing must not claim connected before JNI routing starts."""
from pathlib import Path
import unittest

SOURCE = (
    Path(__file__).resolve().parents[1] /
    "app/src/main/kotlin/com/v2ray/ang/service/PsiphonVpnService.kt"
)


class PsiphonRoutingCallbackContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = SOURCE.read_text(encoding="utf-8")

    def test_both_native_callback_orders_can_activate_routing(self):
        connected = self.text.split("override fun onConnected()", 1)[1].split(
            "override fun onExiting()", 1
        )[0]
        port = self.text.split("override fun onListeningSocksProxyPort(", 1)[1].split(
            "override fun onListeningHttpProxyPort(", 1
        )[0]
        self.assertIn("routeGate.onConnected()", connected)
        self.assertIn("routeGate.onSocksPort(port)", port)
        self.assertIn("PsiphonRouteAction.RestartRequired", connected)

    def test_native_exit_triggers_cleanup_not_stale_connected_state(self):
        exiting = self.text.split("override fun onExiting()", 1)[1].split(
            "override fun onListeningSocksProxyPort(", 1
        )[0]
        self.assertIn("stopAll()", exiting)

    def test_private_diagnostics_are_not_logged_verbatim(self):
        logs = self.text.split("override fun onDiagnosticMessage(", 1)[1].split(
            "override fun onStartedWaitingForNetworkConnectivity(", 1
        )[0]
        self.assertNotIn("Log.d(TAG, \"Psiphon: $message\")", logs)
        self.assertIn('config.put("EmitDiagnosticNetworkParameters", false)', self.text)


if __name__ == "__main__":
    unittest.main()
