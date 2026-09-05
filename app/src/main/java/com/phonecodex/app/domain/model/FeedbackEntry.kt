package com.phonecodex.app.domain.model

data class FeedbackEntry(
    val timestampMillis: Long,
    val packageName: String,
    val screenTextPreview: String,
    val originalDecision: String,
    val correctedDecision: String,
    val reason: String
)
