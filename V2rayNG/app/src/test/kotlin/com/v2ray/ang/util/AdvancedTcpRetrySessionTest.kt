package com.v2ray.ang.util

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import org.junit.Assert.*
import org.junit.Test
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicReference

class AdvancedTcpRetrySessionTest {
    private val target = AdvancedRetryTarget("guid", "rev", "example.invalid", 443)
    private val settings = AdvancedRetrySettings(2, 3, 1)

    @Test fun realWorkerLoopCompletesThreePassesWithOwnedTickets() = runBlocking {
        val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
        val latest = AtomicReference<AdvancedTcpRetryReport?>()
        try {
            val session = AdvancedTcpRetrySession(scope, "session", listOf(target), settings,
                RetryPassMode.ALL_EVERY_PASS, 1_000,
                currentRevision = { "rev" }, networkStillCurrent = { true },
                onReport = { latest.set(it) },
                testConnect = { _, _ -> 1L },
            )
            session.start()
            withTimeout(5_000) {
                while (latest.get()?.snapshot?.phase != RetryRunPhase.FINISHED) delay(25)
            }
            val finished = requireNotNull(latest.get())
            assertEquals(3L, finished.snapshot.attemptsCompleted)
            assertEquals(0L, finished.snapshot.failedAttempts)
            assertEquals(1, finished.snapshot.succeededProfiles)
            assertFalse(session.stop())
        } finally {
            scope.cancel()
        }
    }

    @Test fun stopRejectsBlockedSocketCompletionEvenAfterItReturns() = runBlocking {
        val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
        val entered = CountDownLatch(1)
        val release = CountDownLatch(1)
        try {
            val session = AdvancedTcpRetrySession(scope, "late", listOf(target), settings,
                RetryPassMode.ALL_EVERY_PASS, 1_000,
                currentRevision = { "rev" }, networkStillCurrent = { true },
                onReport = {},
                testConnect = { _, _ ->
                    entered.countDown()
                    release.await(3, TimeUnit.SECONDS)
                    1L
                },
            )
            session.start()
            assertTrue("The fake TCP connect must block before Stop", entered.await(2, TimeUnit.SECONDS))
            assertTrue(session.stop())
            release.countDown()
            delay(100)
            assertEquals(RetryRunPhase.STOPPED, session.snapshot().snapshot.phase)
            assertEquals(0L, session.snapshot().snapshot.attemptsCompleted)
        } finally {
            release.countDown()
            scope.cancel()
        }
    }

    @Test fun editedProfileRevisionTurnsSuccessfulSocketConnectIntoUnknown() = runBlocking {
        val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
        val latest = AtomicReference<AdvancedTcpRetryReport?>()
        val revision = AtomicReference("rev")
        try {
            val session = AdvancedTcpRetrySession(scope, "edited", listOf(target),
                AdvancedRetrySettings(1, 1, 1), RetryPassMode.ALL_EVERY_PASS, 1_000,
                currentRevision = { revision.get() }, networkStillCurrent = { true },
                onReport = { latest.set(it) },
                testConnect = { _, _ -> revision.set("rev-updated"); 1L },
            )
            session.start()
            withTimeout(5_000) {
                while (latest.get()?.snapshot?.phase != RetryRunPhase.FINISHED) delay(25)
            }
            val summary = requireNotNull(latest.get())
            assertEquals(1L, summary.snapshot.unknownAttempts)
            assertEquals(0L, summary.snapshot.failedAttempts)
            assertEquals(0, summary.snapshot.succeededProfiles)
        } finally {
            scope.cancel()
        }
    }

    @Test fun aHandoverIsUnknownNotEligibleTcpFailure() = runBlocking {
        val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
        val latest = AtomicReference<AdvancedTcpRetryReport?>()
        val current = AtomicBoolean(true)
        try {
            val session = AdvancedTcpRetrySession(scope, "handover", listOf(target),
                AdvancedRetrySettings(2, 1, 1), RetryPassMode.ALL_EVERY_PASS, 1_000,
                currentRevision = { "rev" }, networkStillCurrent = { current.get() },
                onReport = { latest.set(it) },
                testConnect = { _, _ ->
                    current.set(false)
                    1L
                },
            )
            session.start()
            withTimeout(5_000) {
                while (latest.get()?.snapshot?.phase != RetryRunPhase.FINISHED) delay(25)
            }
            val summary = requireNotNull(latest.get())
            assertEquals(2L, summary.snapshot.unknownAttempts)
            assertEquals(0L, summary.snapshot.failedAttempts)
            assertEquals(0, summary.snapshot.succeededProfiles)
        } finally {
            scope.cancel()
        }
    }
}
