package com.v2ray.ang.util

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Assert.assertEquals
import org.junit.Test

class TestRunTrackerTest {
    @Test fun startingNewRunRejectsLatePreviousCallbacks() {
        val tracker = TestRunTracker()
        val first = tracker.begin(listOf("a"))
        val second = tracker.begin(listOf("a"))
        assertFalse(tracker.accepts(first, "a"))
        assertTrue(tracker.accepts(second, "a"))
    }

    @Test fun aRunRejectsCallbacksForProfilesOutsideItsScope() {
        val tracker = TestRunTracker()
        val runId = tracker.begin(listOf("visible"))
        assertTrue(tracker.accepts(runId, "visible"))
        assertFalse(tracker.accepts(runId, "hidden"))
    }

    @Test fun snapshotRemainsStableWhenVisibleListChanges() {
        val tracker = TestRunTracker()
        val visible = mutableListOf("original", "removed")
        val id = tracker.begin(visible)
        visible.clear()
        visible.add("new")
        assertTrue(tracker.accepts(id, "original"))
        assertFalse(tracker.accepts(id, "new"))
    }

    @Test fun cancellationRejectsAllRemainingResults() {
        val tracker = TestRunTracker()
        val id = tracker.begin(listOf("a"))
        tracker.invalidate()
        assertFalse(tracker.accepts(id, "a"))
    }
}
