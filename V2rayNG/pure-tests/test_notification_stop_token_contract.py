"""Psiphon notification Stop actions must belong to the current service instance.

This test protects the Kotlin-to-Android PendingIntent integration; the pure
Kotlin NotificationStopTokenGateTest covers token lifecycle behavior.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / "app/src/main/kotlin/com/v2ray/ang/service"


class NotificationStopCommandContract(unittest.TestCase):
    def test_psiphon_stop_action_requires_current_notification_token(self):
        text = (ROOT / "PsiphonVpnService.kt").read_text(encoding="utf-8")
        start = text.split("override fun onStartCommand(", 1)[1].split(
            "override fun onBind(", 1
        )[0]
        stop = start.split("if (intent?.action == ACTION_STOP)", 1)[1].split(
            "if (teardownStarted.get())", 1
        )[0]
        self.assertIn("notificationStopTokenGate.accepts(", stop)
        self.assertIn("stopData?.scheme", stop)
        self.assertIn("return if (startCommandAccepted.get()) START_STICKY else START_NOT_STICKY", stop)

        self.assertLess(stop.index("notificationStopTokenGate.accepts("),
                        stop.index("stopAll()"))
        notification = text.split("private fun startForegroundNotification()", 1)[1].split(
            "private fun updateNotification(", 1
        )[0]
        self.assertIn("stopIntent.data = Uri.parse(", notification)
        self.assertLess(notification.index("stopIntent.data = Uri.parse("),
                        notification.index("PendingIntent.getService("))
        self.assertIn("notificationStopTokenGate.invalidate()", text)
        self.assertIn("UUID.randomUUID()", text)

    def test_rejected_stale_stop_cannot_destroy_unowned_upstream_proxy(self):
        source = (ROOT / "PsiphonVpnService.kt").read_text(encoding="utf-8")
        start = source.split("override fun onStartCommand(", 1)[1].split(
            "override fun onBind(", 1
        )[0]
        destroy = source.split("override fun onDestroy()", 1)[1].split(
            "override fun onStartCommand(", 1
        )[0]
        self.assertIn("private val startCommandAccepted = AtomicBoolean(false)", source)
        self.assertIn("startCommandAccepted.set(true)", start)
        self.assertLess(start.index("if (intent?.action == ACTION_STOP)"),
                        start.index("startCommandAccepted.set(true)"))
        self.assertLess(start.index("startCommandAccepted.set(true)"),
                        start.index("VpnService.prepare(this)"))
        # Android may start a fresh service only to deliver an old PendingIntent.
        # Destroying that never-started service must not stop another Xray owner.
        self.assertIn(
            "if (startCommandAccepted.get()) stopAll(isForced = false)", destroy
        )



if __name__ == "__main__":
    unittest.main()
