package com.phonecodex.app.domain.enforcement

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class EnforcementEventGateTest {

    @Test
    fun contentChanged_isDebounced_stateChanged_isNot() {
        assertTrue(EnforcementEventGate.shouldDebounceContentChanged(true))
        assertFalse(EnforcementEventGate.shouldDebounceContentChanged(false))
    }

    @Test
    fun blankText_skipsContentAndAi() {
        assertTrue(EnforcementEventGate.shouldSkipContentAndAi(""))
        assertTrue(EnforcementEventGate.shouldSkipContentAndAi("   "))
        assertFalse(EnforcementEventGate.shouldSkipContentAndAi("Hide player controls YouTube"))
    }

    @Test
    fun debugPackageWrite_throttlesSamePackage() {
        assertTrue(
            EnforcementEventGate.shouldWriteDebugPackageDetection(
                packageName = "com.android.chrome",
                lastWrittenPackage = null,
                lastWrittenAtMillis = 0L,
                nowMillis = 1000L
            )
        )
        assertFalse(
            EnforcementEventGate.shouldWriteDebugPackageDetection(
                packageName = "com.android.chrome",
                lastWrittenPackage = "com.android.chrome",
                lastWrittenAtMillis = 1000L,
                nowMillis = 1500L,
                throttleMs = 2000L
            )
        )
        assertTrue(
            EnforcementEventGate.shouldWriteDebugPackageDetection(
                packageName = "com.android.chrome",
                lastWrittenPackage = "com.android.chrome",
                lastWrittenAtMillis = 1000L,
                nowMillis = 3500L,
                throttleMs = 2000L
            )
        )
        assertTrue(
            EnforcementEventGate.shouldWriteDebugPackageDetection(
                packageName = "com.google.android.youtube",
                lastWrittenPackage = "com.android.chrome",
                lastWrittenAtMillis = 1000L,
                nowMillis = 1100L,
                throttleMs = 2000L
            )
        )
    }
}
