package com.phonecodex.app.ui.home

import com.phonecodex.app.data.StudyWorldSettingsStore
import com.phonecodex.app.domain.model.AppRule
import com.phonecodex.app.domain.model.AppRuleBehavior
import com.phonecodex.app.domain.model.ContentRule
import com.phonecodex.app.domain.model.ContentRuleAction
import com.phonecodex.app.domain.model.FocusPromise
import com.phonecodex.app.domain.model.StrictnessLevel

/**
 * Human-readable confirmation of a compiled promise. Presentation only.
 */
internal data class PromiseUnderstanding(
    val promiseText: String,
    val durationMinutes: Int,
    val lockAttemptThreshold: Int,
    val sessionTimeLabel: String,
    val allowedLabel: String,
    val blockedLabel: String,
    val conditionalLabel: String?,
    val strictnessLabel: String,
    val driftLabel: String,
    val managedApps: List<String>,
    val clarificationQuestion: String?,
    val cautions: List<String>,
    val canStart: Boolean,
    val source: UnderstandingSource
) {
    val durationLabel: String get() = sessionTimeLabel
    val caution: String? get() = cautions.firstOrNull()
}

internal enum class UnderstandingSource {
    LOCAL_PREVIEW,
    PROMISE_COMPILER
}

internal fun buildPromiseUnderstanding(
    draft: FocusPromise,
    alwaysBlockedLabels: List<String> = emptyList()
): PromiseUnderstanding {
    val threshold = lockAttemptThresholdFor(draft.strictness)

    val allowed = buildList {
        addAll(draft.allowedSummaries)
        if (isEmpty()) {
            addAll(draft.allowedKeywords)
            draft.suggestedAppRules
                .filter {
                    it.behavior == AppRuleBehavior.ALLOW || it.behavior == AppRuleBehavior.AI_DECIDE
                }
                .forEach { add(it.label) }
            draft.contentRules
                .filter { it.action == ContentRuleAction.ALLOW }
                .forEach { add(it.describe()) }
        }
    }

    val blocked = buildList {
        addAll(draft.blockedSummaries)
        if (draft.blockedSummaries.isEmpty()) {
            addAll(draft.blockedKeywords)
            draft.suggestedAppRules
                .filter { it.behavior == AppRuleBehavior.BLOCK }
                .forEach { add(it.label) }
            draft.contentRules
                .filter { it.action == ContentRuleAction.BLOCK }
                .forEach { add(it.describe()) }
        }
        addAll(alwaysBlockedLabels)
    }

    val conditional = draft.conditionalSummaries.ifEmpty {
        draft.contentRules
            .filter {
                it.action == ContentRuleAction.AI_DECIDE || it.action == ContentRuleAction.WARN
            }
            .map(ContentRule::describe)
            .distinct()
    }

    val cautions = buildList {
        addAll(draft.cautionMessages)
        timeframeCaution(draft)?.let { add(it) }
    }.distinct()

    return PromiseUnderstanding(
        promiseText = draft.rawText,
        durationMinutes = draft.sessionDurationMinutes,
        lockAttemptThreshold = threshold,
        sessionTimeLabel = formatDuration(draft.sessionDurationMinutes),
        allowedLabel = joinForDisplay(allowed).ifEmpty { "Anything that fits this promise" },
        blockedLabel = joinForDisplay(blocked).ifEmpty { "Whatever pulls you away" },
        conditionalLabel = joinForDisplay(conditional).ifEmpty { null },
        strictnessLabel = strictnessLabel(draft.strictness),
        driftLabel = driftLabel(draft.strictness, threshold),
        managedApps = draft.suggestedAppRules.map { it.label }.distinct(),
        clarificationQuestion = draft.clarificationQuestion,
        cautions = cautions,
        canStart = !draft.needsClarification,
        source = UnderstandingSource.LOCAL_PREVIEW
    )
}

private fun timeframeCaution(draft: FocusPromise): String? {
    val text = draft.rawText
    val hasSessionCue = SESSION_CUE.containsMatchIn(text) ||
        Regex("""\btoday\b""", RegexOption.IGNORE_CASE).containsMatchIn(text)
    val vagueLongHorizon = UNREADABLE_TIMEFRAME.containsMatchIn(text) && !hasSessionCue
    if (!vagueLongHorizon) return null
    if (draft.contentRules.any { it.contentType == "adult_sexual" }) return null
    return "I could not fully read your timeframe, so session time is " +
        "${formatDuration(draft.sessionDurationMinutes)}. Edit the promise if that is wrong."
}

private val UNREADABLE_TIMEFRAME = Regex(
    "\\b(tonight|tomorrow|until|am|pm)\\b",
    RegexOption.IGNORE_CASE
)

private val SESSION_CUE = Regex(
    """\bfor\s+(?:the\s+)?(?:next\s+)?\d+\s*(?:minutes?|mins?|hours?|hrs?|days?|years?)\b""" +
        """|\b\d+\s*(?:days?|years?)\b|\bnext\s+\d+""",
    RegexOption.IGNORE_CASE
)

internal fun formatDuration(minutes: Int): String {
    if (minutes < 60) return "$minutes minutes"
    val yearMinutes = 365 * MINUTES_PER_DAY
    if (minutes >= yearMinutes && minutes % yearMinutes == 0) {
        val years = minutes / yearMinutes
        return if (years == 1) "1 year" else "$years years"
    }
    if (minutes % MINUTES_PER_DAY == 0) {
        val days = minutes / MINUTES_PER_DAY
        return if (days == 1) "1 day" else "$days days"
    }
    val hours = minutes / 60
    val rest = minutes % 60
    val hourLabel = if (hours == 1) "1 hour" else "$hours hours"
    return if (rest == 0) hourLabel else "$hourLabel $rest min"
}

private const val MINUTES_PER_DAY = 24 * 60

internal fun strictnessLabel(level: StrictnessLevel): String = when (level) {
    StrictnessLevel.SOFT -> "Gentle"
    StrictnessLevel.SMART -> "Balanced"
    StrictnessLevel.STRICT -> "Strict"
    StrictnessLevel.LOCKED -> "Locked in"
}

private fun driftLabel(level: StrictnessLevel, threshold: Int): String = when (level) {
    StrictnessLevel.SOFT -> "I nudge you once and leave the choice to you."
    StrictnessLevel.SMART -> "I warn you first, then block if you keep going."
    StrictnessLevel.STRICT -> "I block it and lock the session after $threshold tries."
    StrictnessLevel.LOCKED -> "I block it, no talking me out of it, and lock after $threshold tries."
}

private fun joinForDisplay(values: List<String>): String =
    values.map { it.trim() }
        .filter { it.isNotEmpty() }
        .distinctBy { it.lowercase() }
        .take(8)
        .joinToString(", ")

internal fun lockAttemptThresholdFor(level: StrictnessLevel): Int = when (level) {
    StrictnessLevel.LOCKED, StrictnessLevel.STRICT -> 3
    StrictnessLevel.SOFT, StrictnessLevel.SMART -> 10
}

internal fun applyFocusPromiseDraft(
    draft: FocusPromise,
    studyWorldSettingsStore: StudyWorldSettingsStore
) {
    studyWorldSettingsStore.setDurationMinutes(draft.sessionDurationMinutes)
    studyWorldSettingsStore.setLockAttemptThreshold(lockAttemptThresholdFor(draft.strictness))
}
