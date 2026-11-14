"""Guard against re-selecting a different account at the same endpoint after refresh."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / "app/src/main/kotlin/com/v2ray/ang"
MANAGER = ROOT / "util/MmkvManager.kt"
PLAN = ROOT / "util/SubscriptionReplacementPlan.kt"
IDENTITY = ROOT / "util/SubscriptionOutboundIdentity.kt"


class SelectedSubscriptionIdentityContractTest(unittest.TestCase):
    def test_selected_replacement_uses_complete_proxy_identity_not_host_port(self):
        source = MANAGER.read_text(encoding="utf-8")
        selected = source.split(
            "val selectedAfter = SubscriptionReplacementPlan.matchSelected(", 1
        )[1]
        selected, closing, _ = selected.partition("} ?: if (selectedGuid")
        self.assertTrue(closing, "Selected-profile matching boundary not found")
        self.assertIn("SubscriptionReplacementPlan.matchesOutbound(", selected)
        self.assertIn("SubscriptionOutboundIdentity.serialize(before, outboundEncoder)", selected)
        self.assertIn("SubscriptionOutboundIdentity.serialize(after, outboundEncoder)", selected)
        self.assertNotIn("getServerAddress()", selected)
        self.assertNotIn("getServerPort()", selected)

    def test_chain_dependency_is_resolved_transitively_and_fails_closed(self):
        helper = IDENTITY.read_text(encoding="utf-8")
        self.assertIn("profile.getProxyOutbound()", helper)
        self.assertIn("val fallback = profile.fullConfig?.outbounds?.firstOrNull()", helper)
        self.assertIn("if (fallback !== primary) return@runCatching null", helper)
        self.assertIn("proxySettings", helper)
        self.assertIn('get("tag")', helper)
        self.assertIn("sockopt?.dialerProxy", helper)
        self.assertIn("byTag[tag]?.singleOrNull()", helper)
        self.assertIn("refs.all(::visit)", helper)
        self.assertIn("resolved.toSortedMap()", helper)
        self.assertIn("routing.rules", helper)
        self.assertIn("routedTags", helper)
        self.assertIn("byTag[it]?.size != 1", helper)
        self.assertIn('identity["routing"] = routing', helper)
        self.assertIn("return@runCatching null", helper)

    def test_missing_outbound_identity_cannot_match(self):
        plan = PLAN.read_text(encoding="utf-8")
        self.assertIn("fun matchesOutbound(previous: String?, candidate: String?)", plan)
        self.assertIn("!previous.isNullOrBlank() && previous == candidate", plan)


if __name__ == "__main__":
    unittest.main()
