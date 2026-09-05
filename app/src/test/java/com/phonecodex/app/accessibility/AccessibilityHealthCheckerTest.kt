package com.phonecodex.app.accessibility

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AccessibilityHealthCheckerTest {

    @Test
    fun isServiceEnabledInSettings_returnsFalseWhenNull() {
        assertFalse(AccessibilityHealthChecker.isServiceEnabledInSettings(null))
    }

    @Test
    fun isServiceEnabledInSettings_returnsFalseWhenBlank() {
        assertFalse(AccessibilityHealthChecker.isServiceEnabledInSettings("   "))
    }

    @Test
    fun isServiceEnabledInSettings_returnsTrueWhenServicePresent() {
        val enabledServices =
            "com.other.app/.OtherService:" +
                AccessibilityHealthChecker.PHONECODEX_ACCESSIBILITY_SERVICE_ID

        assertTrue(AccessibilityHealthChecker.isServiceEnabledInSettings(enabledServices))
    }

    @Test
    fun isServiceEnabledInSettings_returnsFalseWhenOnlyOtherServicesPresent() {
        val enabledServices =
            "com.other.app/.OtherService:com.example/.ExampleService"

        assertFalse(AccessibilityHealthChecker.isServiceEnabledInSettings(enabledServices))
    }

    @Test
    fun isServiceEnabledInSettings_matchesCaseInsensitively() {
        val enabledServices =
            AccessibilityHealthChecker.PHONECODEX_ACCESSIBILITY_SERVICE_ID.uppercase()

        assertTrue(AccessibilityHealthChecker.isServiceEnabledInSettings(enabledServices))
    }
}
