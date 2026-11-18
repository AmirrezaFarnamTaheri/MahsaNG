"""Regression: destroying the Xray VpnService must not orphan native core or TUN."""
from pathlib import Path
import unittest

SERVICES = Path(__file__).resolve().parents[1] / "app/src/main/kotlin/com/v2ray/ang/service"


class XrayVpnDestroyCleanupContractTest(unittest.TestCase):
    def test_on_destroy_closes_tun_and_requests_owned_native_shutdown(self):
        code = (SERVICES / "V2RayVpnService.kt").read_text(encoding="utf-8")
        teardown = code.split("override fun onDestroy() {", 1)[1].split(
            "private fun setup()", 1
        )[0]

        self.assertIn("stopOwnedTun2socks()", teardown)
        self.assertNotIn("tunProcesses.stop()?.destroy()", teardown)
        self.assertIn("releaseUnderlyingNetworkCallback()", teardown)
        self.assertIn("fdScope.cancel()", teardown)
        self.assertIn("if (this::mInterface.isInitialized)", teardown)
        self.assertIn("mInterface.close()", teardown)
        self.assertIn("V2RayServiceManager.stopV2rayPointIfOwner(this, cancelForeground = true)", teardown)
        self.assertLess(
            teardown.index("V2RayServiceManager.stopV2rayPointIfOwner(this, cancelForeground = true)"),
            teardown.index("super.onDestroy()"),
        )

    def test_stale_service_destruction_does_not_stop_new_owner(self):
        vpn = (SERVICES / "V2RayVpnService.kt").read_text(encoding="utf-8")
        teardown = vpn.split("override fun onDestroy() {", 1)[1].split(
            "private fun setup()", 1
        )[0]
        self.assertIn(
            "V2RayServiceManager.stopV2rayPointIfOwner(this, cancelForeground = true)",
            teardown,
        )
        self.assertNotIn("V2RayServiceManager.serviceControl?.get()", teardown)
        self.assertNotIn("V2RayServiceManager.cancelNotification()", teardown)

    def test_stale_proxy_only_destruction_cannot_stop_new_owner(self):
        proxy = (SERVICES / "V2RayProxyOnlyService.kt").read_text(encoding="utf-8")
        teardown = proxy.split("override fun onDestroy() {", 1)[1].split(
            "override fun getService()", 1
        )[0]
        self.assertIn("V2RayServiceManager.stopV2rayPointIfOwner(this)", teardown)
        self.assertNotIn("V2RayServiceManager.serviceControl?.get()", teardown)

    def test_stale_vpn_revoke_releases_own_tun_without_stopping_new_owner(self):
        vpn = (SERVICES / "V2RayVpnService.kt").read_text(encoding="utf-8")
        stop = vpn.split("private fun stopV2Ray(", 1)[1].split(
            "override fun getService()", 1
        )[0]
        self.assertIn("stopOwnedTun2socks()", stop)
        self.assertIn("releaseUnderlyingNetworkCallback()", stop)
        self.assertIn("mInterface.close()", stop)
        self.assertIn("V2RayServiceManager.stopV2rayPointIfOwner(this)", stop)
        self.assertNotIn("V2RayServiceManager.serviceControl?.get()", stop)

    def test_owner_registration_and_shutdown_share_one_monitor(self):
        manager = (SERVICES / "V2RayServiceManager.kt").read_text(encoding="utf-8")
        self.assertRegex(
            manager,
            r"var serviceControl: SoftReference<ServiceControl>\? = null\s+"
            r"@Synchronized\s+set\(value\)",
        )
        self.assertRegex(manager, r"@Synchronized\s+fun stopV2rayPointIfOwner\(")
        guard = manager.split("fun stopV2rayPointIfOwner(", 1)[1].split(
            "fun stopV2rayPoint()", 1
        )[0]
        self.assertIn("val activeOwner = serviceControl?.get()", guard)
        self.assertIn("if (activeOwner != null && activeOwner !== requester) return false", guard)
        self.assertIn("stopV2rayPoint()", guard)
        self.assertIn("if (cancelForeground)", guard)
        self.assertIn("cancelNotificationFor(requester.getService())", guard)
        self.assertLess(
            guard.index("if (activeOwner != null && activeOwner !== requester) return false"),
            guard.index("stopV2rayPoint()"),
        )


if __name__ == "__main__":
    unittest.main()
