package com.v2ray.ang.qa

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log
import com.tencent.mmkv.MMKV
import com.v2ray.ang.BuildConfig
import com.v2ray.ang.util.MmkvManager

/**
 * Debug-only, DUMP-permission-restricted native MMKV inter-process lock probe.
 *
 * The two manifest receivers run in DIFFERENT Android processes. Unlike a
 * mock-based JUnit test, each creates a real MULTI_PROCESS_MODE MMKV handle.
 * No profile values, subscription details, credentials or app settings are read.
 */
abstract class IndexLeaseProbeReceiver(private val role: String) : BroadcastReceiver() {
    companion object {
        private const val TAG = "MahsaIndexLeaseQA"
        private const val MAX_HOLD_MS = 6500L
        private val TOKEN = Regex("[A-Za-z0-9_-]{8,64}")
    }

    override fun onReceive(context: Context, intent: Intent) {
        if (!BuildConfig.DEBUG) return
        val token = intent.getStringExtra("token")?.takeIf(TOKEN::matches) ?: return
        val prime = intent.getBooleanExtra("prime", false)
        val holdMs = if (role == "OWNER" && !prime)
            intent.getIntExtra("hold_ms", 0).toLong().coerceIn(0, MAX_HOLD_MS)
        else 0L
        val pending = goAsync()
        Thread({
            try {
                // The process Application initializes MMKV before onReceive.
                val main = MMKV.mmkvWithID(MmkvManager.ID_MAIN, MMKV.MULTI_PROCESS_MODE)
                if (main == null) {
                    Log.e(TAG, "$token $role INIT_FAILED")
                } else if (prime) {
                    Log.i(TAG, "$token $role READY")
                } else {
                    val acquired = main.tryLock()
                    if (!acquired) {
                        Log.i(TAG, "$token $role DENIED")
                    } else {
                        try {
                            Log.i(TAG, "$token $role " +
                                if (role == "OWNER") "LOCKED" else "GRANTED")
                            if (holdMs > 0) Thread.sleep(holdMs)
                        } finally {
                            main.unlock()
                            if (role == "OWNER") Log.i(TAG, "$token $role RELEASED")
                        }
                    }
                }
            } catch (error: Exception) {
                // An exception type is enough for QA; never print storage contents.
                Log.e(TAG, "$token $role ERROR " + error.javaClass.simpleName)
            } finally {
                pending.finish()
            }
        }, "mahsa-qa-lock-$role").start()
    }
}

class IndexLeaseOwnerReceiver : IndexLeaseProbeReceiver("OWNER")
class IndexLeaseContenderReceiver : IndexLeaseProbeReceiver("CONTENDER")
