"""Service-owned Xray TUN closure must be observed before legacy Stop Success.

This contract concerns ParcelFileDescriptor.close() returning for a tracked
descriptor, NOT native aliases, cross-process receipts, or leak-safe routing.
"""
from pathlib import Path
import unittest

BASE = Path(__file__).resolve().parents[1] / "app/src/main/kotlin/com/v2ray/ang/service"
VPN = BASE / "V2RayVpnService.kt"
MANAGER = BASE / "V2RayServiceManager.kt"


class XrayTunDescriptorCloseContract(unittest.TestCase):
    def test_setup_tracks_establishment_before_publishing_descriptor(self):
        vpn = VPN.read_text(encoding="utf-8")
        setup = vpn.split("private fun setup() {", 1)[1].split("private fun runTun2socks(", 1)[0]
        self.assertIn("tunCloseTracker.beginEstablish()", setup)
        self.assertIn("tunCloseTracker.registered(established)", setup)
        self.assertIn("tunCloseTracker.establishFailed()", setup)
        self.assertIn("closeTrackedTunDescriptor(established)", setup)
        self.assertLess(setup.index("tunCloseTracker.beginEstablish()"), setup.index("builder.establish()"))
        self.assertLess(setup.index("tunCloseTracker.registered(established)"),
                        setup.index("mInterface = established"))

    def test_close_is_evidence_only_after_the_owned_close_returns_successfully(self):
        vpn = VPN.read_text(encoding="utf-8")
        helper = vpn.split("private fun closeTrackedTunDescriptor(", 1)[1].split(
            "private fun stopV2Ray(", 1
        )[0]
        self.assertIn("descriptor.close()", helper)
        self.assertIn("tunCloseTracker.closeReturned(descriptor)", helper)
        self.assertIn("if (closed)", helper)
        self.assertLess(helper.index("descriptor.close()"), helper.index("tunCloseTracker.closeReturned(descriptor)"))
        self.assertIn("tunCloseTracker.requestStop()", helper)
        self.assertIn("tunCloseTracker.awaitClosed(", helper)

    def test_all_lifecycle_shutdown_paths_close_tracked_descriptor(self):
        vpn = VPN.read_text(encoding="utf-8")
        destroy = vpn.split("override fun onDestroy() {", 1)[1].split("private fun setup()", 1)[0]
        stop = vpn.split("private fun stopV2Ray(", 1)[1].split("override fun getService()", 1)[0]
        self.assertIn("closeOwnedTunDescriptors()", destroy)
        self.assertIn("closeOwnedTunDescriptors()", stop)
        self.assertIn("stopSelf()", stop)
        self.assertLess(stop.index("stopSelf()"), stop.index("closeOwnedTunDescriptors()"))
        self.assertNotIn("runCatching { mInterface.close() }", destroy)
        self.assertNotIn("mInterface.close()", stop)
        self.assertNotIn("Thread.sleep(", destroy)

    def test_manager_success_requires_service_owned_fd_close_and_subprocess_exit(self):
        manager = MANAGER.read_text(encoding="utf-8")
        stop = manager.split("fun stopV2rayPoint() {", 1)[1].split(
            "private class ReceiveMessageHandler", 1
        )[0]
        self.assertIn("service.stopAndAwaitTun2socksExit()", stop)
        self.assertIn("service.stopAndAwaitTunDescriptorClose()", stop)
        self.assertIn("val stopped = coreStopped && fragmentorStopped && tunStopped && tunDescriptorClosed", stop)
        self.assertIn("coreStopGate.completeStop(stopToken, stopped)", stop)
        self.assertLess(stop.index("val stopped = coreStopped && fragmentorStopped && tunStopped && tunDescriptorClosed"),
                        stop.index("AppConfig.MSG_STATE_STOP_SUCCESS"))
        self.assertNotIn("VpnNativeStopEvidence.Xray", stop)


if __name__ == "__main__":
    unittest.main()
