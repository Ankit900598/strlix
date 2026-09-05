package com.phonecodex.app.domain.protection

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ProtectionViolationPolicyTest {

    @Test
    fun shouldRecordViolation_allowsFirstViolation() {
        assertTrue(
            ProtectionViolationPolicy.shouldRecordViolation(
                lastViolationMillis = 0L,
                nowMillis = 1_000L
            )
        )
    }

    @Test
    fun shouldRecordViolation_blocksWithinCooldown() {
        assertFalse(
            ProtectionViolationPolicy.shouldRecordViolation(
                lastViolationMillis = 1_000L,
                nowMillis = 30_000L
            )
        )
    }

    @Test
    fun shouldRecordViolation_allowsAfterCooldown() {
        assertTrue(
            ProtectionViolationPolicy.shouldRecordViolation(
                lastViolationMillis = 1_000L,
                nowMillis = 61_500L
            )
        )
    }
}
