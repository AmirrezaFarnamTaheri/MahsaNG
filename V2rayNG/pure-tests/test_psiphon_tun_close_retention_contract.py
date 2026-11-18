"""Live Psiphon service must retain its TUN PFD when close throws.

A returned ParcelFileDescriptor.close() proves only the Java owner closed.
It does not certify native FD aliases, JNI worker exit or full VPN shutdown.
"""
from pathlib import Path
import unittest

BASE = Path(__file__).resolve().parents[1] / "app/src/main/kotlin/com/v2ray/ang/service"
PSIPHON = BASE / "PsiphonVpnService.kt"


class PsiphonTunCloseRetentionContract(unittest.TestCase):
    def test_service_reuses_owned_tun_close_tracker_for_establishment_and_replacement(self):
        service = PSIPHON.read_text(encoding="utf-8")
        setup = service.split("private fun establishVpnInterface() {", 1)[1].split(
            "private fun startTun2socksRouting(", 1
        )[0]
        self.assertIn("TunDescriptorCloseTracker<ParcelFileDescriptor>()", service)
        self.assertIn("tunCloseTracker.beginEstablish()", setup)
        self.assertIn("tunCloseTracker.registered(established)", setup)
        self.assertIn("tunCloseTracker.establishFailed()", setup)
        self.assertIn("closeTrackedTunDescriptor(oldInterface)", setup)
        self.assertLess(setup.index("tunCloseTracker.beginEstablish()"),
                        setup.index("builder.establish()"))
        self.assertLess(setup.index("tunCloseTracker.registered(established)"),
                        setup.index("mInterface = established"))
        self.assertNotIn("mInterface?.close()", setup)

    def test_descriptor_remains_owned_after_failed_close_and_clears_only_after_success(self):
        service = PSIPHON.read_text(encoding="utf-8")
        close_helper = service.split("private fun closeTrackedTunDescriptor(", 1)[1].split(
            "private fun stopAll(", 1
        )[0]
        self.assertIn("tunCloseTracker.isOutstanding(descriptor)", close_helper)
        self.assertIn("runCatching { descriptor.close() }", close_helper)
        self.assertIn("if (closed)", close_helper)
        self.assertIn("tunCloseTracker.closeReturned(descriptor)", close_helper)
        self.assertIn("if (mInterface === descriptor) mInterface = null", close_helper)
        self.assertLess(close_helper.index("descriptor.close()"),
                        close_helper.index("tunCloseTracker.closeReturned(descriptor)"))
        self.assertIn("tunCloseTracker.requestStop()", close_helper)
        self.assertIn("tunCloseTracker.isStopComplete()", close_helper)

    def test_shutdown_preserves_handle_and_withholds_local_success_when_close_unverified(self):
        service = PSIPHON.read_text(encoding="utf-8")
        stop = service.split("private fun stopAll(", 1)[1].split(
            "override fun loadLibrary(", 1
        )[0]
        self.assertIn("val tunCloseReturned = closeOwnedTunDescriptors()", stop)
        self.assertIn("tunCloseReturned = tunCloseReturned", stop)
        self.assertIn("if (evidence.localStopReportable)", stop)
        self.assertNotIn("finally {\n            mInterface = null", stop)
        self.assertNotIn("mInterface?.close()", stop)
        self.assertIn("stopCleanupFinished.set(true)", stop)

    def test_destroy_retries_after_terminal_shutdown_without_reissuing_native_stop(self):
        service = PSIPHON.read_text(encoding="utf-8")
        destroy = service.split("override fun onDestroy() {", 1)[1].split(
            "override fun onStartCommand(", 1
        )[0]
        self.assertIn("stopAll(isForced = false)", destroy)
        self.assertIn("stopCleanupFinished.get()", destroy)
        self.assertIn("closeOwnedTunDescriptors()", destroy)
        self.assertNotIn("Tun2SocksJniLoader.terminateTun2Socks()", destroy)
        self.assertNotIn("VpnNativeStopEvidence", service)


if __name__ == "__main__":
    unittest.main()
