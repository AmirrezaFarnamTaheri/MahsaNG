package com.v2ray.ang.service

/** Fencing identity supplied by a future trusted controller-issued Start intent. */
internal data class VpnStartCommand(
    val sessionId: String,
    val generation: Long,
    val mode: VpnSessionMode,
    val role: VpnSessionRole,
)

/**
 * Bounded, canonical, shell-safe wire format for debug QA and future private IPC.
 * An identifier/generation is NOT an authentication credential.
 */
internal object VpnStartCommandCodec {
    private const val VERSION = "v1"
    private val sessionIdFormat = Regex("[A-Za-z0-9_-]{32,80}")

    private fun supports(mode: VpnSessionMode, role: VpnSessionRole): Boolean = when (mode) {
        VpnSessionMode.XRAY_VPN -> role == VpnSessionRole.XRAY
        VpnSessionMode.PSIPHON_VIA_XRAY -> role == VpnSessionRole.XRAY || role == VpnSessionRole.PSIPHON
    }

    fun encode(command: VpnStartCommand): String? {
        if (!sessionIdFormat.matches(command.sessionId) || command.generation <= 0L ||
            !supports(command.mode, command.role)
        ) return null
        return "$VERSION.${command.sessionId}.${command.generation}.${command.mode.name}.${command.role.name}"
    }

    fun decode(wire: String): VpnStartCommand? {
        if (wire.length !in 1..160) return null
        val segments = wire.split('.')
        if (segments.size != 5 || segments[0] != VERSION) return null
        val generation = segments[2].toLongOrNull() ?: return null
        val mode = VpnSessionMode.values().firstOrNull { it.name == segments[3] } ?: return null
        val role = VpnSessionRole.values().firstOrNull { it.name == segments[4] } ?: return null
        val command = VpnStartCommand(segments[1], generation, mode, role)
        // Canonical equality also rejects whitespace, leading zeroes and plus signs.
        return command.takeIf { encode(it) == wire }
    }
}

/**
 * Pure, fail-closed reservation policy; NOT a live VPN start authorization.
 *
 * A trusted controller must first persist a matching STARTING generation under
 * an OS-backed cross-process lock. Service recipients must reserve their role
 * inside VpnSessionRecordStore.apply(), not on a stale local snapshot. A
 * reservation only records membership; it does not indicate that JNI, TUN,
 * sockets, or native workers started successfully.
 *
 * Any asynchronous native work must recheck the current generation at its
 * own lifecycle boundary, and a stop/start race must not be resolved by this
 * pure check alone. Do not wire it directly into Android services.
 */
internal object VpnStartCommandGate {
    fun mayReserve(state: VpnSessionSnapshot, command: VpnStartCommand): Boolean =
        VpnStartCommandCodec.encode(command) != null &&
            VpnSessionFence.isValidSnapshot(state) &&
            state.phase == VpnSessionPhase.STARTING &&
            state.sessionId == command.sessionId &&
            state.generation == command.generation &&
            state.mode == command.mode &&
            command.role !in state.members

    fun reserve(state: VpnSessionSnapshot, command: VpnStartCommand): VpnSessionSnapshot? {
        if (!mayReserve(state, command)) return null
        return VpnSessionFence.attach(state, command.sessionId, command.generation, command.role)
    }

    /** Read-only membership check; NOT sufficient by itself to start native work. */
    fun stillAttached(state: VpnSessionSnapshot, command: VpnStartCommand): Boolean =
        VpnStartCommandCodec.encode(command) != null &&
            VpnSessionFence.isValidSnapshot(state) &&
            (state.phase == VpnSessionPhase.STARTING || state.phase == VpnSessionPhase.ACTIVE) &&
            state.sessionId == command.sessionId &&
            state.generation == command.generation &&
            state.mode == command.mode &&
            command.role in state.members
}
