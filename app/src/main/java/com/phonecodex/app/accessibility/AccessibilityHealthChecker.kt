package com.phonecodex.app.accessibility

import android.content.Context
import android.provider.Settings

object AccessibilityHealthChecker {

    const val PHONECODEX_ACCESSIBILITY_SERVICE_ID =
        "com.phonecodex.app/.accessibility.PhoneCodexAccessibilityService"
    private const val PHONECODEX_ACCESSIBILITY_SERVICE_FULL_ID =
        "com.phonecodex.app/com.phonecodex.app.accessibility.PhoneCodexAccessibilityService"

    fun isPhoneCodexAccessibilityEnabled(context: Context): Boolean {
        val enabledServices = Settings.Secure.getString(
            context.contentResolver,
            Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES
        )
        return isServiceEnabledInSettings(enabledServices)
    }

    fun isServiceEnabledInSettings(
        enabledServices: String?,
        serviceId: String = PHONECODEX_ACCESSIBILITY_SERVICE_ID
    ): Boolean {
        if (enabledServices.isNullOrBlank()) return false

        return enabledServices.split(':')
            .any { component ->
                component.equals(serviceId, ignoreCase = true) ||
                    component.equals(PHONECODEX_ACCESSIBILITY_SERVICE_FULL_ID, ignoreCase = true)
            }
    }
}
