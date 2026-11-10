package com.v2ray.ang.util

import com.google.gson.Gson
import com.tencent.mmkv.MMKV
import com.v2ray.ang.dto.ServerAffiliationInfo
import com.v2ray.ang.dto.ServerConfig
import com.v2ray.ang.dto.SubscriptionItem

object MmkvManager {
    const val ID_MAIN = "MAIN"
    const val ID_SERVER_CONFIG = "SERVER_CONFIG"
    const val ID_SERVER_RAW = "SERVER_RAW"
    const val ID_SERVER_AFF = "SERVER_AFF"
    const val ID_SUB = "SUB"
    const val ID_SETTING = "SETTING"
    const val KEY_SELECTED_SERVER = "SELECTED_SERVER"
    const val KEY_ANG_CONFIGS = "ANG_CONFIGS"

    private val mainStorage by lazy { MMKV.mmkvWithID(ID_MAIN, MMKV.MULTI_PROCESS_MODE) }
    private val serverStorage by lazy { MMKV.mmkvWithID(ID_SERVER_CONFIG, MMKV.MULTI_PROCESS_MODE) }
    private val serverAffStorage by lazy { MMKV.mmkvWithID(ID_SERVER_AFF, MMKV.MULTI_PROCESS_MODE) }
    private val subStorage by lazy { MMKV.mmkvWithID(ID_SUB, MMKV.MULTI_PROCESS_MODE) }

    fun decodeServerList(): MutableList<String> {
        val json = mainStorage?.decodeString(KEY_ANG_CONFIGS)
        return if (json.isNullOrBlank()) {
            mutableListOf()
        } else {
            Gson().fromJson(json, Array<String>::class.java).toMutableList()
        }
    }

    fun decodeServerConfig(guid: String): ServerConfig? {
        if (guid.isBlank()) {
            return null
        }
        val json = serverStorage?.decodeString(guid)
        if (json.isNullOrBlank()) {
            return null
        }
        return Gson().fromJson(json, ServerConfig::class.java)
    }

    @Synchronized
    fun encodeServerConfig(guid: String, config: ServerConfig): String {
        val key = guid.ifBlank { Utils.getUuid() }
        serverStorage?.encode(key, Gson().toJson(config))
        val serverList = decodeServerList()
        if (!serverList.contains(key)) {
            serverList.add(0, key)
            mainStorage?.encode(KEY_ANG_CONFIGS, Gson().toJson(serverList))
            if (mainStorage?.decodeString(KEY_SELECTED_SERVER).isNullOrBlank()) {
                mainStorage?.encode(KEY_SELECTED_SERVER, key)
            }
        }
        return key
    }

    @Synchronized
    fun removeServer(guid: String) {
        if (guid.isBlank()) {
            return
        }
        if (mainStorage?.decodeString(KEY_SELECTED_SERVER) == guid) {
            mainStorage?.remove(KEY_SELECTED_SERVER)
        }
        val serverList = decodeServerList()
        serverList.remove(guid)
        mainStorage?.encode(KEY_ANG_CONFIGS, Gson().toJson(serverList))
        serverStorage?.remove(guid)
        serverAffStorage?.remove(guid)
    }

    /**
     * Stage new payloads first, atomically publish the serialized GUID index, and
     * only then retire the old subscription payloads. This is an in-process
     * critical section, not a claim of cross-process MMKV transactions.
     */
    @Synchronized
    fun replaceSubscriptionServers(
        subid: String,
        stagedProfiles: Map<String, ServerConfig>,
    ): Boolean {
        if (subid.isBlank() || stagedProfiles.isEmpty()) return false
        val main = mainStorage ?: return false
        val payloads = serverStorage ?: return false
        // An update downloaded before subscription deletion must not resurrect it.
        if (subStorage?.decodeString(subid).isNullOrBlank()) return false

        return try {
            val oldIndex = decodeServerList()
            val oldGuids = oldIndex.filter { guid ->
                decodeServerConfig(guid)?.subscriptionId == subid
            }.toSet()
            val newIndex = SubscriptionReplacementPlan.mergedIndex(
                oldIndex, oldGuids, stagedProfiles.keys.toList()
            )

            if (stagedProfiles.values.any { config ->
                    val outbound = config.getProxyOutbound()
                    val address = outbound?.getServerAddress()
                    val port = outbound?.getServerPort()
                    config.subscriptionId != subid ||
                        address.isNullOrBlank() || port == null || port !in 1..65535
                }) return false

            val selectedGuid = main.decodeString(KEY_SELECTED_SERVER)?.takeIf { it.isNotBlank() }
            val selectedConfig = selectedGuid?.let { decodeServerConfig(it) }
            val selectedAfter = SubscriptionReplacementPlan.matchSelected(
                selectedGuid, oldGuids, selectedConfig, stagedProfiles
            ) { before, after ->
                before.getProxyOutbound()?.getServerAddress() ==
                    after.getProxyOutbound()?.getServerAddress() &&
                    before.getProxyOutbound()?.getServerPort() ==
                    after.getProxyOutbound()?.getServerPort()
            } ?: if (selectedGuid == null) stagedProfiles.keys.firstOrNull() else null

            val written = mutableListOf<String>()
            try {
                for ((guid, config) in stagedProfiles) {
                    // Record the key before writing: an exception after a partial
                    // write must not leave it looking like a committed profile.
                    written.add(guid)
                    if (!payloads.encode(guid, Gson().toJson(config))) {
                        error("Failed to stage subscription profile")
                    }
                }
                if (!main.encode(KEY_ANG_CONFIGS, Gson().toJson(newIndex))) {
                    error("Failed to publish subscription index")
                }
            } catch (_: Exception) {
                written.forEach { guid -> runCatching { payloads.remove(guid) } }
                return false
            }

            // A published replacement must never retain an old selected GUID.
            if (selectedAfter != selectedGuid) {
                runCatching {
                    if (selectedAfter == null || !main.encode(KEY_SELECTED_SERVER, selectedAfter)) {
                        main.remove(KEY_SELECTED_SERVER)
                    }
                }
            }
            // Leaving old, unindexed payloads after interruption is recoverable;
            // removing the old index before publication would lose user profiles.
            oldGuids.forEach { guid ->
                runCatching { payloads.remove(guid) }
                runCatching { serverAffStorage?.remove(guid) }
            }
            true
        } catch (_: Exception) {
            false
        }
    }

    /** Remove one subscription with a single index update under the writer gate. */
    @Synchronized
    fun removeServerViaSubid(subid: String) {
        if (subid.isBlank()) return
        val indexed = decodeServerList()
        val removed = serverStorage?.allKeys()?.mapNotNull { guid ->
            val config = runCatching { decodeServerConfig(guid) }.getOrNull()
            guid.takeIf { config?.subscriptionId == subid }
        }?.toSet().orEmpty()
        if (removed.isEmpty()) return
        val survivors = indexed.filterNot { it in removed }
        if (mainStorage?.encode(KEY_ANG_CONFIGS, Gson().toJson(survivors)) != true) return
        if (mainStorage?.decodeString(KEY_SELECTED_SERVER) in removed) {
            mainStorage?.remove(KEY_SELECTED_SERVER)
        }
        removed.forEach { guid ->
            serverStorage?.remove(guid)
            serverAffStorage?.remove(guid)
        }
    }

    fun decodeServerAffiliationInfo(guid: String): ServerAffiliationInfo? {
        if (guid.isBlank()) {
            return null
        }
        val json = serverAffStorage?.decodeString(guid)
        if (json.isNullOrBlank()) {
            return null
        }
        return Gson().fromJson(json, ServerAffiliationInfo::class.java)
    }

    fun encodeServerTestDelayMillis(guid: String, testResult: Long) {
        if (guid.isBlank()) {
            return
        }
        val aff = decodeServerAffiliationInfo(guid) ?: ServerAffiliationInfo()
        aff.testDelayMillis = testResult
        serverAffStorage?.encode(guid, Gson().toJson(aff))
    }

    fun clearAllTestDelayResults() {
        serverAffStorage?.allKeys()?.forEach { key ->
            decodeServerAffiliationInfo(key)?.let { aff ->
                aff.testDelayMillis = 0
                serverAffStorage?.encode(key, Gson().toJson(aff))
            }
        }
    }

    fun importUrlAsSubscription(url: String): Int {
        val subscriptions = decodeSubscriptions()
        subscriptions.forEach {
            if (it.second.url == url) {
                return 0
            }
        }
        val subItem = SubscriptionItem()
        subItem.remarks = "import sub"
        subItem.url = url
        subStorage?.encode(Utils.getUuid(), Gson().toJson(subItem))
        return 1
    }

    fun decodeSubscriptions(): List<Pair<String, SubscriptionItem>> {
        val subscriptions = mutableListOf<Pair<String, SubscriptionItem>>()
        subStorage?.allKeys()?.forEach { key ->
            val json = subStorage?.decodeString(key)
            if (!json.isNullOrBlank()) {
                subscriptions.add(Pair(key, Gson().fromJson(json, SubscriptionItem::class.java)))
            }
        }
        subscriptions.sortedBy { (_, value) -> value.addedTime }
        return subscriptions
    }

    @Synchronized
    fun removeSubscription(subid: String) {
        subStorage?.remove(subid)
        removeServerViaSubid(subid)
    }

    @Synchronized
    fun removeAllServer() {
        mainStorage?.clearAll()
        serverStorage?.clearAll()
        serverAffStorage?.clearAll()
    }

    fun removeInvalidServer() {
        serverAffStorage?.allKeys()?.forEach { key ->
            decodeServerAffiliationInfo(key)?.let { aff ->
                if (aff.testDelayMillis <= 0L) {
                    removeServer(key)
                }
            }
        }
    }

    fun sortByTestResults( ) {
        data class ServerDelay(var guid: String, var testDelayMillis: Long)

        val serverDelays = mutableListOf<ServerDelay>()
        val serverList = decodeServerList()
        serverList.forEach { key ->
            val delay = decodeServerAffiliationInfo(key)?.testDelayMillis ?: 0L
            serverDelays.add(ServerDelay(key, if (delay <= 0L) 999999 else delay))
        }
        serverDelays.sortBy { it.testDelayMillis }

        serverDelays.forEach {
            serverList.remove(it.guid)
            serverList.add(it.guid)
        }

        mainStorage?.encode(KEY_ANG_CONFIGS, Gson().toJson(serverList))
    }
}
