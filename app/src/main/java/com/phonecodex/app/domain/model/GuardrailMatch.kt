package com.phonecodex.app.domain.model

data class GuardrailMatch(
    val guardrailId: String,
    val guardrailName: String,
    val decision: DecisionType,
    val matchedStrongSignals: List<String>,
    val matchedWeakSignals: List<String>,
    val reason: String
)
