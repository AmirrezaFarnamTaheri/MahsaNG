package com.v2ray.ang.service

/** Session fencing identifier carried by a future internal Stop command. */
internal data class VpnStopCommand(val sessionId: String, val generation: Long)

/**
 * Strict canonical transport-neutral Stop envelope. This is a fencing token,
 * not authentication or an Android intent/IPC endpoint.
 */
internal object VpnStopCommandCodec {
    private const val VERSION = "v1"
    private val idFormat = Regex("[A-Za-z0-9_-]{32,80}")

    fun encode(command: VpnStopCommand): String? {
        if (!idFormat.matches(command.sessionId) || command.generation <= 0L) return null
        return "$VERSION.${command.sessionId}.${command.generation}"
    }

    fun decode(raw: String): VpnStopCommand? {
        if (raw.length !in 1..120) return null
        val fields = raw.split('.')
        if (fields.size != 3 || fields[0] != VERSION) return null
        val generation = fields[2].toLongOrNull() ?: return null
        val command = VpnStopCommand(fields[1], generation)
        // Enforce canonical decimal generations, exact version and zero padding.
        return command.takeIf { encode(it) == raw }
    }
}

/**
 * Unwired service policy. A real controller must persist the STOPPING
 * transition under VpnSessionRecordStore's OS-backed lock BEFORE dispatch.
 *
 * A recipient must re-check eligibility under that same shared record. Its
 * native completion flag can become true ONLY after all its actual native
 * workers, owned descriptors and TUN resources are confirmed stopped.
 *
 * This class does not issue broadcasts, access Android, perform I/O or
 * prove native completion. The debug QA test uses simulated acknowledgements.
 */
internal object VpnStopCommandGate {
    /** Record a controller's stop request for the exact current generation. */
    fun requestStop(state: VpnSessionSnapshot, command: VpnStopCommand): VpnSessionSnapshot? {
        if (VpnStopCommandCodec.encode(command) == null) return null
        return VpnSessionFence.stop(state, command.sessionId, command.generation)
    }

    /** A role can stop only while still a member of the same STOPPING session. */
    fun mayStopNative(
        state: VpnSessionSnapshot,
        command: VpnStopCommand,
        role: VpnSessionRole,
    ): Boolean =
        VpnStopCommandCodec.encode(command) != null &&
            state.phase == VpnSessionPhase.STOPPING &&
            VpnSessionFence.canAct(state, command.sessionId, command.generation, role)

    /**
     * A failure, timeout or incomplete native stop keeps the role attached and
     * blocks a successor. The caller must prove completion independently.
     */
    fun acknowledgeStopped(
        state: VpnSessionSnapshot,
        command: VpnStopCommand,
        role: VpnSessionRole,
        nativeStopped: Boolean,
    ): VpnSessionSnapshot? {
        if (!nativeStopped || !mayStopNative(state, command, role)) return null
        return VpnSessionFence.release(state, command.sessionId, command.generation, role)
    }
}
