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

    fun removeServerViaSubid(subid: String) {
        if (subid.isBlank()) {
            return
        }
        serverStorage?.allKeys()?.forEach { key ->
            decodeServerConfig(key)?.let { config ->
                if (config.subscriptionId == subid) {
                    removeServer(key)
                }
            }
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

    fun removeSubscription(subid: String) {
        subStorage?.remove(subid)
        removeServerViaSubid(subid)
    }

    fun removeAllServer() {
        mainStorage?.clearAll()
        serverStorage?.clearAll()
        serverAffStorage?.clearAll()
    }

    /**
     * Returns only measured failures in the caller's visible/selected scope.
     * Missing records and zero (untested/pending) never qualify.
     */
    @Synchronized
    fun findFailedServerGuids(visibleGuids: Collection<String>): List<String> =
        FailedServerSelection.findFailed(visibleGuids, decodeServerList()) { guid ->
            runCatching { decodeServerAffiliationInfo(guid)?.testDelayMillis }.getOrNull()
        }

    /**
     * Rechecks the confirmed candidate list at commit time, removing only profiles
     * that still exist and still have an explicit negative test result.
     * The serialized index is written once instead of once per deleted profile.
     */
    @Synchronized
    fun removeInvalidServer(confirmedCandidates: Collection<String>): Int {
        if (confirmedCandidates.isEmpty()) return 0
        val main = mainStorage ?: return 0
        val currentGuids = decodeServerList()
        val failedGuids = FailedServerSelection.findFailed(confirmedCandidates, currentGuids) { guid ->
            runCatching { decodeServerAffiliationInfo(guid)?.testDelayMillis }.getOrNull()
        }
        if (failedGuids.isEmpty()) return 0

        val failedSet = failedGuids.toHashSet()
        val survivingGuids = currentGuids.filterNot { it in failedSet }
        if (!main.encode(KEY_ANG_CONFIGS, Gson().toJson(survivingGuids))) return 0

        if (main.decodeString(KEY_SELECTED_SERVER) in failedSet) {
            main.remove(KEY_SELECTED_SERVER)
        }
        failedGuids.forEach { guid ->
            serverStorage?.remove(guid)
            serverAffStorage?.remove(guid)
        }
        return failedGuids.size
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
