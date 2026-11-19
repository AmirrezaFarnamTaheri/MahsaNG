package com.v2ray.ang.service

/**
 * Untrusted notice that a future, private Android process observer may supply.
 *
 * An ID and generation are fencing identifiers, not process identity or
 * authentication. This class intentionally has no PID/timestamp and cannot
 * demonstrate that JNI, TUN aliases, sockets or native workers terminated.
 */
internal data class VpnProcessDeathReport(
    val sessionId: String,
    val generation: Long,
    val role: VpnSessionRole,
)

/**
 * Pure fail-closed process-loss policy. NOT WIRED to production services.
 *
 * The future trusted controller may apply this under VpnSessionRecordStore's
 * native cross-process lock only after verifying the reporting OS process
 * actually owns this exact role and generation. A process death forces the
 * enrolled session into STOPPING, retaining EVERY native participant until
 * separate, verified native-stop evidence can release it.
 *
 * Unenrolled STARTING is deliberately left unchanged: process death cannot
 * imply that no native work was started before attaching the role.
 */
internal object VpnProcessDeathQuarantine {
    fun markLost(
        state: VpnSessionSnapshot,
        report: VpnProcessDeathReport,
    ): VpnSessionSnapshot? {
        if (VpnStopCommandCodec.encode(
                VpnStopCommand(report.sessionId, report.generation)
            ) == null ||
            state.members.isEmpty() ||
            !VpnSessionFence.canAct(state, report.sessionId, report.generation, report.role)
        ) return null

        return when (state.phase) {
            VpnSessionPhase.STOPPING -> state // Repeat reports cannot drop a member.
            VpnSessionPhase.STARTING, VpnSessionPhase.ACTIVE ->
                VpnSessionFence.stop(state, report.sessionId, report.generation)
            VpnSessionPhase.IDLE -> null
        }
    }
}
