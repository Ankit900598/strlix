package com.phonecodex.app.domain.classifier

import com.phonecodex.app.domain.model.DecisionType
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class AiConfidenceGateTest {

    private val gate = AiConfidenceGate()

    @Test
    fun openAiBlockBelowThreshold_downgradesToWarn() {
        val result = gate.apply(
            ContentClassification(
                decision = DecisionType.BLOCK,
                confidence = 0.7,
                reason = "Not study related",
                source = AiConfidenceGate.NETWORK_AI_SOURCE
            )
        )

        assertEquals(DecisionType.WARN, result.decision)
        assertTrue(result.reason.startsWith("Downgraded from BLOCK:"))
    }

    @Test
    fun openAiWarnBelowThreshold_downgradesToAllow() {
        val result = gate.apply(
            ContentClassification(
                decision = DecisionType.WARN,
                confidence = 0.5,
                reason = "Unclear screen",
                source = AiConfidenceGate.NETWORK_AI_SOURCE
            )
        )

        assertEquals(DecisionType.ALLOW, result.decision)
        assertTrue(result.reason.startsWith("Downgraded from WARN:"))
    }

    @Test
    fun nonOpenAiSource_isUnchanged() {
        val original = ContentClassification(
            decision = DecisionType.BLOCK,
            confidence = 0.5,
            reason = "Fake AI block",
            source = "fake_ai"
        )

        val result = gate.apply(original)

        assertEquals(original, result)
    }
}
