package com.phonecodex.app.domain.promise

import com.phonecodex.app.domain.model.ContentRule
import com.phonecodex.app.domain.model.ContentRuleAction
import com.phonecodex.app.domain.model.FocusPromise

/**
 * Extracts structured clock fields from a confirmed [FocusPromise]
 * so enforcement does not re-parse English.
 */
object PromiseContentRuleSupport {

    /**
     * Per-video block threshold in minutes (clock B): block when individual
     * video length is greater than this value. Null = no structured length gate.
     */
    fun maxVideoLengthBlockMinutes(draft: FocusPromise): Int? =
        maxVideoLengthBlockMinutes(draft.contentRules)
            ?: PromiseIntentRules.extractGoalMaxVideoLimitMinutes(draft.rawText)

    fun maxVideoLengthBlockMinutes(rules: List<ContentRule>): Int? {
        val blockGt = rules.firstOrNull { rule ->
            rule.action == ContentRuleAction.BLOCK &&
                rule.unit.equals("minutes", ignoreCase = true) &&
                rule.value != null &&
                rule.value!! > 0 &&
                (rule.operator == "gt" || rule.operator == "gte") &&
                isVideoish(rule)
        }
        if (blockGt != null) {
            // gt 40 → block when > 40; gte 40 → treat as block when >= 40 → use 39 for ">"
            return if (blockGt.operator == "gte") {
                (blockGt.value!! - 1).coerceAtLeast(0)
            } else {
                blockGt.value
            }
        }
        return null
    }

    /**
     * Per-video minimum length in minutes (clock B): block when individual
     * video length is shorter than this value. Null = no structured min gate.
     */
    fun minVideoLengthBlockMinutes(draft: FocusPromise): Int? =
        PromiseIntentRules.extractGoalMinVideoLimitMinutes(draft.rawText)
            ?: minVideoLengthBlockMinutes(draft.contentRules)
            ?: minFromAllowOnlyLongerRules(draft.contentRules)

    fun minVideoLengthBlockMinutes(rules: List<ContentRule>): Int? {
        val blockLt = rules.firstOrNull { rule ->
            rule.action == ContentRuleAction.BLOCK &&
                rule.unit.equals("minutes", ignoreCase = true) &&
                rule.value != null &&
                rule.value!! > 0 &&
                (rule.operator == "lt" || rule.operator == "lte") &&
                isVideoish(rule)
        } ?: return null
        // lt 30 → block when < 30; lte 30 → block when <= 30 → treat as min 31 for "<"
        return if (blockLt.operator == "lte") {
            blockLt.value!! + 1
        } else {
            blockLt.value
        }
    }

    fun hasShortFormBlock(rules: List<ContentRule>): Boolean =
        rules.any {
            it.action == ContentRuleAction.BLOCK &&
                (
                    it.contentType == "short_form_video" ||
                        it.surface.equals("shorts", ignoreCase = true) ||
                        it.surface.equals("reels", ignoreCase = true)
                    )
        }

    /**
     * Daily short-form count quota from structured contentRules (unit=count),
     * else null so callers can fall back to goal-text parse.
     */
    fun shortFormDailyQuotaLimit(draft: FocusPromise): Int? {
        val fromRules = draft.contentRules.firstOrNull { rule ->
            rule.unit.equals("count", ignoreCase = true) &&
                rule.value != null &&
                rule.value!! > 0 &&
                (
                    rule.contentType == "short_form_video" ||
                        rule.surface.equals("shorts", ignoreCase = true) ||
                        rule.surface.equals("reels", ignoreCase = true)
                    ) &&
                (
                    rule.action == ContentRuleAction.ALLOW ||
                        rule.action == ContentRuleAction.WARN ||
                        rule.operator == "lte" ||
                        rule.operator == "lt"
                    )
        }?.value
        return fromRules
            ?: com.phonecodex.app.domain.enforcement.ShortFormQuotaGate.parseDailyShortFormLimit(
                draft.rawText
            )
    }

    fun isCalendarDayWindow(draft: FocusPromise): Boolean {
        val text = draft.rawText.lowercase()
        if (text.contains("today") ||
            text.contains("per day") ||
            text.contains("daily") ||
            text.contains("rest of the day") ||
            text.contains("for the day")
        ) {
            return true
        }
        if (draft.sessionDurationMinutes >= 24 * 60) return true
        val quota = shortFormDailyQuotaLimit(draft)
        return quota != null && !PromiseIntentRules.hasExplicitSessionDuration(text)
    }

    /**
     * Packages that clocks should apply to after clarification rematerialize.
     * Prefer explicit [FocusPromise.scopePackages]; else distinct packageNames on contentRules.
     */
    fun enforcementScopePackages(draft: FocusPromise): List<String> {
        if (draft.scopePackages.isNotEmpty()) {
            return draft.scopePackages.map { it.trim() }.filter { it.isNotEmpty() }.distinct()
        }
        val fromRules = draft.contentRules
            .mapNotNull { it.packageName?.trim()?.takeIf { pkg -> pkg.isNotEmpty() } }
            .distinct()
        if (fromRules.isNotEmpty()) return fromRules
        if (
            PromiseIntentRules.namesThisAppOnly(draft.rawText) ||
            PromiseIntentRules.namesNetMirror(draft.rawText)
        ) {
            return draft.suggestedAppRules
                .map { it.packageName.trim() }
                .filter { it.isNotEmpty() }
                .distinct()
        }
        return emptyList()
    }

    private fun minFromAllowOnlyLongerRules(rules: List<ContentRule>): Int? {
        val allowGt = rules.firstOrNull { rule ->
            rule.action == ContentRuleAction.ALLOW &&
                rule.unit.equals("minutes", ignoreCase = true) &&
                rule.value != null &&
                rule.value!! > 0 &&
                (rule.operator == "gt" || rule.operator == "gte") &&
                isVideoish(rule)
        } ?: return null
        return allowGt.value
    }

    private fun isVideoish(rule: ContentRule): Boolean {
        val type = rule.contentType.lowercase()
        val surface = rule.surface.lowercase()
        return type.contains("video") ||
            type == "entertainment" ||
            type == "long_form_video" ||
            surface == "video" ||
            surface == "any"
    }
}
