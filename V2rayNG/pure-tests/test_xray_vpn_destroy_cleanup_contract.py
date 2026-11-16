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

        self.assertIn("tunProcesses.stop()?.destroy()", teardown)
        self.assertIn("releaseUnderlyingNetworkCallback()", teardown)
        self.assertIn("fdScope.cancel()", teardown)
        self.assertIn("if (this::mInterface.isInitialized)", teardown)
        self.assertIn("mInterface.close()", teardown)
        self.assertIn("V2RayServiceManager.stopV2rayPoint()", teardown)
        self.assertLess(
            teardown.index("V2RayServiceManager.stopV2rayPoint()"),
            teardown.index("super.onDestroy()"),
        )

    def test_stale_service_destruction_does_not_stop_new_owner(self):
        code = (SERVICES / "V2RayVpnService.kt").read_text(encoding="utf-8")
        teardown = code.split("override fun onDestroy() {", 1)[1].split(
            "private fun setup()", 1
        )[0]
        self.assertIn("val activeOwner = V2RayServiceManager.serviceControl?.get()", teardown)
        self.assertIn("if (activeOwner == null || activeOwner === this)", teardown)
        self.assertIn("V2RayServiceManager.cancelNotification()", teardown)

    def test_stale_proxy_only_destruction_cannot_stop_new_owner(self):
        code = (SERVICES / "V2RayProxyOnlyService.kt").read_text(encoding="utf-8")
        teardown = code.split("override fun onDestroy() {", 1)[1].split(
            "override fun getService()", 1
        )[0]
        self.assertIn("val activeOwner = V2RayServiceManager.serviceControl?.get()", teardown)
        self.assertRegex(
            teardown,
            r"if \(activeOwner == null \|\| activeOwner === this\)\s*"
            r"\{\s*V2RayServiceManager\.stopV2rayPoint\(\)",
        )

    def test_stale_vpn_revoke_releases_own_tun_without_stopping_new_owner(self):
        code = (SERVICES / "V2RayVpnService.kt").read_text(encoding="utf-8")
        stop = code.split("private fun stopV2Ray(", 1)[1].split(
            "override fun getService()", 1
        )[0]
        self.assertIn("tunProcesses.stop()", stop)
        self.assertIn("releaseUnderlyingNetworkCallback()", stop)
        self.assertIn("mInterface.close()", stop)
        self.assertIn("val activeOwner = V2RayServiceManager.serviceControl?.get()", stop)
        self.assertRegex(
            stop,
            r"if \(activeOwner == null \|\| activeOwner === this\)\s*"
            r"\{\s*V2RayServiceManager\.stopV2rayPoint\(\)",
        )

    def test_proxy_only_service_keeps_matching_stop_on_destroy(self):
        code = (SERVICES / "V2RayProxyOnlyService.kt").read_text(encoding="utf-8")
        teardown = code.split("override fun onDestroy() {", 1)[1].split(
            "override fun getService()", 1
        )[0]
        self.assertIn("V2RayServiceManager.stopV2rayPoint()", teardown)


if __name__ == "__main__":
    unittest.main()
