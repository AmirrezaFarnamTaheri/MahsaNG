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
import com.v2ray.ang.service.VpnNativeStopEvidence
import com.v2ray.ang.service.VpnStopCommandCodec
import com.v2ray.ang.service.VpnStopCommandGate
import com.v2ray.ang.service.VpnStartCommandCodec
import com.v2ray.ang.service.VpnStartCommandGate

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
                    "BEGIN", "BEGIN_NEXT" -> {
                        val mode = VpnSessionMode.values().firstOrNull {
                            it.name == intent.getStringExtra("mode")
                        }
                        val result = if (mode == null) VpnSessionRecordResult.Rejected
                            else store.apply { VpnSessionFence.begin(it, id, mode) }
                        Log.i(TAG, "$token $actor $operation ${status(result)}")
                    }
                    "ATTACH" -> {
                        val role = VpnSessionRole.values().firstOrNull {
                            it.name == intent.getStringExtra("role")
                        }
                        val result = if (role == null) VpnSessionRecordResult.Rejected
                            else store.apply { VpnSessionFence.attach(it, id, generation, role) }
                        Log.i(TAG, "$token $actor ATTACH ${status(result)}")
                    }
                    "START_RESERVE" -> {
                        // Debug QA only: reserve the matching role inside the
                        // existing native-lock-backed cross-process store.
                        val command = VpnStartCommandCodec.decode(
                            intent.getStringExtra("wire").orEmpty()
                        )
                        val result = if (command == null) VpnSessionRecordResult.Rejected
                            else store.apply { VpnStartCommandGate.reserve(it, command) }
                        Log.i(TAG, "$token $actor START_RESERVE ${status(result)}")
                    }
                    "START_CHECK" -> {
                        // This read-only transaction is not approval to start
                        // JNI or a tunnel after the lock is released.
                        val command = VpnStartCommandCodec.decode(
                            intent.getStringExtra("wire").orEmpty()
                        )
                        val result = if (command == null) VpnSessionRecordResult.Rejected
                            else store.apply { state ->
                                if (VpnStartCommandGate.stillAttached(state, command)) state else null
                            }
                        Log.i(TAG, "$token $actor START_CHECK ${status(result)}")
                    }
                    "CMD_REQUEST" -> {
                        // This is QA-only simulated controller delivery. In
                        // production, STOPPING must be persisted *before* IPC.
                        val command = VpnStopCommandCodec.decode(intent.getStringExtra("wire").orEmpty())
                        val result = if (command == null) VpnSessionRecordResult.Rejected
                            else store.apply { VpnStopCommandGate.requestStop(it, command) }
                        Log.i(TAG, "$token $actor CMD_REQUEST ${status(result)}")
                    }
                    "CMD_CHECK" -> {
                        // This read-only transaction checks membership and
                        // generation under the native multi-process lease.
                        val command = VpnStopCommandCodec.decode(intent.getStringExtra("wire").orEmpty())
                        val role = VpnSessionRole.values().firstOrNull {
                            it.name == intent.getStringExtra("role")
                        }
                        val result = if (command == null || role == null) VpnSessionRecordResult.Rejected
                            else store.apply {
                                if (VpnStopCommandGate.mayStopNative(it, command, role)) it else null
                            }
                        Log.i(TAG, "$token $actor CMD_CHECK ${status(result)}")
                    }
                    "CMD_ROLE_LEFT" -> {
                        // After the other participant has completed teardown,
                        // this process must still see its own outstanding role.
                        val command = VpnStopCommandCodec.decode(intent.getStringExtra("wire").orEmpty())
                        val role = VpnSessionRole.values().firstOrNull {
                            it.name == intent.getStringExtra("role")
                        }
                        val result = if (command == null || role == null) VpnSessionRecordResult.Rejected
                            else store.apply { state ->
                                if (VpnStopCommandGate.mayStopNative(state, command, role) &&
                                    state.members == setOf(role)
                                ) state else null
                            }
                        Log.i(TAG, "$token $actor CMD_ROLE_LEFT ${status(result)}")
                    }
                    "CMD_SIM_ACK" -> {
                        // A shell-supplied boolean is *not* a native shutdown
                        // receipt. Only exercising the policy's fail-closed
                        // transition in two real Android QA processes.
                        val command = VpnStopCommandCodec.decode(intent.getStringExtra("wire").orEmpty())
                        val role = VpnSessionRole.values().firstOrNull {
                            it.name == intent.getStringExtra("role")
                        }
                        val complete = intent.getBooleanExtra("complete", false)
                        // QA-only simulation. A shell boolean cannot prove
                        // JNI exit, descriptor closure, or a native tunnel ack.
                        // Keep this under the disposable debug-only record.
                        val simulatedEvidence: VpnNativeStopEvidence? = when (role) {
                            VpnSessionRole.XRAY -> command?.let {
                                VpnNativeStopEvidence.Xray(
                                    sessionId = it.sessionId, generation = it.generation,
                                    stopLoopReturned = complete, coreNotRunning = complete,
                                    tun2socksProcessExited = complete,
                                    fragmentorListenersExited = complete,
                                    tunDescriptorClosed = complete,
                                )
                            }
                            VpnSessionRole.PSIPHON -> command?.let {
                                VpnNativeStopEvidence.Psiphon(
                                    sessionId = it.sessionId, generation = it.generation,
                                    routingWorkerExited = complete,
                                    psiphonNativeShutdownAcknowledged = complete,
                                    tunDescriptorClosed = complete,
                                )
                            }
                            null -> null
                        }
                        val result = if (command == null || simulatedEvidence == null) {
                            VpnSessionRecordResult.Rejected
                        } else store.apply {
                            VpnStopCommandGate.acknowledgeStopped(it, command, simulatedEvidence)
                        }
                        Log.i(TAG, "$token $actor CMD_SIM_ACK ${status(result)}")
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
                    "PROBE_CORRUPT" -> {
                        // Distinct event name prevents a preceding native-lock
                        // denial from satisfying the corrupted-record assertion.
                        Log.i(TAG, "$token $actor PROBE_CORRUPT ${status(store.apply { it })}")
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
