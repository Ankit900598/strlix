package com.phonecodex.app.domain.guardrail

import com.phonecodex.app.domain.model.DecisionType
import com.phonecodex.app.domain.model.GuardrailMatch
import com.phonecodex.app.domain.model.PermanentGuardrail

class PermanentGuardrailEvaluator {

    fun evaluate(
        packageName: String,
        screenText: String,
        guardrails: List<PermanentGuardrail>
    ): GuardrailMatch? {
        val normalizedText = screenText.lowercase()

        guardrails.forEach { guardrail ->
            if (guardrail.blockedPackages.contains(packageName)) {
                return GuardrailMatch(
                    guardrailId = guardrail.id,
                    guardrailName = guardrail.name,
                    decision = DecisionType.BLOCK,
                    matchedStrongSignals = listOf("package:$packageName"),
                    matchedWeakSignals = emptyList(),
                    reason = buildReason(
                        guardrailName = guardrail.name,
                        strongSignals = listOf("package:$packageName"),
                        weakSignals = emptyList()
                    )
                )
            }

            val match = when (guardrail.id) {
                PORN_GUARDRAIL_ID -> evaluatePornGuardrail(guardrail, normalizedText)
                else -> evaluateGenericKeywordGuardrail(guardrail, normalizedText)
            }

            if (match != null) {
                return match
            }
        }

        return null
    }

    private fun evaluatePornGuardrail(
        guardrail: PermanentGuardrail,
        normalizedText: String
    ): GuardrailMatch? {
        val strongMatched = PORN_STRONG_SIGNALS.filter { signal ->
            normalizedText.contains(signal)
        }
        val weakMatched = PORN_WEAK_SIGNALS.mapNotNull { signal ->
            signal.label.takeIf { signal.pattern.containsMatchIn(normalizedText) }
        }

        if (strongMatched.isNotEmpty()) {
            return GuardrailMatch(
                guardrailId = guardrail.id,
                guardrailName = guardrail.name,
                decision = DecisionType.BLOCK,
                matchedStrongSignals = strongMatched,
                matchedWeakSignals = weakMatched,
                reason = buildReason(guardrail.name, strongMatched, weakMatched)
            )
        }

        if (weakMatched.size >= 2) {
            return GuardrailMatch(
                guardrailId = guardrail.id,
                guardrailName = guardrail.name,
                decision = DecisionType.BLOCK,
                matchedStrongSignals = emptyList(),
                matchedWeakSignals = weakMatched,
                reason = buildReason(guardrail.name, emptyList(), weakMatched)
            )
        }

        if (weakMatched.size == 1) {
            return GuardrailMatch(
                guardrailId = guardrail.id,
                guardrailName = guardrail.name,
                decision = DecisionType.WARN,
                matchedStrongSignals = emptyList(),
                matchedWeakSignals = weakMatched,
                reason = buildReason(guardrail.name, emptyList(), weakMatched)
            )
        }

        return null
    }

    private fun evaluateGenericKeywordGuardrail(
        guardrail: PermanentGuardrail,
        normalizedText: String
    ): GuardrailMatch? {
        val matchedKeywords = guardrail.blockedKeywords.filter { keyword ->
            normalizedText.contains(keyword)
        }

        if (matchedKeywords.isEmpty()) {
            return null
        }

        return GuardrailMatch(
            guardrailId = guardrail.id,
            guardrailName = guardrail.name,
            decision = DecisionType.BLOCK,
            matchedStrongSignals = matchedKeywords,
            matchedWeakSignals = emptyList(),
            reason = buildReason(guardrail.name, matchedKeywords, emptyList())
        )
    }

    private fun buildReason(
        guardrailName: String,
        strongSignals: List<String>,
        weakSignals: List<String>
    ): String {
        val matchedParts = mutableListOf<String>()
        if (strongSignals.isNotEmpty()) {
            matchedParts.add("strong: ${strongSignals.joinToString(", ")}")
        }
        if (weakSignals.isNotEmpty()) {
            matchedParts.add("weak: ${weakSignals.joinToString(", ")}")
        }

        val matchedLabel = matchedParts.joinToString("; ")
        return "Permanent guardrail: $guardrailName (matched: $matchedLabel)"
    }

    companion object {
        private const val PORN_GUARDRAIL_ID = "porn_guardrail"

        private val PORN_STRONG_SIGNALS = listOf(
            "porn",
            "xxx",
            "pornhub",
            "xvideos",
            "xhamster",
            "onlyfans",
            "redtube",
            "xnxx"
        )

        private data class WeakSignal(
            val label: String,
            val pattern: Regex
        )

        private val PORN_WEAK_SIGNALS = listOf(
            WeakSignal("sex", Regex("\\bsex\\b")),
            WeakSignal("nude", Regex("\\bnude\\b")),
            WeakSignal("adult", Regex("\\badult\\b"))
        )
    }
}
