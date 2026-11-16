"""Require nonblocking inter-process writer coordination for MMKV's shared index."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
MMKV = ROOT / "app/src/main/kotlin/com/v2ray/ang/util/MmkvManager.kt"
MAIN = ROOT / "app/src/main/kotlin/com/v2ray/ang/ui/MainActivity.kt"


class CrossProcessIndexContract(unittest.TestCase):
    def test_index_writes_use_native_interprocess_lease(self):
        source = MMKV.read_text()
        self.assertIn("main.tryLock()", source)
        self.assertIn("main.unlock()", source)
        self.assertIn("ProfileIndexMutationGate.execute(", source)
        for method in (
            "encodeServerConfig", "removeServer", "swapServerPositions",
            "replaceSubscriptionServers", "removeServerViaSubid",
            "removeSubscription", "removeAllServer",
            "removeConfirmedFailedServers", "removeDuplicateServers",
            "sortByTestResults",
        ):
            match = re.search(r"fun\s+" + method + r"\s*\(", source)
            self.assertIsNotNone(match, method)
            excerpt = source[match.start():match.start() + 350]
            self.assertIn("withIndexLease(", excerpt, method)

    def test_nested_subscription_deletion_uses_single_index_lease(self):
        source = MMKV.read_text()
        block = source.split("fun removeSubscription(", 1)[1].split("fun removeAllServer(", 1)[0]
        self.assertIn("removeServerViaSubidLocked(subid)", block)
        self.assertIn("subStorage?.remove(subid)", block)
        self.assertNotIn("if (removeServerViaSubid(subid))", block)

    def test_import_fails_closed_when_crossprocess_lease_is_busy(self):
        source = (ROOT / "app/src/main/kotlin/com/v2ray/ang/util/AngConfigManager.kt").read_text()
        self.assertIn('if (guid.isBlank()) return -1', source)
        self.assertIn('if (key.isBlank()) return count', source)
        self.assertIn('if (key.isBlank()) return 0', source)
        self.assertIn('if (key.isNotBlank() && index == angConfig.index)', source)
        self.assertIn('if (guid.isBlank()) return ""', source)

    def test_import_selection_is_serialized_with_index_revision(self):
        mmkv = MMKV.read_text()
        imports = (ROOT / "app/src/main/kotlin/com/v2ray/ang/util/AngConfigManager.kt").read_text()
        self.assertIn("fun selectExistingServer(guid: String): Boolean", mmkv)
        section = mmkv.split("fun selectExistingServer(guid: String): Boolean", 1)[1].split("fun ", 1)[0]
        self.assertIn("withIndexLease(false)", section)
        self.assertIn("guid !in readServerIndex()", section)
        self.assertIn("main.encode(KEY_SELECTED_SERVER, guid)", section)
        self.assertNotIn("mainStorage?.encode(KEY_SELECTED_SERVER", imports)
        self.assertIn("MmkvManager.selectExistingServer(guid)", imports)
        self.assertIn("MmkvManager.selectExistingServer(key)", imports)

    def test_busy_clear_all_is_visible_as_failure_not_false_success(self):
        source = MMKV.read_text()
        self.assertIn("fun removeAllServer(): Boolean", source)
        activity = MAIN.read_text()
        self.assertIn("val completed = withContext(Dispatchers.IO) { MmkvManager.removeAllServer() }", activity)
        self.assertIn("if (completed)", activity)
        self.assertIn("toast(R.string.toast_failure)", activity)


if __name__ == "__main__":
    unittest.main()
