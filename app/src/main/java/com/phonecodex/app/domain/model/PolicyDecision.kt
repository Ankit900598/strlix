package com.phonecodex.app.domain.model

data class PolicyDecision(
    val decision: DecisionType,
    val confidence: Double,
    val reason: String,
    val riskLevel: RiskLevel,
    val source: DecisionSource
)
