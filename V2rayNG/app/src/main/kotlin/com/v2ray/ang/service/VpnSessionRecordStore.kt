package com.v2ray.ang.service

/**
 * Strict, canonical, bounded wire record for the *unwired* VPN session policy.
 * Missing data, unknown versions, malformed states and non-canonical records
 * must never be interpreted as permission to start a new VPN session.
 */
internal object VpnSessionRecordCodec {
    private const val VERSION = "v1"
    private const val EMPTY = "_"

    fun encode(state: VpnSessionSnapshot): String? {
        if (!VpnSessionFence.isValidSnapshot(state)) return null
        val members = if (state.members.isEmpty()) EMPTY
                      else state.members.sortedBy { it.ordinal }.joinToString(",") { it.name }
        return listOf(
            VERSION, state.generation.toString(),
            state.sessionId ?: EMPTY, state.mode?.name ?: EMPTY,
            state.phase.name, members,
        ).joinToString("|")
    }

    fun decode(raw: String): VpnSessionSnapshot? {
        if (raw.length !in 1..256) return null
        val fields = raw.split('|')
        if (fields.size != 6 || fields[0] != VERSION) return null
        val generation = fields[1].toLongOrNull() ?: return null
        val sessionId = fields[2].takeUnless { it == EMPTY }
        val mode = when (fields[3]) {
            EMPTY -> null
            else -> VpnSessionMode.values().firstOrNull { it.name == fields[3] } ?: return null
        }
        val phase = VpnSessionPhase.values().firstOrNull { it.name == fields[4] } ?: return null
        val members = if (fields[5] == EMPTY) emptySet() else {
            val names = fields[5].split(',')
            val roles = names.map { name ->
                VpnSessionRole.values().firstOrNull { it.name == name } ?: return null
            }
            if (roles.distinct().size != roles.size) return null
            roles.toSet()
        }
        val snapshot = VpnSessionSnapshot(generation, sessionId, mode, phase, members)
        // Roundtrip equality also rejects duplicate, reordered or padded fields.
        return snapshot.takeIf { encode(it) == raw }
    }
}

/** Read/write under exactly one OS-backed native MMKV lock in the Android adapter. */
internal interface VpnSessionRecordIO {
    fun tryLock(): Boolean
    fun read(): String?
    fun write(value: String): Boolean
    fun unlock()
}

internal sealed class VpnSessionRecordResult {
    data class Applied(val state: VpnSessionSnapshot) : VpnSessionRecordResult()
    object Rejected : VpnSessionRecordResult()
    object Unavailable : VpnSessionRecordResult()
}

/**
 * Never pre-read the record before taking the native process lock. This
 * transaction is not a full VPN coordination service: it only serializes
 * state transitions for callers holding a real cross-process lease.
 */
internal class VpnSessionRecordStore(private val io: VpnSessionRecordIO) {
    fun apply(change: (VpnSessionSnapshot) -> VpnSessionSnapshot?): VpnSessionRecordResult {
        val locked = try {
            io.tryLock()
        } catch (_: Exception) {
            false
        }
        if (!locked) return VpnSessionRecordResult.Unavailable

        var result: VpnSessionRecordResult = VpnSessionRecordResult.Unavailable
        try {
            val old = io.read()?.let(VpnSessionRecordCodec::decode)
            if (old != null) {
                val updated = change(old)
                result = when {
                    updated == null -> VpnSessionRecordResult.Rejected
                    updated == old -> VpnSessionRecordResult.Applied(old)
                    else -> {
                        val value = VpnSessionRecordCodec.encode(updated)
                        if (value != null && io.write(value)) {
                            VpnSessionRecordResult.Applied(updated)
                        } else VpnSessionRecordResult.Unavailable
                    }
                }
            }
        } catch (_: Exception) {
            result = VpnSessionRecordResult.Unavailable
        } finally {
            // If the OS lock cannot be released, do not report success.
            try {
                io.unlock()
            } catch (_: Exception) {
                result = VpnSessionRecordResult.Unavailable
            }
        }
        return result
    }
}
