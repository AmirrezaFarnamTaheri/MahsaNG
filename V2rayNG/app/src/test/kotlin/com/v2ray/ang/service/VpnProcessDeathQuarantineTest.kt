package com.v2ray.ang.service

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Policy-only tests: process death is NOT native termination evidence. Reports
 * are untrusted until a future controller binds them to the real service PID.
 */
class VpnProcessDeathQuarantineTest {
    private val firstId = "11111111-1111-4111-8111-111111111111"
    private val nextId = "22222222-2222-4222-8222-222222222222"

    private fun session(mode: VpnSessionMode = VpnSessionMode.PSIPHON_VIA_XRAY): VpnSessionSnapshot {
        val starting = requireNotNull(VpnSessionFence.begin(VpnSessionFence.empty(), firstId, mode))
        val withXray = requireNotNull(VpnSessionFence.attach(
            starting, firstId, starting.generation, VpnSessionRole.XRAY
        ))
        return if (mode == VpnSessionMode.XRAY_VPN) withXray else requireNotNull(
            VpnSessionFence.attach(withXray, firstId, starting.generation, VpnSessionRole.PSIPHON)
        )
    }

    private fun lost(role: VpnSessionRole = VpnSessionRole.XRAY,
                     id: String = firstId, generation: Long = 1L) =
        VpnProcessDeathReport(id, generation, role)

    @Test fun xrayCrashChangesActiveSessionToStoppingWithoutReleasingItsRole() {
        val running = session(VpnSessionMode.XRAY_VPN)
        val blocked = requireNotNull(VpnProcessDeathQuarantine.markLost(running, lost()))
        assertEquals(VpnSessionPhase.STOPPING, blocked.phase)
        assertEquals(setOf(VpnSessionRole.XRAY), blocked.members)
        assertEquals(firstId, blocked.sessionId)
        assertEquals(1L, blocked.generation)
        assertNull(VpnSessionFence.begin(blocked, nextId, VpnSessionMode.XRAY_VPN))
    }

    @Test fun chainedPsiphonCrashKeepsBothNativeOwnersQuarantined() {
        val running = session()
        val blocked = requireNotNull(VpnProcessDeathQuarantine.markLost(
            running, lost(VpnSessionRole.PSIPHON)
        ))
        assertEquals(VpnSessionPhase.STOPPING, blocked.phase)
        assertEquals(setOf(VpnSessionRole.XRAY, VpnSessionRole.PSIPHON), blocked.members)
        assertNull(VpnSessionFence.begin(blocked, nextId, VpnSessionMode.PSIPHON_VIA_XRAY))
    }

    @Test fun crashOfReservedRoleDuringStartingPreservesMemberAndCancelsLateStart() {
        val begin = requireNotNull(VpnSessionFence.begin(VpnSessionFence.empty(),
            firstId, VpnSessionMode.PSIPHON_VIA_XRAY))
        val partiallyStarted = requireNotNull(VpnSessionFence.attach(
            begin, firstId, 1L, VpnSessionRole.XRAY
        ))
        val quarantined = requireNotNull(VpnProcessDeathQuarantine.markLost(partiallyStarted, lost()))
        assertEquals(VpnSessionPhase.STOPPING, quarantined.phase)
        assertEquals(setOf(VpnSessionRole.XRAY), quarantined.members)
        assertNull(VpnSessionFence.attach(quarantined, firstId, 1L, VpnSessionRole.PSIPHON))
    }

    @Test fun unreservedCrashDuringStartingNeverTreatsOldGenerationAsIdle() {
        val starting = requireNotNull(VpnSessionFence.begin(
            VpnSessionFence.empty(), firstId, VpnSessionMode.PSIPHON_VIA_XRAY
        ))
        assertNull(VpnProcessDeathQuarantine.markLost(starting, lost()))
        assertEquals(VpnSessionPhase.STARTING, starting.phase)
        assertNull(VpnSessionFence.begin(starting, nextId, VpnSessionMode.XRAY_VPN))
    }

    @Test fun forgedRoleAndWrongIdOrGenerationCannotQuarantineAnotherOwner() {
        val running = session(VpnSessionMode.XRAY_VPN)
        assertNull(VpnProcessDeathQuarantine.markLost(running, lost(VpnSessionRole.PSIPHON)))
        assertNull(VpnProcessDeathQuarantine.markLost(running, lost(id = nextId)))
        assertNull(VpnProcessDeathQuarantine.markLost(running, lost(generation = 2L)))
        assertNull(VpnProcessDeathQuarantine.markLost(running, lost(generation = 0L)))
        assertNull(VpnProcessDeathQuarantine.markLost(running, lost(id = "bad")))
        assertEquals(VpnSessionPhase.ACTIVE, running.phase)
    }

    @Test fun duplicateCrashReportIsIdempotentWithoutDroppingMembers() {
        val running = session()
        val stopping = requireNotNull(VpnProcessDeathQuarantine.markLost(running, lost()))
        assertEquals(stopping, VpnProcessDeathQuarantine.markLost(stopping, lost()))
        assertEquals(setOf(VpnSessionRole.XRAY, VpnSessionRole.PSIPHON), stopping.members)
    }

    @Test fun previouslyReleasedRoleCannotQuarantineRemainingMember() {
        val running = session()
        val stopping = requireNotNull(VpnSessionFence.stop(running, firstId, 1L))
        val remaining = requireNotNull(VpnSessionFence.release(stopping, firstId, 1L, VpnSessionRole.XRAY))
        assertEquals(setOf(VpnSessionRole.PSIPHON), remaining.members)
        assertNull(VpnProcessDeathQuarantine.markLost(remaining, lost(VpnSessionRole.XRAY)))
        assertEquals(remaining, VpnProcessDeathQuarantine.markLost(remaining, lost(VpnSessionRole.PSIPHON)))
    }

    @Test fun idleAndMalformedSnapshotsCannotBecomeQuarantineRecords() {
        assertNull(VpnProcessDeathQuarantine.markLost(VpnSessionFence.empty(), lost()))
        val malformed = session().copy(phase = VpnSessionPhase.IDLE)
        assertFalse(VpnSessionFence.isValidSnapshot(malformed))
        assertNull(VpnProcessDeathQuarantine.markLost(malformed, lost()))
    }

    @Test fun persistedQuarantineTransitionUsesExistingLockAndRetainsRole() {
        class MemoryRecord : VpnSessionRecordIO {
            var raw = VpnSessionRecordCodec.encode(session())
            var writes = 0
            var locks = 0
            var unavailable = false
            override fun tryLock(): Boolean {
                if (unavailable) return false
                locks++
                return true
            }
            override fun read(): String? = raw
            override fun write(value: String): Boolean { raw = value; writes++; return true }
            override fun unlock() = Unit
        }
        val io = MemoryRecord()
        val store = VpnSessionRecordStore(io)
        val first = store.apply { VpnProcessDeathQuarantine.markLost(it, lost(VpnSessionRole.PSIPHON)) }
        assertTrue(first is VpnSessionRecordResult.Applied)
        assertEquals(1, io.writes)
        val persisted = requireNotNull(io.raw).let { requireNotNull(VpnSessionRecordCodec.decode(it)) }
        assertEquals(VpnSessionPhase.STOPPING, persisted.phase)
        assertEquals(setOf(VpnSessionRole.XRAY, VpnSessionRole.PSIPHON), persisted.members)
        assertTrue(store.apply { VpnProcessDeathQuarantine.markLost(it, lost(VpnSessionRole.PSIPHON)) }
            is VpnSessionRecordResult.Applied)
        assertEquals(1, io.writes) // Idempotent duplicate.
        assertEquals(VpnSessionRecordResult.Rejected, store.apply {
            VpnProcessDeathQuarantine.markLost(it, lost(generation = 2))
        })
        assertEquals(1, io.writes)
        io.unavailable = true
        assertEquals(VpnSessionRecordResult.Unavailable, store.apply {
            VpnProcessDeathQuarantine.markLost(it, lost())
        })
        assertEquals(1, io.writes)
    }

    @Test fun reusedSessionIdAtNewGenerationRejectsEarlierCrashReport() {
        val running = session(VpnSessionMode.XRAY_VPN)
        val stopping = requireNotNull(VpnSessionFence.stop(running, firstId, 1L))
        val released = requireNotNull(VpnSessionFence.release(stopping, firstId, 1L, VpnSessionRole.XRAY))
        val next = requireNotNull(VpnSessionFence.begin(released, firstId, VpnSessionMode.XRAY_VPN))
        val newActive = requireNotNull(VpnSessionFence.attach(next, firstId, 2L, VpnSessionRole.XRAY))
        assertNull(VpnProcessDeathQuarantine.markLost(newActive, lost(generation = 1L)))
        assertEquals(VpnSessionPhase.ACTIVE, newActive.phase)
    }

    @Test fun deathReportCannotBeSubstitutedForNativeStopEvidence() {
        val quarantined = requireNotNull(VpnProcessDeathQuarantine.markLost(session(), lost()))
        val request = VpnStopCommand(firstId, 1L)
        val unproven = VpnNativeStopEvidence.Xray(
            firstId, 1L, stopLoopReturned = false, coreNotRunning = false,
            tun2socksProcessExited = false, fragmentorListenersExited = false,
            fragmentorForwardingWorkersExited = false, tunDescriptorClosed = false,
        )
        assertNull(VpnStopCommandGate.acknowledgeStopped(quarantined, request, unproven))
        assertEquals(setOf(VpnSessionRole.XRAY, VpnSessionRole.PSIPHON), quarantined.members)
    }
}
