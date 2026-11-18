"""Do not report Psiphon Stop Success before the observed JNI worker exits.

This contracts the live service's legacy notification/status boundary, NOT a
new cross-process VPN shutdown acknowledgement.
"""
from pathlib import Path
import unittest

SERVICE = (
    Path(__file__).resolve().parents[1]
    / "app/src/main/kotlin/com/v2ray/ang/service/PsiphonVpnService.kt"
)


class PsiphonStopCompletionContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shutdown = SERVICE.read_text(encoding="utf-8").split(
            "private fun stopAll(", 1
        )[1].split("override fun loadLibrary(", 1)[0]

    def test_native_worker_reference_is_retained_if_join_times_out(self):
        stop = self.shutdown
        self.assertIn("val worker = tun2socksThread", stop)
        self.assertIn("worker.join(3000)", stop)
        self.assertIn("val workerExited =", stop)
        self.assertIn("if (workerExited) tun2socksThread = null", stop)
        self.assertNotIn("tun2socksThread = null\n\n        // Clear the handle", stop)
        self.assertLess(stop.index("worker.join(3000)"), stop.index("val workerExited ="))
        self.assertLess(stop.index("val workerExited ="),
                        stop.index("if (workerExited) tun2socksThread = null"))

    def test_stop_report_requires_observed_local_cleanup(self):
        stop = self.shutdown
        self.assertIn("PsiphonTeardownEvidence(", stop)
        self.assertIn("tunnelStopReturned", stop)
        self.assertIn("tunCloseReturned", stop)
        self.assertIn("if (evidence.localStopReportable)", stop)
        self.assertIn(
            "MessageUtil.sendMsg2UI(this, AppConfig.MSG_STATE_STOP_SUCCESS, \"\")",
            stop,
        )
        self.assertIn("AppConfig.MSG_STATE_NOT_RUNNING", stop)
        self.assertLess(stop.index("if (evidence.localStopReportable)"),
                        stop.index("AppConfig.MSG_STATE_STOP_SUCCESS"))

    def test_upstream_stop_request_is_not_claimed_as_native_ack(self):
        stop = self.shutdown
        self.assertIn("stopService(Intent(this, V2RayProxyOnlyService::class.java))", stop)
        self.assertIn("dependsOnXray = usesUpstreamProxy", stop)
        self.assertIn("psiphonNativeStopAcknowledged = false", stop)
        self.assertIn("xrayNativeStopAcknowledged = false", stop)
        self.assertIn("!evidence.wholeChainCompletionEligible", stop)

    def test_failed_native_signal_still_attempts_all_resource_closes(self):
        stop = self.shutdown
        self.assertIn("runCatching { Tun2SocksJniLoader.terminateTun2Socks() }", stop)
        self.assertIn("mInterface?.close()", stop)
        self.assertIn("tunnel?.stop()", stop)
        self.assertIn("startGate.stop()", stop)
        self.assertIn("releaseUnderlyingNetworkCallback()", stop)


if __name__ == "__main__":
    unittest.main()
