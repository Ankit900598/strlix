package com.phonecodex.app.ui.home

import com.phonecodex.app.data.StudyWorldSettingsStore
import com.phonecodex.app.domain.model.AppRule
import com.phonecodex.app.domain.model.AppRuleBehavior
import com.phonecodex.app.domain.model.FocusPromise
import com.phonecodex.app.domain.model.StrictnessLevel

/**
 * What the app tells the user it understood, in plain language.
 *
 * This is a *presentation* summary. It never decides anything at runtime — enforcement is
 * owned by the accessibility service, PolicyEngine and the backend classifier.
 *
 * Where the real Promise Compiler plugs in:
 * today [buildPromiseUnderstanding] is built from the on-device keyword [FocusPromise] produced
 * by `FocusPromiseParser`. When the compiler ships, replace only the body of
 * [buildPromiseUnderstanding] with a mapping from the compiled policy. Every composable already
 * reads this type, so no UI has to change.
 */
internal data class PromiseUnderstanding(
    val promiseText: String,
    val durationMinutes: Int,
    val lockAttemptThreshold: Int,
    val durationLabel: String,
    val allowedLabel: String,
    val blockedLabel: String,
    val strictnessLabel: String,
    val driftLabel: String,
    val managedApps: List<String>,
    /** Set when the summary is knowingly incomplete, so the card can say so instead of bluffing. */
    val caution: String?,
    val source: UnderstandingSource
)

internal enum class UnderstandingSource {
    /** On-device keyword heuristics. Preview quality, good enough to confirm intent. */
    LOCAL_PREVIEW,

    /** Reserved for the real Promise Compiler output. */
    PROMISE_COMPILER
}

/**
 * Turns a parsed promise into the confirmation summary shown on screen.
 *
 * @param alwaysBlockedLabels display names of permanent commitments already switched on, so the
 *   card is honest about protection the user did not just type.
 */
internal fun buildPromiseUnderstanding(
    draft: FocusPromise,
    alwaysBlockedLabels: List<String> = emptyList()
): PromiseUnderstanding {
    val threshold = lockAttemptThresholdFor(draft.strictness)

    val allowed = buildList {
        addAll(draft.allowedKeywords)
        draft.suggestedAppRules
            .filter { it.behavior == AppRuleBehavior.ALLOW || it.behavior == AppRuleBehavior.AI_DECIDE }
            .forEach { add(it.label) }
    }

    val blocked = buildList {
        addAll(draft.blockedKeywords)
        draft.suggestedAppRules
            .filter { it.behavior == AppRuleBehavior.BLOCK }
            .forEach { add(it.label) }
        addAll(alwaysBlockedLabels)
    }

    return PromiseUnderstanding(
        promiseText = draft.rawText,
        durationMinutes = draft.durationMinutes,
        lockAttemptThreshold = threshold,
        durationLabel = formatDuration(draft.durationMinutes),
        allowedLabel = joinForDisplay(allowed).ifEmpty { "Anything that fits this promise" },
        blockedLabel = joinForDisplay(blocked).ifEmpty { "Whatever pulls you away" },
        strictnessLabel = strictnessLabel(draft.strictness),
        driftLabel = driftLabel(draft.strictness, threshold),
        managedApps = draft.suggestedAppRules.map(::describeAppRule),
        caution = timeframeCaution(draft),
        source = UnderstandingSource.LOCAL_PREVIEW
    )
}

/**
 * The keyword parser only understands "N minutes" and "N hours". Anything else (a year, until
 * 2am, tomorrow) silently falls back to the default duration, so say that out loud rather than
 * showing a confident wrong number.
 */
private fun timeframeCaution(draft: FocusPromise): String? {
    val text = draft.rawText
    val vague = UNREADABLE_TIMEFRAME.containsMatchIn(text) &&
        !EXPLICIT_DURATION.containsMatchIn(text)
    if (!vague) return null

    return "I could not read your timeframe yet, so I fell back to " +
        "${formatDuration(draft.durationMinutes)}. Set it under Advanced Controls if that is wrong."
}

private val UNREADABLE_TIMEFRAME = Regex(
    "\\b(year|years|month|months|week|weeks|day|days|tonight|tomorrow|until|am|pm)\\b",
    RegexOption.IGNORE_CASE
)

private val EXPLICIT_DURATION = Regex(
    "\\b\\d+\\s*(hours?|hrs?|minutes?|mins?)\\b",
    RegexOption.IGNORE_CASE
)

internal fun formatDuration(minutes: Int): String {
    if (minutes < 60) return "$minutes minutes"
    val hours = minutes / 60
    val rest = minutes % 60
    val hourLabel = if (hours == 1) "1 hour" else "$hours hours"
    return if (rest == 0) hourLabel else "$hourLabel $rest min"
}

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

private fun describeAppRule(rule: AppRule): String {
    val behavior = when (rule.behavior) {
        AppRuleBehavior.ALLOW -> "allowed"
        AppRuleBehavior.WARN -> "warned"
        AppRuleBehavior.BLOCK -> "blocked"
        AppRuleBehavior.AI_DECIDE -> "judged live"
    }
    return "${rule.label} · $behavior"
}

private fun joinForDisplay(values: List<String>): String =
    values.map { it.trim() }
        .filter { it.isNotEmpty() }
        .distinctBy { it.lowercase() }
        .take(6)
        .joinToString(", ")

/** Strictness decides how much rope the user gets before a session locks. */
internal fun lockAttemptThresholdFor(level: StrictnessLevel): Int = when (level) {
    StrictnessLevel.LOCKED, StrictnessLevel.STRICT -> 3
    StrictnessLevel.SOFT, StrictnessLevel.SMART -> 10
}

/** Persists the parts of a promise that the enforcement engine actually reads. */
internal fun applyFocusPromiseDraft(
    draft: FocusPromise,
    studyWorldSettingsStore: StudyWorldSettingsStore
) {
    studyWorldSettingsStore.setDurationMinutes(draft.durationMinutes)
    studyWorldSettingsStore.setLockAttemptThreshold(lockAttemptThresholdFor(draft.strictness))
}
