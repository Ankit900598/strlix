package com.phonecodex.app.domain.promise

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PromiseUnderstandingRequestGateTest {

    @Test
    fun editingPromiseInvalidatesInFlightCompilerResult() {
        val gate = PromiseUnderstandingRequestGate()
        val request = gate.begin()

        gate.invalidate()

        assertFalse(gate.isCurrent(request))
    }

    @Test
    fun latestRequestCanApplyItsResult() {
        val gate = PromiseUnderstandingRequestGate()
        gate.begin()
        gate.invalidate()

        val latestRequest = gate.begin()

        assertTrue(gate.isCurrent(latestRequest))
    }
}
