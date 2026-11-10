package com.v2ray.ang.util

/** Select only measured failures from the current, explicitly visible profile scope. */
internal object FailedServerSelection {
    fun findFailed(
        visibleGuids: Collection<String>,
        storedGuids: Collection<String>,
        delayByGuid: (String) -> Long?,
    ): List<String> {
        val stored = storedGuids.toHashSet()
        return visibleGuids.distinct().filter { guid ->
            guid in stored && (delayByGuid(guid) ?: 0L) < 0L
        }
    }
}
