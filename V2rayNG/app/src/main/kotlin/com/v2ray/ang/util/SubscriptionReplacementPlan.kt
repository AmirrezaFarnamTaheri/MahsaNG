package com.v2ray.ang.util

/** Pure, storage-independent rules for safe subscription replacement. */
internal object SubscriptionReplacementPlan {
    /** Reject the whole refresh if any nonempty line is unsupported or malformed. */
    fun <T> stage(raw: String?, parse: (String) -> T?): List<T>? {
        val lines = raw?.lines()?.map { it.trim() }?.filter { it.isNotEmpty() }.orEmpty()
        if (lines.isEmpty()) return null
        val staged = ArrayList<T>(lines.size)
        for (line in lines) staged.add(parse(line) ?: return null)
        return staged
    }

    /** One index update, with all profiles in other subscriptions left in original order. */
    fun mergedIndex(existing: List<String>, replaced: Set<String>, staged: List<String>): List<String> {
        require(staged.isNotEmpty() && staged.size == staged.distinct().size)
        require(staged.none { it.isBlank() || it in existing })
        return staged + existing.filterNot { it in replaced }
    }

    /** Keep other subscriptions selected; follow a matching endpoint within the replacement. */
    fun <T> matchSelected(
        selectedGuid: String?,
        removedGuids: Set<String>,
        selectedConfig: T?,
        newConfigs: Map<String, T>,
        sameEndpoint: (T, T) -> Boolean,
    ): String? {
        if (selectedGuid == null || selectedGuid !in removedGuids) return selectedGuid
        if (selectedConfig == null) return null
        return newConfigs.entries.firstOrNull { sameEndpoint(selectedConfig, it.value) }?.key
    }
}
