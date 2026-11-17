package com.v2ray.ang.service

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** The actual native-stop acknowledgement is supplied by the service, not inferred here. */
class VpnStopCommandGateTest {
    private val first = "11111111-1111-4111-8111-111111111111"
    private val second = "22222222-2222-4222-8222-222222222222"

    private fun begun(mode: VpnSessionMode = VpnSessionMode.PSIPHON_VIA_XRAY):
        VpnSessionSnapshot = requireNotNull(VpnSessionFence.begin(VpnSessionFence.empty(), first, mode))

    private fun active(): VpnSessionSnapshot {
        val started = begun()
        val xray = requireNotNull(VpnSessionFence.attach(started, first, 1L, VpnSessionRole.XRAY))
        return requireNotNull(VpnSessionFence.attach(xray, first, 1L, VpnSessionRole.PSIPHON))
    }

    @Test fun wireRoundTripIsExactAndCanonical() {
        val command = VpnStopCommand(first, 12L)
        val wire = requireNotNull(VpnStopCommandCodec.encode(command))
        assertEquals("v1|$first|12", wire)
        assertEquals(command, VpnStopCommandCodec.decode(wire))
        assertEquals(wire, VpnStopCommandCodec.encode(VpnStopCommandCodec.decode(wire)!!))
    }

    @Test fun malformedVersionMissingIdAndNonCanonicalGenerationFailClosed() {
        val good = "v1|$first|1"
        for (wire in listOf("", "v2|$first|1", good + "|tail", good + " ",
            "v1|short|1", "v1|$first|0", "v1|$first|-1",
            "v1|$first|01", "v1|$first|+1", "v1|$first|1.0",
            "v1|$first|9223372036854775808", "v1|$first| 1",
            "v1|$first|1\n"
        )) {
            assertNull("accepted malformed stop: $wire", VpnStopCommandCodec.decode(wire))
        }
        assertNull(VpnStopCommandCodec.encode(VpnStopCommand(first, 0L)))
        assertNull(VpnStopCommandCodec.encode(VpnStopCommand("bad", 1L)))
    }

    @Test fun staleOrWrongGenerationCannotRequestStop() {
        val started = active()
        assertNull(VpnStopCommandGate.requestStop(started, VpnStopCommand(second, 1L)))
        assertNull(VpnStopCommandGate.requestStop(started, VpnStopCommand(first, 0L)))
        assertNull(VpnStopCommandGate.requestStop(started, VpnStopCommand(first, 2L)))
        assertEquals(VpnSessionPhase.ACTIVE, started.phase)
        val stopped = requireNotNull(VpnStopCommandGate.requestStop(
            started, VpnStopCommand(first, 1L)
        ))
        assertEquals(VpnSessionPhase.STOPPING, stopped.phase)
        assertEquals(stopped, VpnStopCommandGate.requestStop(stopped, VpnStopCommand(first, 1L)))
    }

    @Test fun stopRequestWithoutAttachedWorkerNeverAuthorizesLaterWorker() {
        val started = begun()
        val stopped = requireNotNull(VpnStopCommandGate.requestStop(
            started, VpnStopCommand(first, 1L)
        ))
        assertEquals(VpnSessionPhase.IDLE, stopped.phase)
        assertFalse(VpnStopCommandGate.mayStopNative(
            stopped, VpnStopCommand(first, 1L), VpnSessionRole.XRAY
        ))
        assertNull(VpnSessionFence.attach(stopped, first, 1L, VpnSessionRole.XRAY))
    }

    @Test fun onlyAttachedRolesOfExactStoppingSessionMayReceiveStop() {
        val started = begun()
        val xray = requireNotNull(VpnSessionFence.attach(
            started, first, 1L, VpnSessionRole.XRAY
        ))
        val command = VpnStopCommand(first, 1L)
        assertFalse(VpnStopCommandGate.mayStopNative(xray, command, VpnSessionRole.XRAY))
        val stopping = requireNotNull(VpnStopCommandGate.requestStop(xray, command))
        assertTrue(VpnStopCommandGate.mayStopNative(stopping, command, VpnSessionRole.XRAY))
        assertFalse(VpnStopCommandGate.mayStopNative(stopping, command, VpnSessionRole.PSIPHON))
        assertFalse(VpnStopCommandGate.mayStopNative(
            stopping, VpnStopCommand(second, 1L), VpnSessionRole.XRAY
        ))
    }

    @Test fun nativeFailureOrNoStopRequestCannotReleaseAnyRole() {
        val state = active()
        val command = VpnStopCommand(first, 1L)
        assertNull(VpnStopCommandGate.acknowledgeStopped(
            state, command, VpnSessionRole.XRAY, nativeStopped = true
        ))
        val stopping = requireNotNull(VpnStopCommandGate.requestStop(state, command))
        for (role in listOf(VpnSessionRole.XRAY, VpnSessionRole.PSIPHON)) {
            assertNull(VpnStopCommandGate.acknowledgeStopped(
                stopping, command, role, nativeStopped = false
            ))
        }
        assertEquals(setOf(VpnSessionRole.XRAY, VpnSessionRole.PSIPHON), stopping.members)
    }

    @Test fun nextSessionCannotBeginUntilBothNativeStopAcknowledgements() {
        val command = VpnStopCommand(first, 1L)
        val stopping = requireNotNull(VpnStopCommandGate.requestStop(active(), command))
        val xrayGone = requireNotNull(VpnStopCommandGate.acknowledgeStopped(
            stopping, command, VpnSessionRole.XRAY, nativeStopped = true
        ))
        assertEquals(VpnSessionPhase.STOPPING, xrayGone.phase)
        assertEquals(setOf(VpnSessionRole.PSIPHON), xrayGone.members)
        assertNull(VpnSessionFence.begin(xrayGone, second, VpnSessionMode.XRAY_VPN))
        val idle = requireNotNull(VpnStopCommandGate.acknowledgeStopped(
            xrayGone, command, VpnSessionRole.PSIPHON, nativeStopped = true
        ))
        assertEquals(VpnSessionPhase.IDLE, idle.phase)
        val next = requireNotNull(VpnSessionFence.begin(idle, second, VpnSessionMode.XRAY_VPN))
        assertEquals(2L, next.generation)
        assertFalse(VpnStopCommandGate.mayStopNative(next, command, VpnSessionRole.XRAY))
        assertNull(VpnStopCommandGate.acknowledgeStopped(
            next, command, VpnSessionRole.XRAY, nativeStopped = true
        ))
        assertNull(VpnStopCommandGate.requestStop(next, command))
    }

    @Test fun repeatedAckCannotImpersonateAnotherMember() {
        val command = VpnStopCommand(first, 1L)
        val stopping = requireNotNull(VpnStopCommandGate.requestStop(active(), command))
        val partial = requireNotNull(VpnStopCommandGate.acknowledgeStopped(
            stopping, command, VpnSessionRole.XRAY, nativeStopped = true
        ))
        assertNull(VpnStopCommandGate.acknowledgeStopped(
            partial, command, VpnSessionRole.XRAY, nativeStopped = true
        ))
        assertTrue(VpnStopCommandGate.mayStopNative(partial, command, VpnSessionRole.PSIPHON))
    }

    @Test fun reusingTheOpaqueIdCannotBypassMonotonicGeneration() {
        val command = VpnStopCommand(first, 1L)
        val empty = VpnSessionFence.empty()
        val firstStart = requireNotNull(VpnSessionFence.begin(empty, first, VpnSessionMode.XRAY_VPN))
        val firstStop = requireNotNull(VpnStopCommandGate.requestStop(firstStart, command))
        val next = requireNotNull(VpnSessionFence.begin(firstStop, first, VpnSessionMode.XRAY_VPN))
        assertEquals(2L, next.generation)
        assertNull(VpnStopCommandGate.requestStop(next, command))
        assertNull(VpnStopCommandGate.acknowledgeStopped(
            next, command, VpnSessionRole.XRAY, nativeStopped = true
        ))
    }

    @Test fun stopRequestAndAcknowledgementsAreAtomicUnderAnInjectedStoreLease() {
        class MemoryStore : VpnSessionRecordIO {
            var raw = VpnSessionRecordCodec.encode(active())
            var writes = 0
            var unlocks = 0
            var denyLock = false
            override fun tryLock() = !denyLock
            override fun read() = raw
            override fun write(value: String): Boolean { raw = value; writes++; return true }
            override fun unlock() { unlocks++ }
        }
        val io = MemoryStore()
        val store = VpnSessionRecordStore(io)
        val command = VpnStopCommand(first, 1L)
        val stopping = store.apply { VpnStopCommandGate.requestStop(it, command) }
        assertTrue(stopping is VpnSessionRecordResult.Applied)
        assertEquals(1, io.writes)
        val duplicate = store.apply { VpnStopCommandGate.requestStop(it, command) }
        assertTrue(duplicate is VpnSessionRecordResult.Applied)
        assertEquals(1, io.writes) // no unnecessary MMKV rewrite
        io.denyLock = true
        assertEquals(VpnSessionRecordResult.Unavailable, store.apply {
            VpnStopCommandGate.acknowledgeStopped(it, command, VpnSessionRole.XRAY, true)
        })
        io.denyLock = false
        assertEquals(VpnSessionPhase.STOPPING, VpnSessionRecordCodec.decode(io.raw!!)?.phase)
        assertEquals(VpnSessionRecordResult.Rejected, store.apply {
            VpnStopCommandGate.acknowledgeStopped(it, command, VpnSessionRole.PSIPHON, false)
        })
        assertEquals(1, io.writes)
        val firstAck = store.apply {
            VpnStopCommandGate.acknowledgeStopped(it, command, VpnSessionRole.XRAY, true)
        }
        assertTrue(firstAck is VpnSessionRecordResult.Applied)
        assertEquals(2, io.writes)
        assertEquals(setOf(VpnSessionRole.PSIPHON), VpnSessionRecordCodec.decode(io.raw!!)?.members)
        assertTrue(io.unlocks >= 3)
    }

    @Test fun malformedPersistedDataCannotAuthorizeStopOrRelease() {
        class BadStore : VpnSessionRecordIO {
            override fun tryLock() = true
            override fun read(): String = "v1|broken|..."
            override fun write(value: String): Boolean = error("Must never write")
            override fun unlock() = Unit
        }
        val store = VpnSessionRecordStore(BadStore())
        val command = VpnStopCommand(first, 1L)
        assertEquals(VpnSessionRecordResult.Unavailable, store.apply {
            VpnStopCommandGate.requestStop(it, command)
        })
        assertEquals(VpnSessionRecordResult.Unavailable, store.apply {
            VpnStopCommandGate.acknowledgeStopped(it, command, VpnSessionRole.XRAY, true)
        })
    }
}
