"""Guard against re-selecting a different account at the same endpoint after refresh."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / "app/src/main/kotlin/com/v2ray/ang"
MANAGER = ROOT / "util/MmkvManager.kt"
PLAN = ROOT / "util/SubscriptionReplacementPlan.kt"


class SelectedSubscriptionIdentityContractTest(unittest.TestCase):
    def test_selected_replacement_uses_complete_proxy_identity_not_host_port(self):
        source = MANAGER.read_text(encoding="utf-8")
        selected = source.split(
            "val selectedAfter = SubscriptionReplacementPlan.matchSelected(", 1
        )[1].split(") ?: if (selectedGuid", 1)[0]
        self.assertIn("SubscriptionReplacementPlan.matchesOutbound(", selected)
        self.assertEqual(2, selected.count("getProxyOutbound()?.let"))
        self.assertIn("outboundEncoder.toJson(it)", selected)
        self.assertNotIn("getServerAddress()", selected)
        self.assertNotIn("getServerPort()", selected)

    def test_missing_outbound_identity_cannot_match(self):
        plan = PLAN.read_text(encoding="utf-8")
        self.assertIn("fun matchesOutbound(previous: String?, candidate: String?)", plan)
        self.assertIn("!previous.isNullOrBlank() && previous == candidate", plan)


if __name__ == "__main__":
    unittest.main()
