package com.v2ray.ang.util

import org.junit.Assert.assertEquals
import org.junit.Test

class FailedServerSelectionTest {
    @Test fun zeroAndMissingResultsAreNotFailures() {
        val delays = mapOf("untested" to 0L, "failed" to -1L, "healthy" to 45L)
        assertEquals(listOf("failed"), FailedServerSelection.findFailed(
            listOf("untested", "missing", "failed", "healthy"),
            listOf("untested", "missing", "failed", "healthy"),
        ) { delays[it] })
    }

    @Test fun selectionCannotRemoveHiddenOrOtherSubscriptionProfiles() {
        val delays = mapOf("A" to -1L, "B" to -1L, "hidden" to -1L)
        assertEquals(listOf("A"), FailedServerSelection.findFailed(
            listOf("A"), listOf("A", "B", "hidden"),
        ) { delays[it] })
    }

    @Test fun staleAndDuplicateVisibleIdsAreIgnored() {
        assertEquals(listOf("real"), FailedServerSelection.findFailed(
            listOf("removed", "real", "real"), listOf("real"),
        ) { -1L })
    }

    @Test fun emptyScopeNeverDeletesAnything() {
        assertEquals(emptyList<String>(), FailedServerSelection.findFailed(
            emptyList(), listOf("failed"),
        ) { -1L })
    }
}
