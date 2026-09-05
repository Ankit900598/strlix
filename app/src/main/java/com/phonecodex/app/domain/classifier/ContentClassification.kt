package com.phonecodex.app.domain.classifier

import com.phonecodex.app.domain.model.DecisionType

data class ContentClassification(
    val decision: DecisionType,
    val confidence: Double,
    val reason: String,
    val source: String,
    val reasonCategory: String? = null,
    val wouldEscalate: Boolean = false,
    val backendMeta: ClassificationBackendMeta? = null
)
