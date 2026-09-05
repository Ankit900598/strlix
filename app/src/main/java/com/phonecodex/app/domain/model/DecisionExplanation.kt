package com.phonecodex.app.domain.model

data class DecisionExplanation(
    val decision: String,
    val reason: String,
    val source: String,
    val confidence: Double? = null,
    val matchedSignals: List<String> = emptyList()
)
