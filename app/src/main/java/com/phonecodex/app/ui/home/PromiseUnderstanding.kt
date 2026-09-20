package com.phonecodex.app.ui.home

import com.phonecodex.app.data.StudyWorldSettingsStore
import com.phonecodex.app.domain.model.AppRuleBehavior
import com.phonecodex.app.domain.model.ClarificationOption
import com.phonecodex.app.domain.model.ContentRuleAction
import com.phonecodex.app.domain.model.FocusPromise
import com.phonecodex.app.domain.model.StrictnessLevel
import com.phonecodex.app.domain.model.StudyWorldSettings
import com.phonecodex.app.domain.diagnostics.BackendHealthProbe
import com.phonecodex.app.domain.enforcement.ShortFormLanguage
import com.phonecodex.app.domain.promise.ConfirmedPromiseBinder
import com.phonecodex.app.domain.promise.PromiseClarificationLaw

/**
 * Human-readable confirmation of a compiled promise. Presentation only.
 *
 * Internal packages stay on the draft for PolicyEngine. This model is category-level copy.
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
    /** Category/applies-to line — never package names. */
    val appliesToLabel: String?,
    /** User-named apps only (rarely shown). Prefer [appliesToLabel]. */
    val managedApps: List<String>,
    val clarificationQuestion: String?,
    val clarificationOptions: List<ClarificationOption>,
    val selectedClarificationOptionId: String?,
    val requiresStrongerConfirmation: Boolean,
    val strongerConfirmLabel: String?,
    val strongerConfirmAcknowledged: Boolean,
    val understoodSummary: String?,
    val cautions: List<String>,
    val canStart: Boolean,
    val source: UnderstandingSource,
    /** Short pill / status line for the confirmation card. */
    val statusLabel: String,
    /** One-line guidance under the status (why Start is off, or what this preview is). */
    val statusDetail: String
) {
    val durationLabel: String get() = sessionTimeLabel
    val caution: String? get() = cautions.firstOrNull()

    /** Flat user-visible strings for leak tests. */
    fun userFacingTextBlob(): String = listOfNotNull(
        statusLabel,
        statusDetail,
        sessionTimeLabel,
        allowedLabel,
        blockedLabel,
        conditionalLabel,
        appliesToLabel,
        clarificationQuestion,
        strictnessLabel,
        driftLabel,
        understoodSummary,
        strongerConfirmLabel,
        managedApps.joinToString(", ").takeIf { it.isNotBlank() }
    ).plus(cautions).plus(
        clarificationOptions.flatMap { listOf(it.label, it.description, it.policyPreview.orEmpty()) }
    ).joinToString("\n")
}

internal enum class UnderstandingSource {
    LOCAL_PREVIEW,
    PROMISE_COMPILER
}

internal fun understandingStatusLabel(
    source: UnderstandingSource,
    needsClarification: Boolean,
    requiresStrongerConfirmation: Boolean
): String = when {
    needsClarification -> "Needs one clarification"
    requiresStrongerConfirmation -> "Permanent commitment"
    source == UnderstandingSource.PROMISE_COMPILER -> "AI preview ready"
    else -> "Basic offline preview"
}

internal fun understandingStatusDetail(
    source: UnderstandingSource,
    needsClarification: Boolean,
    clarificationQuestion: String?,
    hasClarificationOptions: Boolean,
    requiresStrongerConfirmation: Boolean
): String = when {
    needsClarification && hasClarificationOptions ->
        clarificationQuestion?.takeIf { it.isNotBlank() }
            ?: "Pick the option that matches what you meant."
    needsClarification ->
        clarificationQuestion?.takeIf { it.isNotBlank() }
            ?: "Answer the question below, then tap Understand Promise again."
    requiresStrongerConfirmation ->
        "Check the box below to confirm how long this lasts, then Start Commitment."
    source == UnderstandingSource.PROMISE_COMPILER ->
        "Review this AI interpretation, then Start Commitment if it matches what you meant."
    else ->
        "${BackendHealthProbe.reachabilityHint()} Showing basic offline preview."
}

internal fun buildPromiseUnderstanding(
    draft: FocusPromise,
    alwaysBlockedLabels: List<String> = emptyList(),
    source: UnderstandingSource = UnderstandingSource.LOCAL_PREVIEW,
    selectedClarificationOptionId: String? = null,
    strongerConfirmAcknowledged: Boolean = false
): PromiseUnderstanding {
    val draft = PromiseClarificationLaw.apply(draft, selectedClarificationOptionId)
    val threshold = lockAttemptThresholdFor(draft.strictness)
    val promiseText = draft.rawText

    fun clean(value: String): String = ConfirmationUserCopy.sanitize(value, promiseText)

    val allowed = buildList {
        addAll(draft.allowedSummaries.map(::clean))
        if (none { it.isNotBlank() }) {
            addAll(draft.allowedKeywords.map(::clean))
            draft.suggestedAppRules
                .filter {
                    it.behavior == AppRuleBehavior.ALLOW || it.behavior == AppRuleBehavior.AI_DECIDE
                }
                .forEach { rule ->
                    ConfirmationUserCopy.userVisibleAppLabels(
                        draft.copy(suggestedAppRules = listOf(rule))
                    ).forEach { add(it) }
                }
            draft.contentRules
                .filter { it.action == ContentRuleAction.ALLOW }
                .forEach { add(ConfirmationUserCopy.describeContentRuleForUser(it, promiseText)) }
        }
        ShortFormLanguage.parseLimit(promiseText)?.let { quota ->
            val already = any { line ->
                line.contains(quota.toString()) && line.contains("short", ignoreCase = true)
            }
            if (!already) {
                add(0, "first $quota short videos, then block")
            }
        }
    }.map(::clean).filter { it.isNotBlank() }

    val blocked = buildList {
        addAll(draft.blockedSummaries.map(::clean))
        if (draft.blockedSummaries.none { it.isNotBlank() }) {
            addAll(draft.blockedKeywords.map(::clean))
            draft.suggestedAppRules
                .filter { it.behavior == AppRuleBehavior.BLOCK }
                .forEach { rule ->
                    ConfirmationUserCopy.userVisibleAppLabels(
                        draft.copy(suggestedAppRules = listOf(rule))
                    ).forEach { add(it) }
                }
            draft.contentRules
                .filter { it.action == ContentRuleAction.BLOCK }
                .forEach { add(ConfirmationUserCopy.describeContentRuleForUser(it, promiseText)) }
        }
        addAll(alwaysBlockedLabels.map(::clean))
    }.map(::clean).filter { it.isNotBlank() }

    val conditionalRaw = ConfirmationUserCopy.stripAppliesToLines(
        draft.conditionalSummaries.ifEmpty {
            draft.contentRules
                .filter {
                    it.action == ContentRuleAction.AI_DECIDE || it.action == ContentRuleAction.WARN
                }
                .map { ConfirmationUserCopy.describeContentRuleForUser(it, promiseText) }
                .distinct()
        }
    ).map(::clean).filter { it.isNotBlank() }

    // Blank-check after sanitize: a field that was only a package ID must fall
    // through to the category label, never render as an empty row.
    val appliesTo = draft.userFacingAppliesTo?.let(::clean)?.takeIf { it.isNotBlank() }
        ?: ConfirmationUserCopy.appliesToLabel(draft)?.let(::clean)?.takeIf { it.isNotBlank() }

    val checkThisAndSafety = buildList {
        addAll(draft.checkThisNotes.map(::clean))
        addAll(draft.safetyNotes.map(::clean))
    }.filter { it.isNotBlank() }.distinct()

    val cautions = buildList {
        addAll(draft.cautionMessages.map(::clean))
        addAll(checkThisAndSafety)
        timeframeCaution(draft)?.let { add(clean(it)) }
    }.map(::clean)
        .filter { it.isNotBlank() }
        .distinct()

    val clarification = draft.clarificationQuestion
        ?.takeIf { it.isNotBlank() }
        ?.let(::clean)
    val options = draft.clarificationOptions.map { option ->
        ClarificationOption(
            id = option.id,
            // A label that sanitizes to blank (e.g. raw package ID) must stay tappable.
            label = clean(option.label).ifBlank { "Option ${option.id}" },
            description = clean(option.description),
            recommended = option.recommended,
            policyPreview = option.policyPreview?.let(::clean)
        )
    }
    val hasOptions = options.isNotEmpty()
    val hasRenderableClarify = hasOptions || !clarification.isNullOrBlank()
    val needsOptionPick = hasOptions && selectedClarificationOptionId.isNullOrBlank()
    val ghostClarify = draft.clarificationRequired &&
        !hasRenderableClarify &&
        PromiseClarificationLaw.isConcreteClockPolicy(draft)
    val needsClarification = !ghostClarify && (draft.needsClarification || needsOptionPick)
    val requiresStrongerConfirm = draft.requiresStrongerConfirmation
    val strongerConfirmLabel = if (requiresStrongerConfirm) {
        strongerConfirmationLabel(draft)
    } else {
        null
    }
    val canStart = computeCanStart(
        draft = draft,
        source = source,
        needsOptionPick = needsOptionPick,
        requiresStrongerConfirm = requiresStrongerConfirm,
        strongerConfirmAcknowledged = strongerConfirmAcknowledged,
        ghostClarify = ghostClarify
    )
    val quotaLimit = ShortFormLanguage.parseLimit(promiseText)
    val understood = draft.understoodSummary?.let(::clean)?.takeIf { it.isNotBlank() }
        .let { summary ->
            if (quotaLimit == null) {
                summary
            } else if (summary == null || !summary.contains(quotaLimit.toString())) {
                "I understood: up to $quotaLimit short videos. I'll remind how many are left."
            } else {
                summary
            }
        }

    return PromiseUnderstanding(
        promiseText = promiseText,
        durationMinutes = draft.sessionDurationMinutes,
        lockAttemptThreshold = threshold,
        sessionTimeLabel = draft.userFacingTime?.let(::clean)
            ?.takeIf { it.isNotBlank() }
            ?: formatDuration(draft.sessionDurationMinutes),
        allowedLabel = joinForDisplay(allowed).ifEmpty { "Anything that fits this promise" },
        blockedLabel = joinForDisplay(blocked).ifEmpty { "Whatever pulls you away" },
        conditionalLabel = joinForDisplay(conditionalRaw).ifEmpty { null },
        strictnessLabel = strictnessLabel(draft.strictness),
        driftLabel = driftLabel(draft.strictness, threshold),
        appliesToLabel = appliesTo,
        managedApps = ConfirmationUserCopy.userVisibleAppLabels(draft),
        clarificationQuestion = clarification,
        clarificationOptions = options,
        selectedClarificationOptionId = selectedClarificationOptionId,
        requiresStrongerConfirmation = requiresStrongerConfirm,
        strongerConfirmLabel = strongerConfirmLabel,
        strongerConfirmAcknowledged = strongerConfirmAcknowledged,
        understoodSummary = understood,
        cautions = cautions,
        canStart = canStart,
        source = source,
        statusLabel = understandingStatusLabel(
            source = source,
            needsClarification = needsClarification,
            requiresStrongerConfirmation = requiresStrongerConfirm && !strongerConfirmAcknowledged
        ),
        statusDetail = understandingStatusDetail(
            source = source,
            needsClarification = needsClarification,
            clarificationQuestion = clarification,
            hasClarificationOptions = hasOptions,
            requiresStrongerConfirmation = requiresStrongerConfirm && !strongerConfirmAcknowledged
        )
    )
}

private fun computeCanStart(
    draft: FocusPromise,
    source: UnderstandingSource,
    needsOptionPick: Boolean,
    requiresStrongerConfirm: Boolean,
    strongerConfirmAcknowledged: Boolean,
    ghostClarify: Boolean
): Boolean {
    // Fail-closed: unanswered A/B/C never Starts.
    if (needsOptionPick) return false
    // Concrete clocks + no options: never keep the user locked on a ghost flag.
    if (ghostClarify) {
        if (requiresStrongerConfirm && !strongerConfirmAcknowledged) return false
        return true
    }
    // Fail-closed: clarification still required (even if server mis-set canStart=true).
    if (draft.clarificationRequired) return false
    // Free-text clarify with no options still blocks Start.
    if (!draft.clarificationQuestion.isNullOrBlank() &&
        draft.clarificationOptions.isEmpty() &&
        draft.canStartCommitment != true
    ) {
        return false
    }
    // Permanent / low-transcript: checkbox must be acknowledged.
    if (requiresStrongerConfirm && !strongerConfirmAcknowledged) return false

    draft.canStartCommitment?.let { serverCanStart ->
        if (serverCanStart) return true
        // Server keeps canStart=false while stronger confirm is required.
        // After checkbox ack, unlock locally (CK-PERMANENT-PORN + confirm UX).
        if (requiresStrongerConfirm && strongerConfirmAcknowledged) return true
        return false
    }
    // Local offline preview: legacy question gate only.
    return !draft.needsClarification
}

private fun strongerConfirmationLabel(draft: FocusPromise): String {
    val duration = formatDuration(draft.sessionDurationMinutes)
    return if (draft.isPermanentCommitment || duration.contains("year")) {
        "I understand this lasts $duration and is harder to remove"
    } else {
        "I understand this commitment lasts $duration"
    }
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

internal fun startDisabledMessage(understanding: PromiseUnderstanding): String = when {
    understanding.canStart -> ""
    understanding.clarificationOptions.isNotEmpty() &&
        understanding.selectedClarificationOptionId.isNullOrBlank() ->
        "Start Commitment stays off until you pick one of the options above."
    understanding.requiresStrongerConfirmation &&
        !understanding.strongerConfirmAcknowledged ->
        "Start Commitment stays off until you confirm how long this lasts."
    !understanding.clarificationQuestion.isNullOrBlank() ->
        "Start Commitment is unavailable until you answer the clarification. " +
            "Edit the promise, then tap Understand Promise again."
    else ->
        "Start Commitment is unavailable until this preview is ready."
}

internal fun lockAttemptThresholdFor(level: StrictnessLevel): Int = when (level) {
    StrictnessLevel.LOCKED, StrictnessLevel.STRICT -> 3
    StrictnessLevel.SOFT, StrictnessLevel.SMART -> 10
}

internal fun applyFocusPromiseDraft(
    draft: FocusPromise,
    studyWorldSettingsStore: StudyWorldSettingsStore
): StudyWorldSettings {
    val bound = ConfirmedPromiseBinder.bind(draft)
    studyWorldSettingsStore.replaceSettings(bound)
    val stored = studyWorldSettingsStore.getSettings()
    val audit = ConfirmedPromiseBinder.audit(draft, stored)
    android.util.Log.i("PhoneCodexPromiseStart", audit.format())
    if (!ConfirmedPromiseBinder.hasStructuredMediaRule(stored)) {
        android.util.Log.i("PhoneCodexPromiseStart", audit.missingStructuredMediaLine())
    }
    return bound
}
