package com.v2ray.ang.util

import java.util.UUID

/** In-memory ownership gate for UI and native test results; never persisted to MMKV. */
internal class TestRunTracker {
    private data class ActiveRun(val id: String, val guids: Set<String>)

    @Volatile
    private var active: ActiveRun? = null

    fun begin(visibleGuids: Collection<String>): String {
        val run = ActiveRun(UUID.randomUUID().toString(), visibleGuids.toSet())
        active = run
        return run.id
    }

    fun accepts(runId: String, guid: String): Boolean {
        val run = active ?: return false
        return run.id == runId && guid in run.guids
    }

    fun invalidate() {
        active = null
    }
}
