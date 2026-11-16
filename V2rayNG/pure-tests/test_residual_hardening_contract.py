"""Regression contract for fail-closed MMKV indexes and epoch-owned VPN callbacks."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
KOTLIN = ROOT / "app/src/main/kotlin/com/v2ray/ang"


class ResidualHardeningContractTest(unittest.TestCase):
    def test_vpn_uses_epoch_owner_and_drops_stale_network_callbacks(self):
        code = (KOTLIN / "service/V2RayVpnService.kt").read_text()
        self.assertIn("UnderlyingNetworkOwner<Network>()", code)
        self.assertIn("owner.onLost(epoch, network)", code)
        self.assertIn("owner.onCapabilitiesChanged(epoch, network)", code)
        self.assertIn("owner.publishIfCurrent(update)", code)
        self.assertIn("releaseUnderlyingNetworkCallback()", code)
        self.assertNotIn("setUnderlyingNetworks(null)\n            }", code)

    def test_corrupt_profile_index_cannot_be_treated_as_empty_during_writes(self):
        code = (KOTLIN / "util/MmkvManager.kt").read_text()
        self.assertIn("ProfileIndexSafety.decode(", code)
        self.assertIn("private fun readServerIndex(): MutableList<String>?", code)
        self.assertIn("val serverList = readServerIndex() ?: return", code)
        self.assertIn("val oldIndex = readServerIndex() ?: return false", code)
        self.assertIn("val currentGuids = readServerIndex() ?: return 0", code)
        self.assertIn("val initial = readServerIndex()?.toList() ?: return false", code)

    def test_delete_all_is_dispatched_off_main_thread(self):
        code = (KOTLIN / "ui/MainActivity.kt").read_text()
        delete = code.split("R.id.del_all_config -> {", 1)[1].split("R.id.del_duplicate_config -> {", 1)[0]
        self.assertIn("withContext(Dispatchers.IO) { MmkvManager.removeAllServer() }", delete)
        self.assertIn("mainViewModel.reloadServerList()", delete)

    def test_subscription_is_not_removed_before_profile_index_commit(self):
        code = (KOTLIN / "util/MmkvManager.kt").read_text()
        remove = code.split("fun removeSubscription(subid: String)", 1)[1].split("fun removeAllServer()", 1)[0]
        self.assertIn("if (removeServerViaSubid(subid))", remove)
        self.assertIn("subStorage?.remove(subid)", remove)


if __name__ == "__main__":
    unittest.main()
