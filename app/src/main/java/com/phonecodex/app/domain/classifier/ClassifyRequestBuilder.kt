package com.phonecodex.app.domain.classifier

import com.phonecodex.app.data.PermanentGuardrailsStore
import com.phonecodex.app.domain.model.FocusSession
import com.phonecodex.app.domain.model.SessionStatus

object ClassifyRequestBuilder {

    fun build(
        packageName: String,
        appLabel: String?,
        screenText: String,
        session: FocusSession,
        enabledGuardrailIds: List<String>
    ): ClassificationRequest {
        val counters = mutableMapOf<String, Int>()
        if (session.attemptCount > 0) {
            counters["attemptCount"] = session.attemptCount
        }

        return ClassificationRequest(
            packageName = packageName,
            appLabel = appLabel?.takeIf { it.isNotBlank() },
            screenText = screenText,
            goal = session.goal,
            strictnessLevel = session.strictness.name,
            activeGuardrails = enabledGuardrailIds.map(::mapGuardrailIdForBackend),
            commitmentType = inferCommitmentType(session.goal, session),
            sessionCounters = counters.takeIf { it.isNotEmpty() },
            limitState = "n/a"
        )
    }

    private fun mapGuardrailIdForBackend(guardrailId: String): String {
        return when (guardrailId) {
            PermanentGuardrailsStore.PORN_GUARDRAIL_ID -> "no_adult_content"
            else -> guardrailId
        }
    }

    private fun inferCommitmentType(goal: String, session: FocusSession): String {
        val normalized = goal.lowercase()
        return when {
            normalized.contains("monk") ||
                normalized.contains("zero fun") ||
                normalized.contains("zero entertainment") -> "monk_mode"
            normalized.contains("no porn") ||
                normalized.contains("1 year") ||
                normalized.contains("guardrail") -> "permanent_guardrail"
            normalized.contains("shorts") &&
                (normalized.contains("allow") || normalized.contains("quota") ||
                    QUOTA_NUMBER_REGEX.containsMatchIn(normalized)) -> "quota_entertainment"
            session.status == SessionStatus.LOCKED -> "focus_session"
            else -> "focus_session"
        }
    }

    private val QUOTA_NUMBER_REGEX = Regex("\\d+")
}
