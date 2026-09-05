package com.phonecodex.app.domain.model

data class RecoveryPolicy(
    val mistakeWindowMinutes: Int,
    val cooldownHours: Int,
    val trustedAdminRequired: Boolean,
    val breakFeeEnabled: Boolean,
    val breakFeeAmountLabel: String?,
    val emergencyOverrideAllowed: Boolean
)
