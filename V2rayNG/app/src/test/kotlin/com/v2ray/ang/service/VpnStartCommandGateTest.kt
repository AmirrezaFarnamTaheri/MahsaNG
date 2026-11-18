package com.v2ray.ang.service

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** Pure Kotlin start-command policy tests. Native start remains out of scope. */
class VpnStartCommandGateTest {
    private val oldId = "11111111-1111-4111-8111-111111111111"
    private val newId = "22222222-2222-4222-8222-222222222222"

    private fun start(mode: VpnSessionMode = VpnSessionMode.PSIPHON_VIA_XRAY): VpnSessionSnapshot =
        requireNotNull(VpnSessionFence.begin(VpnSessionFence.empty(), oldId, mode))

    private fun command(role: VpnSessionRole = VpnSessionRole.XRAY,
                        mode: VpnSessionMode = VpnSessionMode.PSIPHON_VIA_XRAY,
                        generation: Long = 1L,
                        id: String = oldId): VpnStartCommand =
        VpnStartCommand(id, generation, mode, role)

    @Test fun canonicalWireRoundTripsForBothRequiredRoles() {
        for (role in VpnSessionRole.values()) {
            val value = command(role)
            val wire = requireNotNull(VpnStartCommandCodec.encode(value))
            assertEquals("v1.$oldId.1.PSIPHON_VIA_XRAY.${role.name}", wire)
            assertEquals(value, VpnStartCommandCodec.decode(wire))
        }
    }

    @Test fun rejectsNonCanonicalMalformedAndShellUnsafeWire() {
        val valid = "v1.$oldId.1.PSIPHON_VIA_XRAY.XRAY"
        for (invalid in listOf(
            "", "v2.$oldId.1.PSIPHON_VIA_XRAY.XRAY", valid + ".extra", valid + " ",
            "v1|$oldId|1|PSIPHON_VIA_XRAY|XRAY", "v1.short.1.PSIPHON_VIA_XRAY.XRAY",
            "v1.$oldId.0.PSIPHON_VIA_XRAY.XRAY", "v1.$oldId.-1.PSIPHON_VIA_XRAY.XRAY",
            "v1.$oldId.01.PSIPHON_VIA_XRAY.XRAY", "v1.$oldId.+1.PSIPHON_VIA_XRAY.XRAY",
            "v1.$oldId.9223372036854775808.PSIPHON_VIA_XRAY.XRAY",
            "v1.$oldId.1.OTHER.XRAY", "v1.$oldId.1.PSIPHON_VIA_XRAY.OTHER",
            "v1.$oldId.1.PSIPHON_VIA_XRAY.XRAY\n"
        )) assertNull("accepted: $invalid", VpnStartCommandCodec.decode(invalid))
    }

    @Test fun rejectsRoleNotSupportedByRequestedMode() {
        val invalid = command(role = VpnSessionRole.PSIPHON, mode = VpnSessionMode.XRAY_VPN)
        assertNull(VpnStartCommandCodec.encode(invalid))
        assertNull(VpnStartCommandCodec.decode("v1.$oldId.1.XRAY_VPN.PSIPHON"))
        assertFalse(VpnStartCommandGate.mayReserve(start(VpnSessionMode.XRAY_VPN), invalid))
    }

    @Test fun exactControllerIssuedTokenAndModeAreRequired() {
        val starting = start()
        assertTrue(VpnStartCommandGate.mayReserve(starting, command()))
        assertFalse(VpnStartCommandGate.mayReserve(starting, command(id = newId)))
        assertFalse(VpnStartCommandGate.mayReserve(starting, command(generation = 2)))
        assertFalse(VpnStartCommandGate.mayReserve(starting, command(generation = 0)))
        assertFalse(VpnStartCommandGate.mayReserve(starting, command(mode = VpnSessionMode.XRAY_VPN)))
    }

    @Test fun chainedModeRequiresBothReservationsBeforeMembershipActive() {
        for (first in VpnSessionRole.values()) {
            val initial = start()
            val firstCommand = command(role = first)
            val partial = requireNotNull(VpnStartCommandGate.reserve(initial, firstCommand))
            assertEquals(VpnSessionPhase.STARTING, partial.phase)
            assertEquals(setOf(first), partial.members)
            assertTrue(VpnStartCommandGate.stillAttached(partial, firstCommand))
            val other = if (first == VpnSessionRole.XRAY) VpnSessionRole.PSIPHON else VpnSessionRole.XRAY
            val complete = requireNotNull(VpnStartCommandGate.reserve(partial, command(role = other)))
            assertEquals(VpnSessionPhase.ACTIVE, complete.phase)
            assertEquals(setOf(VpnSessionRole.XRAY, VpnSessionRole.PSIPHON), complete.members)
        }
    }

    @Test fun duplicateReservationMustNotStartTheSameWorkerTwice() {
        val issued = start()
        val joined = requireNotNull(VpnStartCommandGate.reserve(issued, command()))
        assertNull(VpnStartCommandGate.reserve(joined, command()))
        assertFalse(VpnStartCommandGate.mayReserve(joined, command()))
        assertTrue(VpnStartCommandGate.stillAttached(joined, command()))
    }

    @Test fun stopBeforeDelayedStartCancelsAllEarlierReservations() {
        val issued = start()
        val stopping = requireNotNull(VpnSessionFence.stop(issued, oldId, issued.generation))
        assertEquals(VpnSessionPhase.IDLE, stopping.phase)
        for (role in VpnSessionRole.values()) {
            assertNull(VpnStartCommandGate.reserve(stopping, command(role = role)))
            assertFalse(VpnStartCommandGate.stillAttached(stopping, command(role = role)))
        }
    }

    @Test fun stopAfterFirstRoleJoinsRejectsLateParticipant() {
        val issued = start()
        val xray = requireNotNull(VpnStartCommandGate.reserve(issued, command()))
        val stopping = requireNotNull(VpnSessionFence.stop(xray, oldId, xray.generation))
        assertEquals(VpnSessionPhase.STOPPING, stopping.phase)
        assertFalse(VpnStartCommandGate.stillAttached(stopping, command()))
        assertNull(VpnStartCommandGate.reserve(stopping, command(VpnSessionRole.PSIPHON)))
        assertNull(VpnSessionFence.begin(stopping, newId, VpnSessionMode.XRAY_VPN))
    }

    @Test fun oldGenerationRejectedEvenWhenOpaqueSessionIdIsReused() {
        val first = start(VpnSessionMode.XRAY_VPN)
        val idle = requireNotNull(VpnSessionFence.stop(first, oldId, first.generation))
        val second = requireNotNull(VpnSessionFence.begin(idle, oldId, VpnSessionMode.XRAY_VPN))
        val oldCommand = command(mode = VpnSessionMode.XRAY_VPN)
        assertEquals(2L, second.generation)
        assertNull(VpnStartCommandGate.reserve(second, oldCommand))
        assertFalse(VpnStartCommandGate.stillAttached(second, oldCommand))
        assertTrue(VpnStartCommandGate.mayReserve(second, oldCommand.copy(generation = 2L)))
    }

    @Test fun malformedSnapshotAndUnavailableStorageFailClosed() {
        val malformed = start().copy(phase = VpnSessionPhase.IDLE)
        assertFalse(VpnStartCommandGate.mayReserve(malformed, command()))
        assertNull(VpnStartCommandGate.reserve(malformed, command()))

        class FakeStorage : VpnSessionRecordIO {
            var record = VpnSessionRecordCodec.encode(start())
            var denied = true
            var writes = 0
            override fun tryLock(): Boolean = !denied
            override fun read(): String? = record
            override fun write(value: String): Boolean { record = value; writes++; return true }
            override fun unlock() = Unit
        }
        val io = FakeStorage()
        val store = VpnSessionRecordStore(io)
        assertEquals(VpnSessionRecordResult.Unavailable, store.apply {
            VpnStartCommandGate.reserve(it, command())
        })
        assertEquals(0, io.writes)
        io.denied = false
        val accepted = store.apply { VpnStartCommandGate.reserve(it, command()) }
        assertTrue(accepted is VpnSessionRecordResult.Applied)
        assertEquals(1, io.writes)
        assertEquals(VpnSessionRecordResult.Rejected, store.apply {
            VpnStartCommandGate.reserve(it, command())
        })
        assertEquals(1, io.writes)
    }
}
