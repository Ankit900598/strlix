package com.phonecodex.app.domain.promise

import com.phonecodex.app.domain.enforcement.EnforcementReasonCodes
import com.phonecodex.app.domain.enforcement.ShortFormQuotaGate
import com.phonecodex.app.domain.model.FocusPromise
import com.phonecodex.app.domain.model.StrictnessLevel
import com.phonecodex.app.domain.model.StudyWorldSettings

/**
 * Confirmed promise → stored Study World clocks.
 * Accessibility must read these fields; it must not re-parse English.
 */
object ConfirmedPromiseBinder {

    fun bind(draft: FocusPromise): StudyWorldSettings {
        val isCalendarDay = PromiseContentRuleSupport.isCalendarDayWindow(draft)
        val duration = if (isCalendarDay) {
            maxOf(draft.sessionDurationMinutes, 24 * 60)
        } else {
            draft.sessionDurationMinutes
        }
        return StudyWorldSettings(
            durationMinutes = duration.coerceAtLeast(1),
            lockAttemptThreshold = lockAttemptThresholdFor(draft.strictness),
            blockAttemptCooldownMinutes = 2,
            maxVideoLengthBlockMinutes =
                PromiseContentRuleSupport.maxVideoLengthBlockMinutes(draft),
            minVideoLengthBlockMinutes =
                PromiseContentRuleSupport.minVideoLengthBlockMinutes(draft),
            shortFormDailyQuotaLimit =
                PromiseContentRuleSupport.shortFormDailyQuotaLimit(draft),
            allowLongEducationalVideos = ShortFormQuotaGate.allowsLongEducational(draft.rawText),
            timeWindowKind = if (isCalendarDay) {
                "calendar_day"
            } else {
                "session_fixed"
            },
            enforcementScopePackages = PromiseContentRuleSupport.enforcementScopePackages(draft)
        )
    }

    fun audit(draft: FocusPromise, stored: StudyWorldSettings): PromiseStartAudit =
        PromiseStartAudit(
            rawPromise = draft.rawText,
            contentRules = draft.contentRules.map { rule ->
                listOf(
                    rule.action.name,
                    rule.operator.orEmpty(),
                    rule.value?.toString().orEmpty(),
                    rule.unit.orEmpty(),
                    rule.contentType,
                    rule.surface,
                    rule.packageName.orEmpty()
                ).joinToString(":")
            },
            minVideoLengthBlockMinutes = stored.minVideoLengthBlockMinutes,
            maxVideoLengthBlockMinutes = stored.maxVideoLengthBlockMinutes,
            shortFormDailyQuotaLimit = stored.shortFormDailyQuotaLimit,
            enforcementScopePackages = stored.enforcementScopePackages
        )

    fun hasStructuredMediaRule(settings: StudyWorldSettings): Boolean =
        settings.minVideoLengthBlockMinutes != null ||
            settings.maxVideoLengthBlockMinutes != null ||
            settings.shortFormDailyQuotaLimit != null

    /** Session clock for Start. Never fall back to leftover Study World 30. */
    fun sessionDurationMillis(settings: StudyWorldSettings): Long =
        settings.durationMinutes.coerceAtLeast(1) * 60_000L

    fun sessionDurationMillis(draft: FocusPromise): Long =
        sessionDurationMillis(bind(draft))

    private fun lockAttemptThresholdFor(level: StrictnessLevel): Int = when (level) {
        StrictnessLevel.LOCKED, StrictnessLevel.STRICT -> 3
        StrictnessLevel.SOFT, StrictnessLevel.SMART -> 10
    }
}

data class PromiseStartAudit(
    val rawPromise: String,
    val contentRules: List<String>,
    val minVideoLengthBlockMinutes: Int?,
    val maxVideoLengthBlockMinutes: Int?,
    val shortFormDailyQuotaLimit: Int?,
    val enforcementScopePackages: List<String>
) {
    fun format(): String =
        "rawPromise=${rawPromise.replace("\n", " ").take(240)} " +
            "contentRules=[${contentRules.joinToString(";")}] " +
            "minVideoLengthBlockMinutes=$minVideoLengthBlockMinutes " +
            "maxVideoLengthBlockMinutes=$maxVideoLengthBlockMinutes " +
            "shortFormDailyQuotaLimit=$shortFormDailyQuotaLimit " +
            "enforcementScopePackages=[${enforcementScopePackages.joinToString(",")}] " +
            "stored settings after write: " +
            "min=$minVideoLengthBlockMinutes max=$maxVideoLengthBlockMinutes " +
            "quota=$shortFormDailyQuotaLimit scope=$enforcementScopePackages"

    fun missingStructuredMediaLine(): String =
        "code=${EnforcementReasonCodes.NO_STRUCTURED_MEDIA_RULE} " +
            "session active but media settings are null " +
            "(min/max/quota all unset)"
}
