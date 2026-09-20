package com.phonecodex.app.domain.enforcement

/**
 * Deterministic usage quota (clock C / Shorts count).
 * First matching events count once each (by signature); only after the limit → BLOCK.
 */
enum class QuotaVerdict {
    /** No quota configured for this promise. */
    NONE,
    /** Matching event counted; still under limit. */
    ALLOW_UNDER_LIMIT,
    /** Limit reached / exceeded — block further matching events. */
    BLOCK_OVER_LIMIT,
    /** Duplicate signature within the session — do not re-count. */
    DUPLICATE_IGNORED
}

data class QuotaEvaluation(
    val verdict: QuotaVerdict,
    val count: Int,
    val limit: Int,
    val key: String
)

class QuotaEnforcementGate {

    private val countedSignatures = mutableMapOf<String, MutableSet<String>>()
    private val counts = mutableMapOf<String, Int>()

    fun reset() {
        countedSignatures.clear()
        counts.clear()
    }

    /**
     * @param quotaKey e.g. "shorts" or "entertainment_events"
     * @param eventSignature stable id for this matching event (package + text hash)
     * @param limit max allowed matching events before block (inclusive allow while count < limit)
     */
    fun evaluate(
        quotaKey: String,
        eventSignature: String,
        limit: Int
    ): QuotaEvaluation {
        if (limit <= 0) {
            return QuotaEvaluation(QuotaVerdict.NONE, 0, limit, quotaKey)
        }

        val signatures = countedSignatures.getOrPut(quotaKey) { linkedSetOf() }
        val current = counts.getOrDefault(quotaKey, 0)

        if (eventSignature in signatures) {
            val verdict = if (current >= limit) {
                QuotaVerdict.BLOCK_OVER_LIMIT
            } else {
                QuotaVerdict.DUPLICATE_IGNORED
            }
            return QuotaEvaluation(verdict, current, limit, quotaKey)
        }

        // First time we see this matching event — count it.
        signatures += eventSignature
        val next = current + 1
        counts[quotaKey] = next

        val verdict = if (next > limit) {
            QuotaVerdict.BLOCK_OVER_LIMIT
        } else {
            QuotaVerdict.ALLOW_UNDER_LIMIT
        }
        return QuotaEvaluation(verdict, next, limit, quotaKey)
    }

    fun currentCount(quotaKey: String): Int = counts.getOrDefault(quotaKey, 0)

    companion object {
        const val KEY_SHORTS = "shorts"

        fun parseShortsQuotaLimit(goal: String): Int? = ShortFormLanguage.parseLimit(goal)
    }
}
