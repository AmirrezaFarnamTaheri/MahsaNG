package com.v2ray.ang.qa

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log
import com.v2ray.ang.BuildConfig
import com.v2ray.ang.service.VpnSessionFence
import com.v2ray.ang.service.VpnSessionMmkvRecordIO
import com.v2ray.ang.service.VpnSessionMode
import com.v2ray.ang.service.VpnSessionPhase
import com.v2ray.ang.service.VpnSessionRecordCodec
import com.v2ray.ang.service.VpnSessionRecordResult
import com.v2ray.ang.service.VpnSessionRecordStore
import com.v2ray.ang.service.VpnSessionRole

/**
 * Debug-only DUMP-restricted Android cross-process state-transition probe.
 * Uses a disposable, isolated MMKV namespace, NEVER actual user VPN sessions.
 * Emitted events contain only a generated test correlation token and status.
 */
abstract class VpnSessionFenceQaReceiver(private val actor: String) : BroadcastReceiver() {
    companion object {
        private const val TAG = "MahsaSessionFenceQA"
        private val CORRELATION = Regex("[A-Za-z0-9_-]{8,64}")
    }

    override fun onReceive(context: Context, intent: Intent) {
        if (!BuildConfig.DEBUG) return
        val token = intent.getStringExtra("token")?.takeIf(CORRELATION::matches) ?: return
        val operation = intent.getStringExtra("op") ?: return
        val id = intent.getStringExtra("id").orEmpty()
        val generation = intent.getLongExtra("gen", -1L)
        val pending = goAsync()
        Thread({
            try {
                val io = VpnSessionMmkvRecordIO.openDebugQa()
                if (io == null) {
                    Log.e(TAG, "$token $actor $operation UNAVAILABLE")
                    return@Thread
                }
                val store = VpnSessionRecordStore(io)
                fun status(result: VpnSessionRecordResult): String = when (result) {
                    is VpnSessionRecordResult.Applied -> "ACCEPTED"
                    VpnSessionRecordResult.Rejected -> "REJECTED"
                    VpnSessionRecordResult.Unavailable -> "UNAVAILABLE"
                }
                // Controlled by Android shell only; no untrusted or exported
                // production command can access these debug-only receivers.
                when (operation) {
                    "SEED" -> {
                        if (actor != "OWNER") return@Thread
                        // Deliberate QA-only reset. Never use for real VPN state.
                        if (!io.tryLock()) {
                            Log.i(TAG, "$token $actor SEED UNAVAILABLE")
                        } else {
                            try {
                                val record = VpnSessionRecordCodec.encode(VpnSessionFence.empty())
                                val ok = record != null && io.write(record)
                                Log.i(TAG, "$token $actor SEED " + (if (ok) "ACCEPTED" else "UNAVAILABLE"))
                            } finally {
                                io.unlock()
                            }
                        }
                    }
                    "BEGIN" -> {
                        val mode = VpnSessionMode.values().firstOrNull {
                            it.name == intent.getStringExtra("mode")
                        }
                        val result = if (mode == null) VpnSessionRecordResult.Rejected
                            else store.apply { VpnSessionFence.begin(it, id, mode) }
                        Log.i(TAG, "$token $actor BEGIN ${status(result)}")
                    }
                    "ATTACH" -> {
                        val role = VpnSessionRole.values().firstOrNull {
                            it.name == intent.getStringExtra("role")
                        }
                        val result = if (role == null) VpnSessionRecordResult.Rejected
                            else store.apply { VpnSessionFence.attach(it, id, generation, role) }
                        Log.i(TAG, "$token $actor ATTACH ${status(result)}")
                    }
                    "STOP" -> {
                        val result = store.apply { VpnSessionFence.stop(it, id, generation) }
                        Log.i(TAG, "$token $actor STOP ${status(result)}")
                    }
                    "RELEASE" -> {
                        val role = VpnSessionRole.values().firstOrNull {
                            it.name == intent.getStringExtra("role")
                        }
                        val result = if (role == null) VpnSessionRecordResult.Rejected
                            else store.apply { VpnSessionFence.release(it, id, generation, role) }
                        Log.i(TAG, "$token $actor RELEASE ${status(result)}")
                    }
                    "CHECK" -> {
                        val phase = intent.getStringExtra("phase")
                        val result = store.apply { it }
                        val matches = result is VpnSessionRecordResult.Applied &&
                            result.state.generation == generation && result.state.phase.name == phase
                        Log.i(TAG, "$token $actor CHECK $phase " + (if (matches) "PASS" else "FAIL"))
                    }
                    "PROBE" -> {
                        Log.i(TAG, "$token $actor PROBE ${status(store.apply { it })}")
                    }
                    "HOLD" -> {
                        if (actor != "OWNER") return@Thread
                        if (!io.tryLock()) {
                            Log.i(TAG, "$token $actor HOLD UNAVAILABLE")
                        } else {
                            try {
                                Log.i(TAG, "$token $actor HOLD LOCKED")
                                Thread.sleep(4500L)
                            } finally {
                                io.unlock()
                                Log.i(TAG, "$token $actor HOLD RELEASED")
                            }
                        }
                    }
                    "CORRUPT" -> {
                        if (actor != "OWNER") return@Thread
                        if (!io.tryLock()) {
                            Log.i(TAG, "$token $actor CORRUPT UNAVAILABLE")
                        } else {
                            try {
                                val ok = io.write("not-a-valid-session-record")
                                Log.i(TAG, "$token $actor CORRUPT " + (if (ok) "ACCEPTED" else "UNAVAILABLE"))
                            } finally {
                                io.unlock()
                            }
                        }
                    }
                    else -> Log.w(TAG, "$token $actor UNKNOWN")
                }
            } catch (error: Exception) {
                Log.e(TAG, "$token $actor $operation ERROR " + error.javaClass.simpleName)
            } finally {
                pending.finish()
            }
        }, "mahsa-session-qa-$actor").start()
    }
}

class VpnSessionQaOwnerReceiver : VpnSessionFenceQaReceiver("OWNER")
class VpnSessionQaContenderReceiver : VpnSessionFenceQaReceiver("CONTENDER")
