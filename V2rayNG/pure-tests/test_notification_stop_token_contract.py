"""Notification-generated Stop actions must be scoped to a service instance.

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
        self.assertIn("intent.data?.scheme", stop)
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

    def test_xray_stale_notification_stop_does_not_target_replacement_owner(self):
        text = (ROOT / "V2RayServiceManager.kt").read_text(encoding="utf-8")
        setter = text.split("var serviceControl:", 1)[1].split(
            "var currentConfig:", 1
        )[0]
        self.assertIn("notificationStopTokenGate.invalidate()", setter)
        stop_method = text.split("fun stopV2rayPoint()", 1)[1].split(
            "private class ReceiveMessageHandler", 1
        )[0]
        self.assertIn("notificationStopTokenGate.invalidate()", stop_method)
        stop_branch = text.split("AppConfig.MSG_STATE_STOP -> {", 1)[1].split(
            "AppConfig.MSG_STATE_RESTART -> {", 1
        )[0]
        self.assertIn("notificationStopTokenGate.accepts(", stop_branch)
        self.assertIn("intent?.data", stop_branch)
        self.assertIn("synchronized(V2RayServiceManager)", stop_branch)
        self.assertLess(stop_branch.index("notificationStopTokenGate.accepts("),
                        stop_branch.index("stopService()"))
        notification = text.split("private fun showNotification()", 1)[1].split(
            "private fun createNotificationChannel(", 1
        )[0]
        self.assertIn("notificationStopTokenGate.arm(", notification)
        self.assertIn("stopV2RayIntent.data = Uri.parse(", notification)
        self.assertLess(notification.index("stopV2RayIntent.data = Uri.parse("),
                        notification.index("PendingIntent.getBroadcast("))

    def test_legacy_ui_stop_broadcast_is_preserved_until_shared_intent_migration(self):
        text = (ROOT / "V2RayServiceManager.kt").read_text(encoding="utf-8")
        stop_branch = text.split("AppConfig.MSG_STATE_STOP -> {", 1)[1].split(
            "AppConfig.MSG_STATE_RESTART -> {", 1
        )[0]
        # A data-less legacy UI broadcast is deliberately still accepted.
        # The new fence is limited to our own notification URI scheme.
        self.assertIn("NOTIFICATION_STOP_SCHEME", stop_branch)
        self.assertIn("requestData?.scheme", stop_branch)
        self.assertIn("stopService()", stop_branch)


if __name__ == "__main__":
    unittest.main()
