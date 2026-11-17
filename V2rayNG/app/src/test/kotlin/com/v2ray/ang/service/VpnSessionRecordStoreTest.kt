package com.v2ray.ang.service

import org.junit.Assert.*
import org.junit.Test

/** Real pure Kotlin transaction/codec exercised without Android or MMKV. */
class VpnSessionRecordStoreTest {
    private val first = "11111111-1111-4111-8111-111111111111"
    private val second = "22222222-2222-4222-8222-222222222222"

    private class MemoryRecord(
        var raw: String? = VpnSessionRecordCodec.encode(VpnSessionFence.empty()),
    ) : VpnSessionRecordIO {
        var locks = 0
        var unlocks = 0
        var writes = 0
        var denyLock = false
        var rejectWrite = false
        var throwOnRead = false
        override fun tryLock(): Boolean {
            if (denyLock) return false
            locks++
            return true
        }
        override fun read(): String? {
            if (throwOnRead) error("storage read unavailable")
            return raw
        }
        override fun write(value: String): Boolean {
            writes++
            if (rejectWrite) return false
            raw = value
            return true
        }
        override fun unlock() { unlocks++ }
    }

    private fun applied(result: VpnSessionRecordResult): VpnSessionSnapshot =
        (result as VpnSessionRecordResult.Applied).state

    @Test fun exactRoundTripAndCanonicalEncodingForBothModes() {
        val initial = VpnSessionFence.empty()
        val start = requireNotNull(VpnSessionFence.begin(initial, first, VpnSessionMode.PSIPHON_VIA_XRAY))
        val joined = requireNotNull(VpnSessionFence.attach(start, first, start.generation, VpnSessionRole.PSIPHON))
        val active = requireNotNull(VpnSessionFence.attach(joined, first, start.generation, VpnSessionRole.XRAY))
        for (state in listOf(initial, start, joined, active,
            requireNotNull(VpnSessionFence.stop(active, first, start.generation))
        )) {
            val raw = requireNotNull(VpnSessionRecordCodec.encode(state))
            assertEquals(state, VpnSessionRecordCodec.decode(raw))
            assertEquals(raw, VpnSessionRecordCodec.encode(VpnSessionRecordCodec.decode(raw)!!))
        }
    }

    @Test fun corruptUnknownOrNonCanonicalWireRecordsFailClosed() {
        val raw = requireNotNull(VpnSessionRecordCodec.encode(VpnSessionFence.empty()))
        for (invalid in listOf("", "not-json", "v0" + raw.drop(2), raw + "|extra",
            raw.replace("IDLE", "ACTIVE"), raw.replace("|0|", "|-1|"),
            raw.replace("|0|", "|00|"), raw + " ", raw.replace("XRAY", "UNKNOWN")
        )) assertNull("accepted: $invalid", VpnSessionRecordCodec.decode(invalid))
        val active = requireNotNull(VpnSessionFence.begin(VpnSessionFence.empty(), first, VpnSessionMode.XRAY_VPN))
        val withRole = requireNotNull(VpnSessionFence.attach(active, first, active.generation, VpnSessionRole.XRAY))
        val valid = requireNotNull(VpnSessionRecordCodec.encode(withRole))
        assertNull(VpnSessionRecordCodec.decode(valid.replace("XRAY", "XRAY,XRAY")))
    }

    @Test fun absentOrMalformedRecordCannotImplicitlyBootstrap() {
        for (raw in listOf<String?>(null, "", "bad")) {
            val io = MemoryRecord(raw)
            val result = VpnSessionRecordStore(io).apply {
                VpnSessionFence.begin(it, first, VpnSessionMode.XRAY_VPN)
            }
            assertEquals(VpnSessionRecordResult.Unavailable, result)
            assertEquals(raw, io.raw)
            assertEquals(0, io.writes)
            assertEquals(1, io.unlocks)
        }
    }

    @Test fun transactionsRequireAndReleaseNativeLock() {
        val io = MemoryRecord()
        io.denyLock = true
        val denied = VpnSessionRecordStore(io).apply {
            VpnSessionFence.begin(it, first, VpnSessionMode.XRAY_VPN)
        }
        assertEquals(VpnSessionRecordResult.Unavailable, denied)
        assertEquals(0, io.writes)
        assertEquals(0, io.unlocks)
        io.denyLock = false
        val started = applied(VpnSessionRecordStore(io).apply {
            VpnSessionFence.begin(it, first, VpnSessionMode.XRAY_VPN)
        })
        assertEquals(1L, started.generation)
        assertEquals(1, io.writes)
        assertEquals(1, io.unlocks)
    }

    @Test fun failedWriteReportsUnavailableWithoutOverwritingState() {
        val io = MemoryRecord()
        val before = io.raw
        io.rejectWrite = true
        assertEquals(VpnSessionRecordResult.Unavailable, VpnSessionRecordStore(io).apply {
            VpnSessionFence.begin(it, first, VpnSessionMode.XRAY_VPN)
        })
        assertEquals(before, io.raw)
        assertEquals(1, io.unlocks)
    }

    @Test fun storageExceptionStillReleasesNativeLock() {
        val io = MemoryRecord()
        io.throwOnRead = true
        assertEquals(VpnSessionRecordResult.Unavailable, VpnSessionRecordStore(io).apply {
            VpnSessionFence.begin(it, first, VpnSessionMode.XRAY_VPN)
        })
        assertEquals(1, io.unlocks)
        assertEquals(0, io.writes)
    }

    @Test fun refusedStaleActionsNeverWriteAndCannotChangeSuccessor() {
        val io = MemoryRecord()
        val store = VpnSessionRecordStore(io)
        val firstStarted = applied(store.apply {
            VpnSessionFence.begin(it, first, VpnSessionMode.XRAY_VPN)
        })
        val firstJoined = applied(store.apply {
            VpnSessionFence.attach(it, first, firstStarted.generation, VpnSessionRole.XRAY)
        })
        applied(store.apply { VpnSessionFence.stop(it, first, firstJoined.generation) })
        applied(store.apply { VpnSessionFence.release(it, first, firstJoined.generation, VpnSessionRole.XRAY) })
        val secondStarted = applied(store.apply {
            VpnSessionFence.begin(it, second, VpnSessionMode.XRAY_VPN)
        })
        val before = io.writes
        assertEquals(VpnSessionRecordResult.Rejected, store.apply {
            VpnSessionFence.stop(it, first, firstStarted.generation)
        })
        assertEquals(VpnSessionRecordResult.Rejected, store.apply {
            VpnSessionFence.attach(it, first, firstStarted.generation, VpnSessionRole.XRAY)
        })
        assertEquals(before, io.writes)
        assertEquals(secondStarted, VpnSessionRecordCodec.decode(io.raw!!))
    }

    @Test fun chainedSessionBlocksSuccessorUntilBothMembersRelease() {
        val io = MemoryRecord()
        val store = VpnSessionRecordStore(io)
        val issued = applied(store.apply {
            VpnSessionFence.begin(it, first, VpnSessionMode.PSIPHON_VIA_XRAY)
        })
        applied(store.apply { VpnSessionFence.attach(it, first, issued.generation, VpnSessionRole.XRAY) })
        applied(store.apply { VpnSessionFence.attach(it, first, issued.generation, VpnSessionRole.PSIPHON) })
        val stopping = applied(store.apply { VpnSessionFence.stop(it, first, issued.generation) })
        val writesBeforeDuplicate = io.writes
        assertEquals(stopping, applied(store.apply { VpnSessionFence.stop(it, first, issued.generation) }))
        assertEquals(writesBeforeDuplicate, io.writes)
        applied(store.apply { VpnSessionFence.release(it, first, issued.generation, VpnSessionRole.PSIPHON) })
        assertEquals(VpnSessionRecordResult.Rejected, store.apply {
            VpnSessionFence.begin(it, second, VpnSessionMode.XRAY_VPN)
        })
        applied(store.apply { VpnSessionFence.release(it, first, issued.generation, VpnSessionRole.XRAY) })
        assertEquals(2L, applied(store.apply {
            VpnSessionFence.begin(it, second, VpnSessionMode.XRAY_VPN)
        }).generation)
    }
}
