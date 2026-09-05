package com.phonecodex.app.domain.model

data class FocusPromise(
    val rawText: String,
    val durationMinutes: Int,
    val allowedKeywords: List<String>,
    val blockedKeywords: List<String>,
    val strictness: StrictnessLevel,
    val suggestedAppRules: List<AppRule>
)
