package com.v2ray.ang.service

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Evidence is supplied by trusted, generation-fenced native owners in a future
 * integration. These tests simulate observations; they do NOT exercise JNI.
 */
class VpnNativeStopEvidenceTest {
    private val first = "11111111-1111-4111-8111-111111111111"
    private val second = "22222222-2222-4222-8222-222222222222"
    private val command = VpnStopCommand(first, 1L)

    private fun stopped(): VpnSessionSnapshot {
        val starting = requireNotNull(VpnSessionFence.begin(
            VpnSessionFence.empty(), first, VpnSessionMode.PSIPHON_VIA_XRAY
        ))
        val xray = requireNotNull(VpnSessionFence.attach(starting, first, 1L, VpnSessionRole.XRAY))
        val active = requireNotNull(VpnSessionFence.attach(xray, first, 1L, VpnSessionRole.PSIPHON))
        return requireNotNull(VpnStopCommandGate.requestStop(active, command))
    }

    private fun xray(id: String = first, generation: Long = 1L) =
        VpnNativeStopEvidence.Xray(
            sessionId = id, generation = generation,
            stopLoopReturned = true, coreNotRunning = true,
            tun2socksProcessExited = true, fragmentorListenersExited = true,
            tunDescriptorClosed = true,
        )

    private fun psiphon(id: String = first, generation: Long = 1L) =
        VpnNativeStopEvidence.Psiphon(
            sessionId = id, generation = generation,
            routingWorkerExited = true, psiphonNativeShutdownAcknowledged = true,
            tunDescriptorClosed = true,
        )

    @Test fun xrayMissingAnyRequiredObservationCannotRelease() {
        val state = stopped()
        for (missing in listOf(
            xray().copy(stopLoopReturned = false),
            xray().copy(coreNotRunning = false),
            xray().copy(tun2socksProcessExited = false),
            xray().copy(fragmentorListenersExited = false),
            xray().copy(tunDescriptorClosed = false),
        )) {
            assertNull(VpnStopCommandGate.acknowledgeStopped(state, command, missing))
        }
        assertEquals(setOf(VpnSessionRole.XRAY, VpnSessionRole.PSIPHON), state.members)
    }

    @Test fun psiphonJniExitWithoutIndependentNativeTunnelAckCannotRelease() {
        val state = stopped()
        assertNull(VpnStopCommandGate.acknowledgeStopped(
            state, command, psiphon().copy(psiphonNativeShutdownAcknowledged = false)
        ))
        assertNull(VpnStopCommandGate.acknowledgeStopped(
            state, command, psiphon().copy(routingWorkerExited = false)
        ))
        assertNull(VpnStopCommandGate.acknowledgeStopped(
            state, command, psiphon().copy(tunDescriptorClosed = false)
        ))
    }

    @Test fun sameGenerationRequiresExactSessionIdentity() {
        val state = stopped()
        assertNull(VpnStopCommandGate.acknowledgeStopped(state, command, xray(id = second)))
        assertNull(VpnStopCommandGate.acknowledgeStopped(state, command, psiphon(id = second)))
    }

    @Test fun sameSessionRequiresExactGeneration() {
        val state = stopped()
        assertNull(VpnStopCommandGate.acknowledgeStopped(state, command, xray(generation = 2L)))
        assertNull(VpnStopCommandGate.acknowledgeStopped(state, command, psiphon(generation = 0L)))
    }

    @Test fun completeEvidenceOnlyReleasesItsOwnRole() {
        val state = stopped()
        val afterXray = requireNotNull(VpnStopCommandGate.acknowledgeStopped(state, command, xray()))
        assertEquals(VpnSessionPhase.STOPPING, afterXray.phase)
        assertEquals(setOf(VpnSessionRole.PSIPHON), afterXray.members)
        assertNull(VpnStopCommandGate.acknowledgeStopped(afterXray, command, xray()))
        assertNull(VpnSessionFence.begin(afterXray, second, VpnSessionMode.XRAY_VPN))
        val afterPsiphon = requireNotNull(VpnStopCommandGate.acknowledgeStopped(
            afterXray, command, psiphon()
        ))
        assertEquals(VpnSessionPhase.IDLE, afterPsiphon.phase)
        assertTrue(afterPsiphon.members.isEmpty())
    }

    @Test fun completeEvidenceBeforeStoppingCannotRelease() {
        val state = stopped()
        val active = state.copy(phase = VpnSessionPhase.ACTIVE)
        assertNull(VpnStopCommandGate.acknowledgeStopped(active, command, xray()))
        assertNull(VpnStopCommandGate.acknowledgeStopped(active, command, psiphon()))
    }

    @Test fun previouslyCompletedEvidenceCannotReleaseSuccessorWithReusedSessionId() {
        val stopping = stopped()
        val xrayGone = requireNotNull(VpnStopCommandGate.acknowledgeStopped(stopping, command, xray()))
        val idle = requireNotNull(VpnStopCommandGate.acknowledgeStopped(xrayGone, command, psiphon()))
        val nextStart = requireNotNull(VpnSessionFence.begin(
            idle, first, VpnSessionMode.XRAY_VPN
        ))
        val nextActive = requireNotNull(VpnSessionFence.attach(
            nextStart, first, 2L, VpnSessionRole.XRAY
        ))
        val nextStop = requireNotNull(VpnStopCommandGate.requestStop(
            nextActive, VpnStopCommand(first, 2L)
        ))
        assertNull(VpnStopCommandGate.acknowledgeStopped(nextStop, VpnStopCommand(first, 2L), xray()))
    }

    @Test fun storeLeaseCannotBeBypassedWithCompleteButStaleEvidence() {
        class MemoryIO : VpnSessionRecordIO {
            var raw = VpnSessionRecordCodec.encode(stopped())
            var writes = 0
            var locked = false
            override fun tryLock(): Boolean = !locked
            override fun read() = raw
            override fun write(value: String): Boolean { raw = value; writes++; return true }
            override fun unlock() = Unit
        }
        val io = MemoryIO()
        val store = VpnSessionRecordStore(io)
        io.locked = true
        assertEquals(VpnSessionRecordResult.Unavailable, store.apply {
            VpnStopCommandGate.acknowledgeStopped(it, command, xray())
        })
        io.locked = false
        assertEquals(VpnSessionRecordResult.Rejected, store.apply {
            VpnStopCommandGate.acknowledgeStopped(it, command, xray(generation = 2L))
        })
        assertEquals(0, io.writes)
        val accepted = store.apply { VpnStopCommandGate.acknowledgeStopped(it, command, xray()) }
        assertTrue(accepted is VpnSessionRecordResult.Applied)
        assertEquals(1, io.writes)
    }
}
