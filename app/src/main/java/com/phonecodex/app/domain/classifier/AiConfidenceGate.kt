package com.phonecodex.app.domain.classifier

import com.phonecodex.app.domain.model.DecisionType

class AiConfidenceGate {

    fun apply(classification: ContentClassification): ContentClassification {
        if (classification.source != NETWORK_AI_SOURCE) {
            return classification
        }

        return when (classification.decision) {
            DecisionType.BLOCK, DecisionType.LOCK -> {
                if (classification.confidence < BLOCK_WARN_THRESHOLD) {
                    classification.copy(
                        decision = DecisionType.WARN,
                        reason = "Downgraded from ${classification.decision}: ${classification.reason}"
                    )
                } else {
                    classification
                }
            }
            DecisionType.WARN -> {
                if (classification.confidence < WARN_ALLOW_THRESHOLD) {
                    classification.copy(
                        decision = DecisionType.ALLOW,
                        reason = "Downgraded from WARN: ${classification.reason}"
                    )
                } else {
                    classification
                }
            }
            else -> classification
        }
    }

    companion object {
        const val NETWORK_AI_SOURCE = "openai_backend"
        private const val BLOCK_WARN_THRESHOLD = 0.80
        private const val WARN_ALLOW_THRESHOLD = 0.65
    }
}
