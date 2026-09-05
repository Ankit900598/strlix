package com.phonecodex.app.domain.model

data class StudyWorldSettings(
    val durationMinutes: Int,
    val lockAttemptThreshold: Int,
    val blockAttemptCooldownMinutes: Int
)
