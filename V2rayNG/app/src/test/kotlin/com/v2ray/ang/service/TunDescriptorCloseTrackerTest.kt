package com.v2ray.ang.service

import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** Fake descriptor identities: JNI/TUN closure is not exercised by these tests. */
class TunDescriptorCloseTrackerTest {
    @Test fun stopWithoutEstablishedTunCanCompleteOnlyAfterStopWasRequested() {
        val tracker = TunDescriptorCloseTracker<Any>()
        assertFalse(tracker.awaitClosed(25L))
        assertTrue(tracker.requestStop().isEmpty())
        assertTrue(tracker.awaitClosed(25L))
        assertFalse(tracker.beginEstablish())
    }

    @Test fun closeRequestIsNotEvidenceThatDescriptorClosed() {
        val tracker = TunDescriptorCloseTracker<Any>()
        val tun = Any()
        assertTrue(tracker.beginEstablish())
        assertTrue(tracker.registered(tun))
        assertEquals(listOf(tun), tracker.requestStop())
        assertFalse(tracker.awaitClosed(25L))
        assertTrue(tracker.closeReturned(tun))
        assertTrue(tracker.awaitClosed(25L))
    }

    @Test fun failedCloseCannotMarkDescriptorCompleteOrAllowNewSession() {
        val tracker = TunDescriptorCloseTracker<Any>()
        val tun = Any()
        assertTrue(tracker.beginEstablish())
        assertTrue(tracker.registered(tun))
        tracker.requestStop()
        // The owner must not call closeReturned when ParcelFileDescriptor.close throws.
        assertFalse(tracker.awaitClosed(25L))
        assertFalse(tracker.beginEstablish())
        assertEquals(listOf(tun), tracker.requestStop())
    }

    @Test fun establishmentStillInFlightKeepsStopIncomplete() {
        val tracker = TunDescriptorCloseTracker<Any>()
        assertTrue(tracker.beginEstablish())
        assertTrue(tracker.requestStop().isEmpty())
        assertFalse(tracker.awaitClosed(25L))
        val lateTun = Any()
        assertFalse(tracker.registered(lateTun))
        assertFalse(tracker.awaitClosed(25L))
        assertTrue(tracker.closeReturned(lateTun))
        assertTrue(tracker.awaitClosed(25L))
    }

    @Test fun establishmentFailureMustBeAccountedAfterStop() {
        val tracker = TunDescriptorCloseTracker<Any>()
        assertTrue(tracker.beginEstablish())
        tracker.requestStop()
        assertFalse(tracker.awaitClosed(25L))
        tracker.establishFailed()
        assertTrue(tracker.awaitClosed(25L))
    }

    @Test fun replacingOneTunCannotEraseEarlierFailedClosure() {
        val tracker = TunDescriptorCloseTracker<Any>()
        val first = Any()
        val second = Any()
        assertTrue(tracker.beginEstablish())
        assertTrue(tracker.registered(first))
        assertTrue(tracker.beginEstablish())
        assertTrue(tracker.registered(second))
        tracker.requestStop()
        assertTrue(tracker.closeReturned(second))
        assertFalse(tracker.awaitClosed(25L))
        assertTrue(tracker.closeReturned(first))
        assertTrue(tracker.awaitClosed(25L))
    }

    @Test fun descriptorEqualityIsNotOwnership() {
        data class FakeTun(val number: Int)
        val tracker = TunDescriptorCloseTracker<FakeTun>()
        val actual = FakeTun(42)
        assertTrue(tracker.beginEstablish())
        assertTrue(tracker.registered(actual))
        tracker.requestStop()
        assertFalse(tracker.closeReturned(FakeTun(42)))
        assertFalse(tracker.awaitClosed(25L))
        assertTrue(tracker.closeReturned(actual))
        assertTrue(tracker.awaitClosed(25L))
    }

    @Test fun repeatedStopCannotReopenOrDiscardOutstandingDescriptors() {
        val tracker = TunDescriptorCloseTracker<Any>()
        val tun = Any()
        assertTrue(tracker.beginEstablish())
        assertTrue(tracker.registered(tun))
        assertEquals(listOf(tun), tracker.requestStop())
        assertEquals(listOf(tun), tracker.requestStop())
        assertFalse(tracker.beginEstablish())
        assertFalse(tracker.awaitClosed(25L))
        assertTrue(tracker.closeReturned(tun))
        assertTrue(tracker.awaitClosed(25L))
    }

    @Test fun waitingThreadCanObserveClosureReportedByServiceOwner() {
        val tracker = TunDescriptorCloseTracker<Any>()
        val tun = Any()
        assertTrue(tracker.beginEstablish())
        assertTrue(tracker.registered(tun))
        tracker.requestStop()
        val start = CountDownLatch(1)
        val closer = Thread {
            start.await()
            tracker.closeReturned(tun)
        }
        closer.start()
        try {
            start.countDown()
            assertTrue(tracker.awaitClosed(1_000L))
        } finally {
            closer.join(1_000L)
        }
    }

    @Test fun interruptedWaitFailsClosedAndPreservesInterruptFlag() {
        val tracker = TunDescriptorCloseTracker<Any>()
        val tun = Any()
        assertTrue(tracker.beginEstablish())
        assertTrue(tracker.registered(tun))
        tracker.requestStop()
        Thread.currentThread().interrupt()
        try {
            assertFalse(tracker.awaitClosed(250L))
            assertTrue(Thread.currentThread().isInterrupted)
        } finally {
            Thread.interrupted()
            tracker.closeReturned(tun)
        }
    }

    @Test fun invalidOrUnboundedWaitsAreNeverProofOfClosure() {
        val tracker = TunDescriptorCloseTracker<Any>()
        tracker.requestStop()
        assertFalse(tracker.awaitClosed(0L))
        assertFalse(tracker.awaitClosed(-1L))
        assertFalse(tracker.awaitClosed(Long.MAX_VALUE))
        assertTrue(tracker.awaitClosed(25L))
    }
}
