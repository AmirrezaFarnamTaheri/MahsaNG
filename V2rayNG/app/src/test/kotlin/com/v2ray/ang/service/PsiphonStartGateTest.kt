package com.v2ray.ang.service

import org.junit.Assert.*
import org.junit.Test
import java.util.concurrent.CountDownLatch
import java.util.concurrent.atomic.AtomicInteger

class PsiphonStartGateTest {
    @Test fun duplicateStartsDoNotCreateTwoNativeTunnelWorkers() {
        val gate = PsiphonStartGate()
        val token = gate.beginStart()!!
        assertNull(gate.beginStart())
        assertTrue(gate.isCurrent(token))
    }

    @Test fun stopInvalidatesAnOutstandingPortWaiter() {
        val gate = PsiphonStartGate()
        val stale = gate.beginStart()!!
        gate.stop()
        assertFalse(gate.isCurrent(stale))
        assertFalse(gate.isActive())
    }

    @Test fun restartCannotReuseOldAttemptToken() {
        val gate = PsiphonStartGate()
        val old = gate.beginStart()!!
        gate.stop()
        val recent = gate.beginStart()!!
        assertNotEquals(old, recent)
        assertFalse(gate.isCurrent(old))
        assertTrue(gate.isCurrent(recent))
    }

    @Test fun concurrentlyRequestedStartsAreCoalesced() {
        val gate = PsiphonStartGate()
        val start = CountDownLatch(1)
        val done = CountDownLatch(32)
        val count = AtomicInteger()
        repeat(32) {
            Thread {
                start.await()
                if (gate.beginStart() != null) count.incrementAndGet()
                done.countDown()
            }.start()
        }
        start.countDown()
        done.await()
        assertEquals(1, count.get())
    }

    @Test fun repeatedStopsKeepPendingStartInvalidated() {
        val gate = PsiphonStartGate()
        val token = gate.beginStart()!!
        gate.stop()
        gate.stop()
        assertFalse(gate.isCurrent(token))
        assertFalse(gate.isActive())
    }
}
