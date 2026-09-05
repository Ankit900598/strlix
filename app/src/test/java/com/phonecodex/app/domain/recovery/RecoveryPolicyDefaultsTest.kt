package com.phonecodex.app.domain.recovery

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class RecoveryPolicyDefaultsTest {

    @Test
    fun default_matchesProductPolicy() {
        val policy = RecoveryPolicyDefaults.default()

        assertEquals(10, policy.mistakeWindowMinutes)
        assertEquals(24, policy.cooldownHours)
        assertFalse(policy.trustedAdminRequired)
        assertFalse(policy.breakFeeEnabled)
        assertNull(policy.breakFeeAmountLabel)
        assertTrue(policy.emergencyOverrideAllowed)
    }
}
