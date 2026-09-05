package com.phonecodex.app.domain.recovery

import com.phonecodex.app.domain.model.RecoveryPolicy

object RecoveryPolicyDefaults {

    const val MISTAKE_WINDOW_MINUTES = 10
    const val COOLDOWN_HOURS = 24
    const val TRUSTED_ADMIN_REQUIRED = false
    const val BREAK_FEE_ENABLED = false
    const val EMERGENCY_OVERRIDE_ALLOWED = true

    fun default(): RecoveryPolicy {
        return RecoveryPolicy(
            mistakeWindowMinutes = MISTAKE_WINDOW_MINUTES,
            cooldownHours = COOLDOWN_HOURS,
            trustedAdminRequired = TRUSTED_ADMIN_REQUIRED,
            breakFeeEnabled = BREAK_FEE_ENABLED,
            breakFeeAmountLabel = null,
            emergencyOverrideAllowed = EMERGENCY_OVERRIDE_ALLOWED
        )
    }
}
