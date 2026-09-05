package com.phonecodex.app.domain.model

data class FocusSession(
    val id: String,
    val worldId: String,
    val goal: String,
    val startTimeMillis: Long,
    val deadlineMillis: Long,
    val status: SessionStatus,
    val attemptCount: Int,
    val strictness: StrictnessLevel
)
