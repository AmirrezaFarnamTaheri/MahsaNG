package com.v2ray.ang.util

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class SubscriptionReplacementPlanTest {
    @Test fun emptyReplacementCannotRemoveExistingProfiles() {
        assertEquals(null, SubscriptionReplacementPlan.stage<String>("\n \r\n") { it })
    }

    @Test fun oneMalformedProfileRejectsWholeReplacement() {
        val staged = SubscriptionReplacementPlan.stage("vmess://good\ninvalid://bad\nvless://good") {
            if (it.startsWith("invalid:")) null else it
        }
        assertEquals(null, staged)
    }

    @Test fun acceptedReplacementKeepsOriginalOrderAndSkipsBlankLines() {
        val staged = SubscriptionReplacementPlan.stage(" a \n\n b \n") { it }
        assertEquals(listOf("a", "b"), staged)
    }

    @Test fun mergedIndexKeepsUnrelatedProfilesAndReplacesOnlyOneSubscription() {
        val merged = SubscriptionReplacementPlan.mergedIndex(
            existing = listOf("oldA", "other", "oldB", "saved"),
            replaced = setOf("oldA", "oldB"),
            staged = listOf("newA", "newB"),
        )
        assertEquals(listOf("newA", "newB", "other", "saved"), merged)
    }

    @Test fun duplicateOrEmptyNewIdsCannotBePublished() {
        val invalid = runCatching {
            SubscriptionReplacementPlan.mergedIndex(listOf("old"), setOf("old"), listOf("new", "new"))
        }
        assertTrue(invalid.isFailure)
        val empty = runCatching {
            SubscriptionReplacementPlan.mergedIndex(listOf("old"), setOf("old"), emptyList())
        }
        assertTrue(empty.isFailure)
    }

    @Test fun activeSelectionFollowsMatchingEndpoint() {
        val selected = SubscriptionReplacementPlan.matchSelected(
            selectedGuid = "old",
            removedGuids = setOf("old"),
            selectedConfig = "example:443",
            newConfigs = linkedMapOf("new1" to "unrelated:443", "new2" to "example:443"),
            sameEndpoint = { a, b -> a == b },
        )
        assertEquals("new2", selected)
    }

    @Test fun matchingHostAndPortWithDifferentCredentialsMustNotRetargetSelection() {
        val selected = """{"address":"example.org","port":443,"user":"original","tls":"example.org"}"""
        val anotherAccount = """{"address":"example.org","port":443,"user":"other","tls":"example.org"}"""
        val changedTransport = """{"address":"example.org","port":443,"user":"original","tls":"different.example"}"""
        val replacement = selected
        val result = SubscriptionReplacementPlan.matchSelected(
            selectedGuid = "old",
            removedGuids = setOf("old"),
            selectedConfig = selected,
            newConfigs = linkedMapOf(
                "wrong-account" to anotherAccount,
                "wrong-transport" to changedTransport,
                "same-account" to replacement,
            ),
            sameEndpoint = SubscriptionReplacementPlan::matchesOutbound,
        )
        assertEquals("same-account", result)
        assertEquals(null, SubscriptionReplacementPlan.matchSelected(
            "old", setOf("old"), selected, mapOf("wrong-account" to anotherAccount),
            SubscriptionReplacementPlan::matchesOutbound,
        ))
        assertEquals(false, SubscriptionReplacementPlan.matchesOutbound(null, null))
        assertEquals(false, SubscriptionReplacementPlan.matchesOutbound("", ""))
    }

    @Test fun selectedProfileOutsideReplacedSubscriptionStaysSelected() {
        val selected = SubscriptionReplacementPlan.matchSelected(
            selectedGuid = "other",
            removedGuids = setOf("old"),
            selectedConfig = "example:443",
            newConfigs = linkedMapOf("new" to "foo:443"),
            sameEndpoint = { a, b -> a == b },
        )
        assertEquals("other", selected)
    }

    @Test fun unmatchedRemovedSelectionClearsSafely() {
        val selected = SubscriptionReplacementPlan.matchSelected(
            selectedGuid = "old",
            removedGuids = setOf("old"),
            selectedConfig = "example:443",
            newConfigs = linkedMapOf("new" to "foo:443"),
            sameEndpoint = { a, b -> a == b },
        )
        assertEquals(null, selected)
    }
}
