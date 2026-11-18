package com.v2ray.ang.service

/**
 * Role-specific, generation-fenced *claims* about observed native teardown.
 *
 * This is a pure policy input, NOT a trusted receipt or source of observations.
 * Any caller can construct these values. Only a future trusted service owner
 * may populate them from real JNI/process/TUN teardown under its generation.
 * The live Android VPN services do not construct or persist these claims.
 */
internal sealed interface VpnNativeStopEvidence {
    val sessionId: String
    val generation: Long
    val role: VpnSessionRole

    /** Every required observation for this role must be independently true. */
    fun isComplete(): Boolean

    /**
     * This is stricter than Xray's existing local UI Stop Success.
     * A returned stopLoop alone does not prove tun2socks exit or TUN close.
     */
    data class Xray(
        override val sessionId: String,
        override val generation: Long,
        val stopLoopReturned: Boolean,
        val coreNotRunning: Boolean,
        val tun2socksProcessExited: Boolean,
        val fragmentorListenersExited: Boolean,
        // A closed listener does not imply accepted-client up/downstream exit.
        val fragmentorForwardingWorkersExited: Boolean,
        val tunDescriptorClosed: Boolean,
    ) : VpnNativeStopEvidence {
        override val role: VpnSessionRole get() = VpnSessionRole.XRAY

        override fun isComplete(): Boolean =
            stopLoopReturned && coreNotRunning && tun2socksProcessExited &&
                fragmentorListenersExited && fragmentorForwardingWorkersExited &&
                tunDescriptorClosed
    }

    /**
     * PsiphonTunnel.stop() returning is NOT a native shutdown receipt.
     * psiphonNativeShutdownAcknowledged requires a separate verified native
     * completion mechanism which does not yet exist in production.
     */
    data class Psiphon(
        override val sessionId: String,
        override val generation: Long,
        val routingWorkerExited: Boolean,
        val psiphonNativeShutdownAcknowledged: Boolean,
        val tunDescriptorClosed: Boolean,
    ) : VpnNativeStopEvidence {
        override val role: VpnSessionRole get() = VpnSessionRole.PSIPHON

        override fun isComplete(): Boolean =
            routingWorkerExited && psiphonNativeShutdownAcknowledged &&
                tunDescriptorClosed
    }
}
