package com.v2ray.ang.service

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Policy-only session fencing. This must be paired with atomic shared storage
 * and actual native stop acknowledgement before live services may use it.
 */
class VpnSessionFenceTest {
    private val oldId = "11111111-1111-4111-8111-111111111111"
    private val newId = "22222222-2222-4222-8222-222222222222"

    @Test fun emptyStateOnlyStartsWithAValidNewSessionId() {
        val empty = VpnSessionFence.empty()
        assertEquals(VpnSessionPhase.IDLE, empty.phase)
        assertNull(VpnSessionFence.begin(empty, "", VpnSessionMode.XRAY_VPN))
        assertNull(VpnSessionFence.begin(empty, "short", VpnSessionMode.XRAY_VPN))
        val issued = requireNotNull(VpnSessionFence.begin(empty, oldId, VpnSessionMode.XRAY_VPN))
        assertEquals(1L, issued.generation)
        assertEquals(oldId, issued.sessionId)
        assertEquals(VpnSessionPhase.STARTING, issued.phase)
        assertTrue(issued.members.isEmpty())
    }

    @Test fun xrayVpnBecomesActiveOnlyAfterItsServiceJoins() {
        val issued = requireNotNull(VpnSessionFence.begin(
            VpnSessionFence.empty(), oldId, VpnSessionMode.XRAY_VPN
        ))
        assertFalse(VpnSessionFence.canAct(issued, oldId, issued.generation, VpnSessionRole.XRAY))
        val joined = requireNotNull(VpnSessionFence.attach(
            issued, oldId, issued.generation, VpnSessionRole.XRAY
        ))
        assertEquals(VpnSessionPhase.ACTIVE, joined.phase)
        assertEquals(setOf(VpnSessionRole.XRAY), joined.members)
        assertTrue(VpnSessionFence.canAct(joined, oldId, joined.generation, VpnSessionRole.XRAY))
    }

    @Test fun chainedModeWaitsForBothSeparateProcessRolesRegardlessOfArrivalOrder() {
        for (first in listOf(VpnSessionRole.XRAY, VpnSessionRole.PSIPHON)) {
            val issued = requireNotNull(VpnSessionFence.begin(
                VpnSessionFence.empty(), oldId, VpnSessionMode.PSIPHON_VIA_XRAY
            ))
            val partial = requireNotNull(VpnSessionFence.attach(
                issued, oldId, issued.generation, first
            ))
            assertEquals(VpnSessionPhase.STARTING, partial.phase)
            assertEquals(setOf(first), partial.members)
            val second = if (first == VpnSessionRole.XRAY) VpnSessionRole.PSIPHON else VpnSessionRole.XRAY
            val completed = requireNotNull(VpnSessionFence.attach(
                partial, oldId, issued.generation, second
            ))
            assertEquals(VpnSessionPhase.ACTIVE, completed.phase)
            assertEquals(setOf(VpnSessionRole.XRAY, VpnSessionRole.PSIPHON), completed.members)
        }
    }

    @Test fun wrongRoleStaleIdAndDuplicateJoinCannotStealSession() {
        val issued = requireNotNull(VpnSessionFence.begin(
            VpnSessionFence.empty(), oldId, VpnSessionMode.XRAY_VPN
        ))
        assertNull(VpnSessionFence.attach(issued, oldId, issued.generation, VpnSessionRole.PSIPHON))
        assertNull(VpnSessionFence.attach(issued, newId, issued.generation, VpnSessionRole.XRAY))
        assertNull(VpnSessionFence.attach(issued, oldId, issued.generation - 1, VpnSessionRole.XRAY))
        val joined = requireNotNull(VpnSessionFence.attach(
            issued, oldId, issued.generation, VpnSessionRole.XRAY
        ))
        assertNull(VpnSessionFence.attach(joined, oldId, joined.generation, VpnSessionRole.XRAY))
        assertFalse(VpnSessionFence.canAct(joined, newId, joined.generation, VpnSessionRole.XRAY))
    }

    @Test fun overlappingLaunchIsDeniedUntilNativeMembersAreReleased() {
        val issued = requireNotNull(VpnSessionFence.begin(
            VpnSessionFence.empty(), oldId, VpnSessionMode.XRAY_VPN
        ))
        val joined = requireNotNull(VpnSessionFence.attach(
            issued, oldId, issued.generation, VpnSessionRole.XRAY
        ))
        assertNull(VpnSessionFence.begin(joined, newId, VpnSessionMode.PSIPHON_VIA_XRAY))
        val stopping = requireNotNull(VpnSessionFence.stop(joined, oldId, joined.generation))
        assertEquals(VpnSessionPhase.STOPPING, stopping.phase)
        assertNull(VpnSessionFence.begin(stopping, newId, VpnSessionMode.XRAY_VPN))
        assertNull(VpnSessionFence.attach(stopping, oldId, stopping.generation, VpnSessionRole.PSIPHON))
        assertTrue(VpnSessionFence.canAct(stopping, oldId, stopping.generation, VpnSessionRole.XRAY))
        val released = requireNotNull(VpnSessionFence.release(
            stopping, oldId, stopping.generation, VpnSessionRole.XRAY
        ))
        assertEquals(VpnSessionPhase.IDLE, released.phase)
        assertTrue(released.members.isEmpty())
        assertNull(released.sessionId)
        assertEquals(issued.generation, released.generation)
        assertNotNull(VpnSessionFence.begin(released, newId, VpnSessionMode.XRAY_VPN))
    }

    @Test fun chainedSessionCannotRestartAfterOnlyOneDaemonReleases() {
        val issued = requireNotNull(VpnSessionFence.begin(
            VpnSessionFence.empty(), oldId, VpnSessionMode.PSIPHON_VIA_XRAY
        ))
        val xray = requireNotNull(VpnSessionFence.attach(
            issued, oldId, issued.generation, VpnSessionRole.XRAY
        ))
        val both = requireNotNull(VpnSessionFence.attach(
            xray, oldId, issued.generation, VpnSessionRole.PSIPHON
        ))
        val stopping = requireNotNull(VpnSessionFence.stop(both, oldId, both.generation))
        val psiphonGone = requireNotNull(VpnSessionFence.release(
            stopping, oldId, both.generation, VpnSessionRole.PSIPHON
        ))
        assertEquals(VpnSessionPhase.STOPPING, psiphonGone.phase)
        assertEquals(setOf(VpnSessionRole.XRAY), psiphonGone.members)
        assertNull(VpnSessionFence.begin(psiphonGone, newId, VpnSessionMode.XRAY_VPN))
        val bothGone = requireNotNull(VpnSessionFence.release(
            psiphonGone, oldId, both.generation, VpnSessionRole.XRAY
        ))
        assertEquals(VpnSessionPhase.IDLE, bothGone.phase)
    }

    @Test fun stopBeforeAnyServiceJoinsInvalidatesDelayedStartup() {
        val issued = requireNotNull(VpnSessionFence.begin(
            VpnSessionFence.empty(), oldId, VpnSessionMode.PSIPHON_VIA_XRAY
        ))
        val stopped = requireNotNull(VpnSessionFence.stop(issued, oldId, issued.generation))
        assertEquals(VpnSessionPhase.IDLE, stopped.phase)
        assertNull(VpnSessionFence.attach(stopped, oldId, issued.generation, VpnSessionRole.XRAY))
        assertNull(VpnSessionFence.attach(stopped, oldId, issued.generation, VpnSessionRole.PSIPHON))
    }

    @Test fun oldSessionCallbacksCannotStopOrReleaseNewSession() {
        val first = requireNotNull(VpnSessionFence.begin(
            VpnSessionFence.empty(), oldId, VpnSessionMode.XRAY_VPN
        ))
        val attached = requireNotNull(VpnSessionFence.attach(
            first, oldId, first.generation, VpnSessionRole.XRAY
        ))
        val stopping = requireNotNull(VpnSessionFence.stop(attached, oldId, first.generation))
        val idle = requireNotNull(VpnSessionFence.release(
            stopping, oldId, first.generation, VpnSessionRole.XRAY
        ))
        val second = requireNotNull(VpnSessionFence.begin(
            idle, newId, VpnSessionMode.XRAY_VPN
        ))
        val secondAttached = requireNotNull(VpnSessionFence.attach(
            second, newId, second.generation, VpnSessionRole.XRAY
        ))
        assertEquals(2L, secondAttached.generation)
        assertNull(VpnSessionFence.stop(secondAttached, oldId, first.generation))
        assertNull(VpnSessionFence.release(secondAttached, oldId, first.generation, VpnSessionRole.XRAY))
        assertFalse(VpnSessionFence.canAct(secondAttached, oldId, first.generation, VpnSessionRole.XRAY))
        assertTrue(VpnSessionFence.canAct(secondAttached, newId, second.generation, VpnSessionRole.XRAY))
    }

    @Test fun generationFencesOldCallbacksEvenIfOpaqueSessionIdIsReused() {
        val issued = requireNotNull(VpnSessionFence.begin(
            VpnSessionFence.empty(), oldId, VpnSessionMode.XRAY_VPN
        ))
        val idle = requireNotNull(VpnSessionFence.stop(issued, oldId, issued.generation))
        val again = requireNotNull(VpnSessionFence.begin(idle, oldId, VpnSessionMode.XRAY_VPN))
        assertEquals(issued.generation + 1L, again.generation)
        assertNull(VpnSessionFence.attach(again, oldId, issued.generation, VpnSessionRole.XRAY))
        assertNull(VpnSessionFence.stop(again, oldId, issued.generation))
    }

    @Test fun duplicateStopsAreIdempotentButDuplicateReleaseIsNot() {
        val issued = requireNotNull(VpnSessionFence.begin(
            VpnSessionFence.empty(), oldId, VpnSessionMode.XRAY_VPN
        ))
        val attached = requireNotNull(VpnSessionFence.attach(
            issued, oldId, issued.generation, VpnSessionRole.XRAY
        ))
        val stopping = requireNotNull(VpnSessionFence.stop(attached, oldId, attached.generation))
        assertEquals(stopping, VpnSessionFence.stop(stopping, oldId, attached.generation))
        val idle = requireNotNull(VpnSessionFence.release(
            stopping, oldId, attached.generation, VpnSessionRole.XRAY
        ))
        assertNull(VpnSessionFence.release(idle, oldId, attached.generation, VpnSessionRole.XRAY))
        assertNull(VpnSessionFence.stop(idle, oldId, attached.generation))
    }

    @Test fun generationOverflowRefusesNewSessionInsteadOfWrapping() {
        val idle = VpnSessionFence.empty().copy(generation = Long.MAX_VALUE)
        assertNull(VpnSessionFence.begin(idle, oldId, VpnSessionMode.XRAY_VPN))
    }

    @Test fun failedStopByWrongSessionLeavesCurrentOwnerUntouched() {
        val issued = requireNotNull(VpnSessionFence.begin(
            VpnSessionFence.empty(), oldId, VpnSessionMode.XRAY_VPN
        ))
        val joined = requireNotNull(VpnSessionFence.attach(
            issued, oldId, issued.generation, VpnSessionRole.XRAY
        ))
        assertNull(VpnSessionFence.stop(joined, newId, joined.generation))
        assertNull(VpnSessionFence.release(joined, oldId, joined.generation, VpnSessionRole.XRAY))
        assertEquals(VpnSessionPhase.ACTIVE, joined.phase)
    }
}
