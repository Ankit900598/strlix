package com.phonecodex.app.domain.model

/**
 * A structured content / surface rule inferred from a natural-language promise.
 *
 * This is the local preview shape. The Azure Promise Compiler will emit a richer policy that
 * maps into the same fields (or replaces [FocusPromise] wholesale) without UI rewrites.
 */
data class ContentRule(
    val appLabel: String?,
    val packageName: String?,
    /** Human surface: video, shorts, reels, feed, messages, search, playlist, any */
    val surface: String,
    /** Aligned with commitment_policy_schema content types where possible. */
    val contentType: String,
    /** gt / gte / lt / lte / eq, or null when not a threshold rule. */
    val operator: String?,
    val value: Int?,
    /** minutes / hours / count, or null. */
    val unit: String?,
    val action: ContentRuleAction
) {
    fun describe(): String {
        val app = appLabel ?: "App"
        val threshold = if (operator != null && value != null && unit != null) {
            " ${operatorLabel(operator)} $value $unit"
        } else {
            ""
        }
        val surfaceBit = if (surface == "any") "" else " $surface"
        return "$app$surfaceBit$threshold → ${action.name}"
    }

    private fun operatorLabel(op: String): String = when (op) {
        "gt" -> ">"
        "gte" -> "≥"
        "lt" -> "<"
        "lte" -> "≤"
        "eq" -> "="
        else -> op
    }
}

enum class ContentRuleAction {
    ALLOW,
    BLOCK,
    WARN,
    AI_DECIDE
}
