package com.v2ray.ang.util

import java.util.Collections
import java.util.UUID
import java.util.WeakHashMap

/** In-memory ownership gate for UI and native test results; never persisted to MMKV. */
internal class TestRunTracker {
    private data class ActiveRun(val id: String, val guids: Set<String>)

    @Volatile
    private var active: ActiveRun? = null

    init { synchronized(trackers) { trackers.add(this) } }

    @Synchronized
    fun begin(visibleGuids: Collection<String>): String {
        val run = ActiveRun(UUID.randomUUID().toString(), visibleGuids.toSet())
        active = run
        return run.id
    }

    fun accepts(runId: String, guid: String): Boolean {
        val run = active ?: return false
        return run.id == runId && guid in run.guids
    }

    @Synchronized
    fun forgetGuid(guid: String) {
        if (guid.isBlank()) return
        val run = active ?: return
        active = run.copy(guids = run.guids - guid)
    }

    @Synchronized
    fun invalidate() {
        active = null
    }

    companion object {
        // Avoid holding an Activity or ViewModel strongly after its lifecycle ends.
        private val trackers: MutableSet<TestRunTracker> =
            Collections.newSetFromMap(WeakHashMap<TestRunTracker, Boolean>())

        /** Remove a changed profile synchronously from every live in-process run. */
        fun forgetProfile(guid: String) {
            if (guid.isBlank()) return
            synchronized(trackers) { trackers.toList().forEach { it.forgetGuid(guid) } }
        }
    }
}
