package com.phonecodex.app.domain.guardrail

import com.phonecodex.app.domain.model.DecisionType
import com.phonecodex.app.domain.model.PermanentGuardrail
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Test

class PermanentGuardrailEvaluatorTest {

    private val evaluator = PermanentGuardrailEvaluator()

    @Test
    fun oneWeakPornSignal_returnsWarnNotBlock() {
        val match = evaluator.evaluate(
            packageName = "com.android.chrome",
            screenText = "This page mentions adult content warnings",
            guardrails = listOf(pornGuardrail())
        )

        assertNotNull(match)
        assertEquals(DecisionType.WARN, match?.decision)
        assertEquals(listOf("adult"), match?.matchedWeakSignals)
    }

    @Test
    fun twoWeakPornSignals_returnBlock() {
        val match = evaluator.evaluate(
            packageName = "com.android.chrome",
            screenText = "adult hot scene description",
            guardrails = listOf(pornGuardrail())
        )

        assertNotNull(match)
        assertEquals(DecisionType.BLOCK, match?.decision)
        assertEquals(listOf("adult", "hot"), match?.matchedWeakSignals)
    }

    @Test
    fun strongPornSignal_returnsBlock() {
        val match = evaluator.evaluate(
            packageName = "com.android.chrome",
            screenText = "visit xvideos now",
            guardrails = listOf(pornGuardrail())
        )

        assertNotNull(match)
        assertEquals(DecisionType.BLOCK, match?.decision)
        assertEquals(listOf("xvideos"), match?.matchedStrongSignals)
    }

    @Test
    fun noPornSignals_returnsNull() {
        val match = evaluator.evaluate(
            packageName = "com.android.chrome",
            screenText = "DSA lecture notes and compiler design",
            guardrails = listOf(pornGuardrail())
        )

        assertNull(match)
    }

    private fun pornGuardrail(): PermanentGuardrail {
        return PermanentGuardrail(
            id = "porn_guardrail",
            name = "Block Porn",
            enabled = true,
            blockedKeywords = emptySet(),
            blockedPackages = emptySet(),
            createdAtMillis = 0L,
            expiresAtMillis = null
        )
    }
}
