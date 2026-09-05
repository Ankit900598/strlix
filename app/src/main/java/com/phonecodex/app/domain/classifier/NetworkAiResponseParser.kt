package com.phonecodex.app.domain.classifier

import com.phonecodex.app.domain.model.DecisionType
import org.json.JSONObject

/**
 * Parses POST /classify JSON from PhoneCodex backend (Azure OpenAI v04).
 */
object NetworkAiResponseParser {

    private val SUPPORTED_DECISIONS = setOf(
        DecisionType.ALLOW,
        DecisionType.WARN,
        DecisionType.BLOCK,
        DecisionType.LOCK
    )

    fun parse(raw: String): ContentClassification? {
        return try {
            val json = JSONObject(raw)
            val decisionName = json.optString("decision", "")
            val decision = runCatching { DecisionType.valueOf(decisionName) }.getOrNull()
            if (decision !in SUPPORTED_DECISIONS) {
                return null
            }

            val metaJson = json.optJSONObject("meta")
            val meta = metaJson?.let {
                ClassificationBackendMeta(
                    provider = it.optString("provider").ifBlank { null },
                    deployment = it.optString("deployment").ifBlank { null },
                    promptVersion = it.optString("promptVersion").ifBlank { null },
                    latencyMs = if (it.has("latencyMs")) it.optLong("latencyMs") else null
                )
            }

            ContentClassification(
                decision = decision!!,
                confidence = json.optDouble("confidence", 0.0),
                reason = json.optString("reason", "No reason provided."),
                source = AiConfidenceGate.NETWORK_AI_SOURCE,
                reasonCategory = json.optString("reasonCategory").ifBlank { null },
                wouldEscalate = json.optBoolean("would_escalate", false),
                backendMeta = meta
            )
        } catch (_: Exception) {
            null
        }
    }
}
