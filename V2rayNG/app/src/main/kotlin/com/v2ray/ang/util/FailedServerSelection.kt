package com.v2ray.ang.util

/**
 * An exact, in-memory confirmation of a negative measurement and its original
 * serialized profile. It is never logged or persisted as a second credential copy.
 */
internal data class FailedServerEvidence(
    val guid: String,
    val profileRevision: String,
    val observedDelay: Long,
)

/** Select only measured failures from the current, explicitly visible scope. */
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

    /**
     * Bind a destructive confirmation to the exact profile payload and observed
     * failure. The preview cannot accidentally authorise future profile revisions
     * that reuse a GUID or statuses from a new/cancelled test.
     */
    fun snapshotFailures(
        visibleGuids: Collection<String>,
        storedGuids: Collection<String>,
        delayByGuid: (String) -> Long?,
        profileRevisionByGuid: (String) -> String?,
    ): List<FailedServerEvidence> {
        val indexed = storedGuids.toHashSet()
        return visibleGuids.distinct().mapNotNull { guid ->
            if (guid !in indexed) return@mapNotNull null
            val delay = delayByGuid(guid) ?: return@mapNotNull null
            if (delay >= 0L) return@mapNotNull null
            val revision = profileRevisionByGuid(guid)?.takeIf { it.isNotBlank() }
                ?: return@mapNotNull null
            FailedServerEvidence(guid, revision, delay)
        }
    }

    /**
     * Recheck all destructive evidence under the storage writer lock. Changed,
     * removed, newly untested and newly successful profiles are never included.
     * No new GUID can be added after the confirmation was displayed.
     */
    fun reconfirmFailures(
        confirmed: Collection<FailedServerEvidence>,
        storedGuids: Collection<String>,
        delayByGuid: (String) -> Long?,
        profileRevisionByGuid: (String) -> String?,
    ): List<String> {
        val indexed = storedGuids.toHashSet()
        return confirmed.distinctBy { it.guid }.filter { snapshot ->
            snapshot.guid in indexed &&
                snapshot.observedDelay < 0L &&
                delayByGuid(snapshot.guid) == snapshot.observedDelay &&
                profileRevisionByGuid(snapshot.guid) == snapshot.profileRevision
        }.map { it.guid }
    }
}
