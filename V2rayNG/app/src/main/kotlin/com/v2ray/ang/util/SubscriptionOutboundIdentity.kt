package com.v2ray.ang.util

import com.google.gson.Gson
import com.v2ray.ang.dto.ServerConfig
import com.v2ray.ang.dto.V2rayConfig

/**
 * Full connection identity for safe selection after a subscription refresh.
 *
 * A selected outbound can delegate to additional outbounds via proxySettings.tag
 * or streamSettings.sockopt.dialerProxy. Comparing only the selected outbound
 * would ignore the delegated credentials. Resolve every referenced outbound
 * transitively and reject dangling, ambiguous, malformed or cyclic references.
 *
 * Without chain references, preserve the existing serialized outbound identity.
 * Nothing here modifies a profile or persists credential information.
 */
internal object SubscriptionOutboundIdentity {
    fun serialize(profile: ServerConfig, gson: Gson): String? = runCatching {
        val primary = profile.getProxyOutbound() ?: return@runCatching null
        val directIdentity = gson.toJson(primary)
        val directReferences = references(primary, gson) ?: return@runCatching null
        if (directReferences.isEmpty()) return@runCatching directIdentity

        // A chained outbound without its full graph cannot be safely compared.
        val candidates = profile.fullConfig?.outbounds ?: return@runCatching null
        val byTag = candidates.groupBy { it.tag }
        val resolved = mutableMapOf<String, V2rayConfig.OutboundBean>()
        val visiting = mutableSetOf(primary.tag)

        fun visit(tag: String): Boolean {
            if (tag in visiting) return false // a cycle through the selected outbound or chain
            if (tag in resolved) return true
            // Duplicate tags are ambiguous: never guess which account will be used.
            val next = byTag[tag]?.singleOrNull() ?: return false
            visiting.add(tag)
            val refs = references(next, gson) ?: return false
            if (!refs.all(::visit)) return false
            visiting.remove(tag)
            resolved[tag] = next
            return true
        }

        if (!directReferences.all(::visit)) return@runCatching null
        // Sorting by tag makes identity independent of unrelated outbound order.
        gson.toJson(linkedMapOf<String, Any>(
            "primary" to primary,
            "referencedOutbounds" to resolved.toSortedMap(),
        ))
    }.getOrNull()

    private fun references(outbound: V2rayConfig.OutboundBean, gson: Gson): List<String>? {
        val result = mutableListOf<String>()
        outbound.proxySettings?.let { settings ->
            val json = gson.toJsonTree(settings)
            if (!json.isJsonObject) return null
            val value = json.asJsonObject.get("tag")
            if (value == null || !value.isJsonPrimitive ||
                !value.asJsonPrimitive.isString || value.asString.isBlank()
            ) return null
            result.add(value.asString)
        }
        outbound.streamSettings?.sockopt?.dialerProxy?.let { tag ->
            if (tag.isBlank()) return null
            result.add(tag)
        }
        return result.distinct()
    }
}
