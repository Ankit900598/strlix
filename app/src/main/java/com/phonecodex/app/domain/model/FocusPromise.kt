package com.phonecodex.app.domain.model

/**
 * Local preview of a compiled promise.
 *
 * [sessionDurationMinutes] is how long the commitment runs.
 * [contentRules] are intra-app / length / surface rules — never confuse them with session length.
 * [clarificationQuestion] non-null means: do not start enforcement yet.
 *
 * Human summary lists are for the confirmation card (no package names).
 * When Azure Promise Compiler lands, map its JSON into this type and keep the UI unchanged.
 */
data class FocusPromise(
    val rawText: String,
    val sessionDurationMinutes: Int,
    val allowedKeywords: List<String>,
    val blockedKeywords: List<String>,
    val strictness: StrictnessLevel,
    val suggestedAppRules: List<AppRule>,
    val contentRules: List<ContentRule> = emptyList(),
    val clarificationQuestion: String? = null,
    val warnings: List<String> = emptyList(),
    val allowedSummaries: List<String> = emptyList(),
    val blockedSummaries: List<String> = emptyList(),
    val conditionalSummaries: List<String> = emptyList()
) {
    /** Alias used by older call sites that meant session duration. */
    val durationMinutes: Int
        get() = sessionDurationMinutes

    val needsClarification: Boolean
        get() = !clarificationQuestion.isNullOrBlank()

    /** Product alias for warnings shown on the confirmation card. */
    val cautionMessages: List<String>
        get() = warnings

    /** Alias for content duration / surface rules. */
    val contentDurationRules: List<ContentRule>
        get() = contentRules
}
