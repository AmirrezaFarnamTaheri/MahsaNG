"""Regression contracts for live-core delay results after stop or restart."""
from pathlib import Path
import unittest

SOURCE = (
    Path(__file__).resolve().parents[1]
    / "app/src/main/kotlin/com/v2ray/ang/service/V2RayServiceManager.kt"
)


class LiveCoreDelayObservationContract(unittest.TestCase):
    def setUp(self):
        code = SOURCE.read_text(encoding="utf-8")
        self.top = code.split("private class V2RayCallback", 1)[0]
        self.start = code.split("fun startV2rayPoint() {", 1)[1].split(
            "fun stopV2rayPoint() {", 1
        )[0]
        self.stop = code.split("fun stopV2rayPoint() {", 1)[1].split(
            "private class ReceiveMessageHandler", 1
        )[0]
        self.measure = code.split("private fun measureV2rayDelay() {", 1)[1].split(
            "private fun showNotification()", 1
        )[0]

    def test_measurement_runs_in_owned_scope_not_global_scope(self):
        self.assertNotIn("GlobalScope.launch(", self.measure)
        self.assertIn("liveDelayScope.launch", self.measure)
        self.assertIn("liveDelayTracker.begin(", self.measure)

    def test_start_and_stop_invalidate_old_jni_observations(self):
        self.assertIn("invalidateLiveDelay()", self.start)
        self.assertIn("invalidateLiveDelay()", self.stop)
        self.assertIn("liveDelayJob?.cancel()", self.top)

    def test_rejected_delay_requests_terminate_the_testing_state(self):
        self.assertIn("if (guid == null || !v2rayPoint.isRunning)", self.measure)
        rejection = self.measure.split(
            "if (guid == null || !v2rayPoint.isRunning)", 1
        )[1].split("val runId = liveDelayTracker.begin", 1)[0]
        self.assertIn("AppConfig.MSG_MEASURE_DELAY_SUCCESS", rejection)
        self.assertIn("service.getString(R.string.connection_test_error", rejection)
        self.assertIn("return", rejection)

    def test_result_requires_current_token_running_core_and_selected_profile(self):
        for gate in (
            "synchronized(V2RayServiceManager)",
            "liveDelayTracker.accepts(runId, guid)",
            "v2rayPoint.isRunning",
            "serviceControl?.get()?.getService() !== service",
            "decodeString(MmkvManager.KEY_SELECTED_SERVER) != guid",
        ):
            self.assertIn(gate, self.measure)
        self.assertLess(
            self.measure.index("liveDelayTracker.accepts(runId, guid)"),
            self.measure.index("MessageUtil.sendMsg2UI(service, AppConfig.MSG_MEASURE_DELAY_SUCCESS"),
        )


if __name__ == "__main__":
    unittest.main()
