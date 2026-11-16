"""Psiphon must not publish obsolete Android underlying-network callbacks."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "app/src/main/kotlin/com/v2ray/ang/service/PsiphonVpnService.kt"


class PsiphonUnderlyingNetworkOwnerContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text(encoding="utf-8")

    def test_callback_events_use_network_identity_and_session_epoch(self):
        code = self.source
        self.assertIn("UnderlyingNetworkOwner<Network>()", code)
        callbacks = code.split("private fun registerUnderlyingNetworkCallback()", 1)[1].split(
            "private fun releaseUnderlyingNetworkCallback()", 1
        )[0]
        self.assertIn("val epoch = underlyingNetworkOwner.begin()", callbacks)
        self.assertIn("underlyingNetworkOwner.onAvailable(epoch, network)", callbacks)
        self.assertIn("underlyingNetworkOwner.onCapabilitiesChanged(epoch, network)", callbacks)
        self.assertIn("underlyingNetworkOwner.onLost(epoch, network)", callbacks)
        self.assertIn("connectivity.requestNetwork(defaultNetworkRequest, callback)", callbacks)
        self.assertNotIn("setUnderlyingNetworks(", callbacks)

    def test_queued_updates_are_revalidated_before_publishing(self):
        publish = self.source.split("private fun postUnderlyingNetworkUpdate(", 1)[1].split(
            "private fun registerUnderlyingNetworkCallback()", 1
        )[0]
        self.assertIn("underlyingNetworkHandler.post", publish)
        self.assertIn("underlyingNetworkOwner.publishIfCurrent(update)", publish)
        self.assertIn("setUnderlyingNetworks(network?.let { arrayOf(it) })", publish)

    def test_register_only_after_tun_establishment(self):
        setup = self.source.split("private fun establishVpnInterface()", 1)[1].split(
            "private fun startTun2socksRouting(port: Int)", 1
        )[0]
        self.assertIn("mInterface = builder.establish()", setup)
        self.assertIn("registerUnderlyingNetworkCallback()", setup)
        self.assertLess(
            setup.index("mInterface = builder.establish()"),
            setup.index("registerUnderlyingNetworkCallback()"),
        )
        self.assertNotIn("private val defaultNetworkCallback by lazy", self.source)

    def test_api_21_does_not_post_unsupported_underlying_network_calls(self):
        release = self.source.split("private fun releaseUnderlyingNetworkCallback()", 1)[1].split(
            "// =========================================================================", 1
        )[0]
        # MahsaNG's minSdk is 21; VpnService.setUnderlyingNetworks needs API 22.
        # No callback is registered below API 28, so there is nothing to publish.
        self.assertRegex(
            release,
            r"val stopUpdate = underlyingNetworkOwner\.stop\(\)\s+"
            r"if \(Build\.VERSION\.SDK_INT >= Build\.VERSION_CODES\.P\) \{\s*"
            r"postUnderlyingNetworkUpdate\(stopUpdate\)",
        )

    def test_teardown_invalidates_epoch_before_unregistering_callback(self):
        release = self.source.split("private fun releaseUnderlyingNetworkCallback()", 1)[1].split(
            "// =========================================================================", 1
        )[0]
        self.assertIn("underlyingNetworkOwner.stop()", release)
        self.assertIn("connectivity.unregisterNetworkCallback(callback)", release)
        self.assertLess(
            release.index("underlyingNetworkOwner.stop()"),
            release.index("connectivity.unregisterNetworkCallback(callback)"),
        )
        teardown = self.source.split("private fun stopAll(", 1)[1].split(
            "override fun loadLibrary(", 1
        )[0]
        self.assertIn("releaseUnderlyingNetworkCallback()", teardown)


if __name__ == "__main__":
    unittest.main()
