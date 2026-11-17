package com.v2ray.ang.service

/** The live VPN modes that can participate in a shared fencing generation. */
internal enum class VpnSessionMode { XRAY_VPN, PSIPHON_VIA_XRAY }

/** Processes that must finish teardown before a successor may start. */
internal enum class VpnSessionRole { XRAY, PSIPHON }

internal enum class VpnSessionPhase { IDLE, STARTING, ACTIVE, STOPPING }

/**
 * Immutable snapshot for an eventual atomically persisted, cross-process lease.
 * This model alone provides NO inter-process locking or native ownership.
 */
internal data class VpnSessionSnapshot(
    val generation: Long,
    val sessionId: String?,
    val mode: VpnSessionMode?,
    val phase: VpnSessionPhase,
    val members: Set<VpnSessionRole>,
)

/**
 * Fail-closed, side-effect-free policy for VPN session starts/stops.
 * All read/modify/write transitions MUST later be executed under a real
 * inter-process lock. Do not call this directly from Android services.
 */
internal object VpnSessionFence {
    private val idFormat = Regex("[A-Za-z0-9_-]{32,80}")

    fun empty(): VpnSessionSnapshot = idle(0L)

    private fun idle(generation: Long) = VpnSessionSnapshot(
        generation = generation,
        sessionId = null,
        mode = null,
        phase = VpnSessionPhase.IDLE,
        members = emptySet(),
    )

    private fun required(mode: VpnSessionMode): Set<VpnSessionRole> = when (mode) {
        VpnSessionMode.XRAY_VPN -> setOf(VpnSessionRole.XRAY)
        VpnSessionMode.PSIPHON_VIA_XRAY -> setOf(VpnSessionRole.XRAY, VpnSessionRole.PSIPHON)
    }

    /** Treat malformed persisted data as unavailable; never infer that it is idle. */
    private fun valid(state: VpnSessionSnapshot): Boolean {
        if (state.generation < 0L) return false
        if (state.phase == VpnSessionPhase.IDLE) {
            return state.sessionId == null && state.mode == null && state.members.isEmpty()
        }
        val mode = state.mode ?: return false
        val sessionId = state.sessionId ?: return false
        if (state.generation == 0L || !idFormat.matches(sessionId)) return false
        val roles = required(mode)
        if (!roles.containsAll(state.members)) return false
        return when (state.phase) {
            VpnSessionPhase.STARTING -> state.members.size < roles.size
            VpnSessionPhase.ACTIVE -> state.members == roles
            VpnSessionPhase.STOPPING -> state.members.isNotEmpty()
            VpnSessionPhase.IDLE -> false
        }
    }

    private fun matches(state: VpnSessionSnapshot, sessionId: String, generation: Long): Boolean =
        valid(state) && state.phase != VpnSessionPhase.IDLE &&
            state.sessionId == sessionId && state.generation == generation

    /** A controller starts a new generation only after the old one is fully idle. */
    fun begin(previous: VpnSessionSnapshot, sessionId: String, mode: VpnSessionMode): VpnSessionSnapshot? {
        if (!valid(previous) || previous.phase != VpnSessionPhase.IDLE ||
            previous.generation == Long.MAX_VALUE || !idFormat.matches(sessionId)
        ) return null
        return VpnSessionSnapshot(previous.generation + 1L, sessionId, mode,
            VpnSessionPhase.STARTING, emptySet())
    }

    /** Each required process joins at most once, for the exact generation. */
    fun attach(state: VpnSessionSnapshot, sessionId: String, generation: Long,
               role: VpnSessionRole): VpnSessionSnapshot? {
        if (!matches(state, sessionId, generation) || state.phase != VpnSessionPhase.STARTING) return null
        val roles = required(state.mode ?: return null)
        if (role !in roles || role in state.members) return null
        val members = state.members + role
        val phase = if (members == roles) VpnSessionPhase.ACTIVE else VpnSessionPhase.STARTING
        return state.copy(phase = phase, members = members)
    }

    /** Repeated stop requests for this generation are idempotent. */
    fun stop(state: VpnSessionSnapshot, sessionId: String, generation: Long): VpnSessionSnapshot? {
        if (!matches(state, sessionId, generation)) return null
        if (state.phase == VpnSessionPhase.STOPPING) return state
        if (state.phase != VpnSessionPhase.STARTING && state.phase != VpnSessionPhase.ACTIVE) return null
        return if (state.members.isEmpty()) idle(state.generation)
               else state.copy(phase = VpnSessionPhase.STOPPING)
    }

    /** Remove a participant only after its native work has actually stopped. */
    fun release(state: VpnSessionSnapshot, sessionId: String, generation: Long,
                role: VpnSessionRole): VpnSessionSnapshot? {
        if (!matches(state, sessionId, generation) ||
            state.phase != VpnSessionPhase.STOPPING || role !in state.members
        ) return null
        val members = state.members - role
        return if (members.isEmpty()) idle(state.generation) else state.copy(members = members)
    }

    /** Strict persisted record verification; never decode malformed state as IDLE. */
    fun isValidSnapshot(state: VpnSessionSnapshot): Boolean = valid(state)

    /** Checks lifetime membership, NOT OS packet ownership or authentication. */
    fun canAct(state: VpnSessionSnapshot, sessionId: String, generation: Long,
               role: VpnSessionRole): Boolean =
        matches(state, sessionId, generation) && role in state.members
}
