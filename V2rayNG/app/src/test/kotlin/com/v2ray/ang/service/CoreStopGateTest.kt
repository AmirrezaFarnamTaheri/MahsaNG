package com.v2ray.ang.service

import org.junit.Test
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue

class CoreStopGateTest {
    @Test fun stopBlocksStartUntilNativeCleanupCompletes() {
        val gate = CoreStopGate()
        val token = gate.beginStop()!!
        assertFalse(gate.requestStart())
        assertFalse(gate.canResume(token))
        val restart = gate.completeStop(token, success = true)!!
        assertTrue(gate.canResume(restart))
        assertTrue(gate.requestStart())
    }

    @Test fun stoppingStateRemainsVisibleUntilAsyncStopCompletes() {
        val gate = CoreStopGate()
        assertFalse(gate.isStopping())
        val token = gate.beginStop()!!
        assertTrue(gate.isStopping())
        assertEquals(null, gate.beginStop())
        assertTrue(gate.isStopping())
        gate.completeStop(token, success = true)
        assertFalse(gate.isStopping())
    }

    @Test fun duplicateNativeStopPreservesDeferredRestartWithoutSchedulingSecondStop() {
        val gate = CoreStopGate()
        val token = gate.beginStop()!!
        assertFalse(gate.requestStart())
        assertEquals(null, gate.beginStop())
        assertTrue(gate.completeStop(token, success = true) != null)
    }

    @Test fun nativeStopFailureDoesNotAuthorizeRestart() {
        val gate = CoreStopGate()
        val token = gate.beginStop()!!
        assertFalse(gate.requestStart())
        assertEquals(null, gate.completeStop(token, success = false))
        assertTrue(gate.requestStart())
    }

    @Test fun newStopInvalidatesPreviouslyQueuedRestart() {
        val gate = CoreStopGate()
        val token = gate.beginStop()!!
        assertFalse(gate.requestStart())
        val restartToken = gate.completeStop(token, success = true)!!
        assertEquals(null, gate.beginStop()?.let { second ->
            assertFalse(gate.canResume(restartToken))
            gate.completeStop(second, success = true)
        })
        assertFalse(gate.canResume(restartToken))
    }

    @Test fun oldCompletionIsIgnoredAfterSuccess() {
        val gate = CoreStopGate()
        val token = gate.beginStop()!!
        assertEquals(null, gate.completeStop(token, success = true))
        assertEquals(null, gate.completeStop(token, success = true))
        assertTrue(gate.requestStart())
    }
}
