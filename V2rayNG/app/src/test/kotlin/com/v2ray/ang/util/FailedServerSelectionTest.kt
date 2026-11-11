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

    @Test fun changedProfileRevisionCannotBeDeletedAfterConfirmation() {
        val revisions = mutableMapOf("a" to "original-config", "b" to "original-other")
        val delays = mapOf("a" to -1L, "b" to -1L)
        val preview = FailedServerSelection.snapshotFailures(
            listOf("a"), listOf("a", "b"), { delays[it] }, { revisions[it] },
        )
        assertEquals(listOf("a"), preview.map { it.guid })
        revisions["a"] = "replaced-profile-with-same-guid"
        assertEquals(emptyList<String>(), FailedServerSelection.reconfirmFailures(
            preview, listOf("a", "b"), { delays[it] }, { revisions[it] },
        ))
    }

    @Test fun aNewMeasurementCannotReuseOldFailureEvidence() {
        val delays = mutableMapOf("failed" to -1L, "pending" to 0L, "success" to 40L)
        val revisions = mapOf("failed" to "r1", "pending" to "r2", "success" to "r3")
        val preview = FailedServerSelection.snapshotFailures(
            listOf("failed", "pending", "success"),
            listOf("failed", "pending", "success"), { delays[it] }, { revisions[it] },
        )
        assertEquals(listOf("failed"), preview.map { it.guid })
        delays["failed"] = 0L
        assertEquals(emptyList<String>(), FailedServerSelection.reconfirmFailures(
            preview, listOf("failed", "pending", "success"),
            { delays[it] }, { revisions[it] },
        ))
    }

    @Test fun deletionNeverExpandsBeyondFrozenVisibleAndStoredScope() {
        val revisions = mapOf("a" to "r1", "hidden" to "r2")
        val preview = FailedServerSelection.snapshotFailures(
            listOf("a", "a"), listOf("a", "hidden"),
            { -1L }, { revisions[it] },
        )
        assertEquals(listOf("a"), preview.map { it.guid })
        assertEquals(listOf("a"), FailedServerSelection.reconfirmFailures(
            preview, listOf("a", "hidden"), { -1L }, { revisions[it] },
        ))
        assertEquals(emptyList<String>(), FailedServerSelection.reconfirmFailures(
            preview, listOf("hidden"), { -1L }, { revisions[it] },
        ))
    }

    @Test fun explicitNegativeFailuresRequireReadableProfileRevision() {
        val preview = FailedServerSelection.snapshotFailures(
            listOf("missing", "blank", "valid"), listOf("missing", "blank", "valid"),
            { -1L }, { if (it == "missing") null else if (it == "blank") "" else "r3" },
        )
        assertEquals(listOf("valid"), preview.map { it.guid })
    }
}
