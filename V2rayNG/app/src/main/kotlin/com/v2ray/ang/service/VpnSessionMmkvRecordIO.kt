package com.v2ray.ang.service

import com.tencent.mmkv.MMKV

/**
 * Android MMKV adapter for the currently UNWIRED session record transaction.
 * Opening this adapter does not enroll any live VPN service or initialize
 * an absent record. A missing/corrupt record causes every transition to fail.
 *
 * Only the debug-only QA receivers currently use the isolated QA storage ID.
 * Do not pass this QA store to a live VPN or persist user profile information.
 */
internal class VpnSessionMmkvRecordIO(private val mmkv: MMKV) : VpnSessionRecordIO {
    companion object {
        const val DEBUG_QA_ID = "VPN_SESSION_FENCE_DEBUG_QA_V1"
        private const val KEY = "SESSION_RECORD"

        fun openDebugQa(): VpnSessionMmkvRecordIO? {
            val mmkv = MMKV.mmkvWithID(DEBUG_QA_ID, MMKV.MULTI_PROCESS_MODE) ?: return null
            return VpnSessionMmkvRecordIO(mmkv)
        }
    }

    override fun tryLock(): Boolean = mmkv.tryLock()
    override fun read(): String? = mmkv.decodeString(KEY)
    override fun write(value: String): Boolean = mmkv.encode(KEY, value)
    override fun unlock() = mmkv.unlock()
}
