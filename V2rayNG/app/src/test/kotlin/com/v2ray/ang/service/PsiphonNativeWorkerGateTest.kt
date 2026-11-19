package com.v2ray.ang.service

import org.junit.Assert.*
import org.junit.Test
import java.util.concurrent.CountDownLatch
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicInteger

class PsiphonNativeWorkerGateTest {
    @Test fun stopBeforeNativeEntryIsNotLost() {
        val stopped = AtomicBoolean(true)
        assertTrue(PsiphonNativeWorkerGate.acquire { stopped.set(false) })
        stopped.set(true)
        assertFalse(PsiphonNativeWorkerGate.acquire { stopped.set(false) })
        assertTrue(stopped.get())
        PsiphonNativeWorkerGate.release()
        assertTrue(PsiphonNativeWorkerGate.acquire { stopped.set(false) })
        assertFalse(stopped.get())
        PsiphonNativeWorkerGate.release()
    }

    @Test fun nativePrepareFailureDoesNotRetainLease() {
        try {
            PsiphonNativeWorkerGate.acquire { error("JNI unavailable") }
            fail("expected JNI failure")
        } catch (_: IllegalStateException) { }
        assertTrue(PsiphonNativeWorkerGate.acquire { })
        PsiphonNativeWorkerGate.release()
    }

    @Test fun unrelatedThreadCannotReleaseAnotherNativeWorker() {
        assertTrue(PsiphonNativeWorkerGate.acquire { })
        val released = CountDownLatch(1)
        try {
            val mistakenCallback = Thread {
                // This is currently unowned and unconditionally opens the gate.
                PsiphonNativeWorkerGate.release()
                released.countDown()
            }
            mistakenCallback.start()
            assertTrue(released.await(2, java.util.concurrent.TimeUnit.SECONDS))
            mistakenCallback.join(2_000)
            val overlappingWorker = PsiphonNativeWorkerGate.acquire { }
            if (overlappingWorker) PsiphonNativeWorkerGate.release()
            assertFalse("Unrelated callback admitted overlapping JNI owner", overlappingWorker)
        } finally {
            PsiphonNativeWorkerGate.release()
        }
    }

    @Test fun duplicateReleaseMustNotClearSuccessorNativeWorker() {
        assertTrue(PsiphonNativeWorkerGate.acquire { })
        PsiphonNativeWorkerGate.release()
        assertTrue(PsiphonNativeWorkerGate.acquire { })
        try {
            // A late duplicate callback from an earlier worker.
            PsiphonNativeWorkerGate.release()
            val unexpected = PsiphonNativeWorkerGate.acquire { }
            if (unexpected) PsiphonNativeWorkerGate.release()
            assertFalse("Old completion opened a successor's JNI lease", unexpected)
        } finally {
            PsiphonNativeWorkerGate.release()
        }
    }

    @Test fun concurrentWorkerStartRequestsAreCoalesced() {
        val start = CountDownLatch(1)
        val done = CountDownLatch(16)
        val accepted = AtomicInteger()
        repeat(16) {
            Thread {
                start.await()
                if (PsiphonNativeWorkerGate.acquire { }) accepted.incrementAndGet()
                done.countDown()
            }.start()
        }
        start.countDown()
        done.await()
        assertEquals(1, accepted.get())
        PsiphonNativeWorkerGate.release()
    }
}
