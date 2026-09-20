package com.phonecodex.app.domain.promise

import com.phonecodex.app.domain.model.ClarificationOption

/**
 * Two exclusive worlds in one sentence must not silently merge.
 *
 * "allow only calculus, monk 4 hrs" → ask. "10 shorts today, never adult" → compose, no ask.
 */
object CompoundIntentLaw {

    private val ALLOW_ONLY = Regex(
        """\b(?:allow\s+only|only\s+allow)\b""",
        RegexOption.IGNORE_CASE
    )
    private val MONK = Regex("""\bmonk(?:\s+mode)?\b""", RegexOption.IGNORE_CASE)
    private val SPLIT = Regex(
        """\s*(?:,|;|\bbut\b|\band then\b|\bsecond(?:ly)?(?:\s+is)?\b)\s*""",
        RegexOption.IGNORE_CASE
    )

    data class Clarification(
        val question: String,
        val understood: String,
        val options: List<ClarificationOption>
    )

    fun clauses(rawText: String): List<String> =
        rawText.split(SPLIT).map { it.trim() }.filter { it.length >= 6 }

    fun isExclusiveClause(text: String): Boolean =
        ALLOW_ONLY.containsMatchIn(text) || MONK.containsMatchIn(text)

    fun needsClarification(rawText: String): Boolean {
        val text = rawText.trim()
        if (text.isBlank()) return false
        if (ALLOW_ONLY.findAll(text).count() >= 2) return true
        return clauses(text).count(::isExclusiveClause) >= 2
    }

    fun exclusiveClauses(rawText: String): List<String> =
        clauses(rawText).filter(::isExclusiveClause)

    fun effectivePromiseText(rawText: String, selectedOptionId: String?): String {
        val id = selectedOptionId?.trim()?.uppercase().orEmpty()
        val text = rawText.trim()
        if (id.isEmpty() || id == "A" || !needsClarification(text)) return text
        val exclusive = exclusiveClauses(text)
        return when (id) {
            "B" -> exclusive.getOrNull(0) ?: text
            "C" -> exclusive.getOrNull(1) ?: exclusive.getOrNull(0) ?: text
            else -> text
        }
    }

    fun clarificationFor(rawText: String): Clarification? {
        if (!needsClarification(rawText)) return null
        val exclusive = exclusiveClauses(rawText)
        val first = exclusive.getOrNull(0)?.take(80) ?: "the first part"
        val second = exclusive.getOrNull(1)?.take(80) ?: "the second part"
        val twoAllowOnly = ALLOW_ONLY.findAll(rawText).count() >= 2
        return Clarification(
            question = "You wrote two different phone rules. Which should Strlix enforce?",
            understood = if (twoAllowOnly) {
                "These look like two exclusive worlds. Pick one, or combine if you meant both."
            } else {
                "I can combine both into one commitment, or keep only one part."
            },
            options = listOf(
                ClarificationOption(
                    id = "A",
                    label = "Both together",
                    description = "One commitment with both parts. The stricter rule wins if they clash.",
                    recommended = !twoAllowOnly,
                    policyPreview = "Run both rules in one session."
                ),
                ClarificationOption(
                    id = "B",
                    label = "Only the first",
                    description = first,
                    recommended = twoAllowOnly,
                    policyPreview = "Enforce only: $first"
                ),
                ClarificationOption(
                    id = "C",
                    label = "Only the second",
                    description = second,
                    recommended = false,
                    policyPreview = "Enforce only: $second"
                )
            )
        )
    }
}
