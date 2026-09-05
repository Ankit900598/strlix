package com.phonecodex.app.domain.promise

import com.phonecodex.app.domain.model.AppRule
import com.phonecodex.app.domain.model.AppRuleBehavior
import com.phonecodex.app.domain.model.ContentRule
import com.phonecodex.app.domain.model.ContentRuleAction
import com.phonecodex.app.domain.model.FocusPromise
import com.phonecodex.app.domain.model.StrictnessLevel

/**
 * On-device Promise Compiler preview.
 *
 * Separates session duration from content-duration / surface rules. Ambiguous promises return
 * [FocusPromise.clarificationQuestion] so Start cannot run.
 *
 * Azure swap: map Promise Compiler JSON → [FocusPromise]; confirmation UI stays unchanged.
 */
class FocusPromiseParser {

    fun parse(rawText: String): FocusPromise {
        val trimmed = rawText.trim()
        val normalized = trimmed.lowercase()

        val contentLengthHits = findContentLengthHits(normalized)
        var contentRules = buildContentRules(normalized, contentLengthHits)
        contentRules = applyOnlyLongVideoSemantics(normalized, contentRules, contentLengthHits)

        val sessionDurationMinutes = parseSessionDurationMinutes(normalized, contentLengthHits)
        val suggestedAppRules = parseSuggestedAppRules(normalized, contentRules)
        val strictness = parseStrictness(normalized)
        val clarification = detectClarification(normalized, contentRules, contentLengthHits)
        val warnings = buildWarnings(normalized, sessionDurationMinutes, contentLengthHits)

        val summaries = buildHumanSummaries(
            normalized = normalized,
            contentRules = contentRules,
            suggestedAppRules = suggestedAppRules
        )

        return FocusPromise(
            rawText = trimmed,
            sessionDurationMinutes = sessionDurationMinutes,
            allowedKeywords = findKeywords(normalized, ALLOW_KEYWORDS),
            blockedKeywords = findKeywords(normalized, BLOCK_KEYWORDS),
            strictness = strictness,
            suggestedAppRules = suggestedAppRules,
            contentRules = contentRules,
            clarificationQuestion = clarification,
            warnings = warnings,
            allowedSummaries = summaries.allowed,
            blockedSummaries = summaries.blocked,
            conditionalSummaries = summaries.conditional
        )
    }

    private data class ContentLengthHit(
        val range: IntRange,
        val minutes: Int,
        val operator: String
    )

    private data class HumanSummaries(
        val allowed: List<String>,
        val blocked: List<String>,
        val conditional: List<String>
    )

    private fun findContentLengthHits(normalized: String): List<ContentLengthHit> {
        val hits = mutableListOf<ContentLengthHit>()

        fun addHit(range: IntRange, minutes: Int, operator: String) {
            val covered = hits.any { it.range.first <= range.first && range.last <= it.range.last }
            if (!covered) hits += ContentLengthHit(range, minutes, operator)
        }

        CONTENT_COMPARISON_PATTERN.findAll(normalized).forEach { match ->
            val opWord = match.groupValues[1]
            val amount = match.groupValues[2].toIntOrNull() ?: return@forEach
            val unit = match.groupValues[3]
            val minutes = toMinutes(amount, unit) ?: return@forEach
            val operator = when {
                opWord.startsWith("long") || opWord.startsWith("great") ||
                    opWord.startsWith("more") -> "gt"
                opWord.startsWith("shorter") || opWord.startsWith("less") -> "lt"
                else -> "gt"
            }
            addHit(match.range, minutes, operator)
        }

        LENGTH_IS_PATTERN.findAll(normalized).forEach { match ->
            val amount = match.groupValues[1].toIntOrNull() ?: return@forEach
            val unit = match.groupValues[2]
            val minutes = toMinutes(amount, unit) ?: return@forEach
            addHit(match.range, minutes, "gt")
        }

        CONTENT_GT_SYMBOL_PATTERN.findAll(normalized).forEach { match ->
            val amount = match.groupValues[1].toIntOrNull() ?: return@forEach
            val unit = match.groupValues[2]
            val minutes = toMinutes(amount, unit) ?: return@forEach
            addHit(match.range, minutes, "gt")
        }

        return hits
    }

    private fun buildContentRules(
        normalized: String,
        lengthHits: List<ContentLengthHit>
    ): List<ContentRule> {
        val rules = mutableListOf<ContentRule>()

        lengthHits.forEach { hit ->
            val windowStart = (hit.range.first - 64).coerceAtLeast(0)
            val window = normalized.substring(windowStart, hit.range.last + 1)
            val action = inferLengthAction(window)
            val apps = appsMentionedNear(window, normalized)

            if (apps.isEmpty()) {
                rules += ContentRule(
                    appLabel = null,
                    packageName = null,
                    surface = "video",
                    contentType = "long_form_video",
                    operator = hit.operator,
                    value = hit.minutes,
                    unit = "minutes",
                    action = action
                )
            } else {
                apps.forEach { app ->
                    rules += ContentRule(
                        appLabel = app.label,
                        packageName = app.packageName,
                        surface = "video",
                        contentType = "long_form_video",
                        operator = hit.operator,
                        value = hit.minutes,
                        unit = "minutes",
                        action = action
                    )
                }
            }
        }

        if (mentionsInstagram(normalized)) {
            val messagesOnly = INSTAGRAM_MESSAGES_ONLY.containsMatchIn(normalized) ||
                ((normalized.contains("only") || normalized.contains("sirf")) &&
                    (normalized.contains("message") || normalized.contains("dm") ||
                        normalized.contains("chat") || normalized.contains("repl")))
            val noReels = normalized.contains("no reel") || normalized.contains("no reels") ||
                (normalized.contains("reel") &&
                    (normalized.contains("block") || normalized.contains("don't") ||
                        normalized.contains("dont") || normalized.contains("without") ||
                        normalized.contains("mat ")))
            if (messagesOnly) {
                rules += ContentRule(
                    appLabel = "Instagram",
                    packageName = PKG_INSTAGRAM,
                    surface = "messages",
                    contentType = "social_dm",
                    operator = null,
                    value = null,
                    unit = null,
                    action = ContentRuleAction.ALLOW
                )
            }
            if (noReels || messagesOnly) {
                rules += ContentRule(
                    appLabel = "Instagram",
                    packageName = PKG_INSTAGRAM,
                    surface = "reels",
                    contentType = "short_form_video",
                    operator = null,
                    value = null,
                    unit = null,
                    action = ContentRuleAction.BLOCK
                )
                rules += ContentRule(
                    appLabel = "Instagram",
                    packageName = PKG_INSTAGRAM,
                    surface = "feed",
                    contentType = "social_feed",
                    operator = null,
                    value = null,
                    unit = null,
                    action = ContentRuleAction.BLOCK
                )
            }
        }

        if ((normalized.contains("youtube") || normalized.contains("neso") ||
                normalized.contains("playlist")) &&
            (normalized.contains("neso") || normalized.contains("playlist") ||
                normalized.contains("only on") ||
                (normalized.contains("only") && normalized.contains("lecture")))
        ) {
            rules += ContentRule(
                appLabel = "YouTube",
                packageName = PKG_YOUTUBE,
                surface = "playlist",
                contentType = "study",
                operator = null,
                value = null,
                unit = null,
                action = ContentRuleAction.AI_DECIDE
            )
        }

        if (normalized.contains("porn") || normalized.contains("adult content") ||
            normalized.contains("nsfw") || normalized.contains("18+")
        ) {
            rules += ContentRule(
                appLabel = null,
                packageName = null,
                surface = "any",
                contentType = "adult_sexual",
                operator = null,
                value = null,
                unit = null,
                action = ContentRuleAction.BLOCK
            )
        }

        return rules.distinctBy {
            listOf(it.appLabel, it.surface, it.contentType, it.operator, it.value, it.action)
        }
    }

    /**
     * "only allow … longer than N" means shorter videos are blocked — no clarification needed.
     */
    private fun applyOnlyLongVideoSemantics(
        normalized: String,
        rules: List<ContentRule>,
        hits: List<ContentLengthHit>
    ): List<ContentRule> {
        if (hits.isEmpty()) return rules
        val onlyLong = hits.any { hit ->
            val before = normalized.substring(0, hit.range.first).takeLast(72)
            ONLY_ALLOW_CUE.containsMatchIn(before) ||
                (before.contains("only") &&
                    (before.contains("allow") || before.contains("youtube") ||
                        before.contains("video")))
        }
        if (!onlyLong) return rules

        val expanded = rules.toMutableList()
        rules.filter {
            it.action == ContentRuleAction.ALLOW &&
                it.operator == "gt" &&
                it.contentType == "long_form_video" &&
                it.value != null
        }.forEach { allowRule ->
            expanded += allowRule.copy(
                operator = "lte",
                action = ContentRuleAction.BLOCK
            )
        }
        return expanded.distinctBy {
            listOf(it.appLabel, it.surface, it.contentType, it.operator, it.value, it.action)
        }
    }

    private fun inferLengthAction(window: String): ContentRuleAction {
        val blockCue = window.contains("block") || window.contains("don't allow") ||
            window.contains("dont allow") || window.contains("forbid")
        val allowCue = window.contains("allow") || window.contains("keep me") ||
            window.contains("only")
        return when {
            blockCue && !allowCue -> ContentRuleAction.BLOCK
            allowCue -> ContentRuleAction.ALLOW
            blockCue -> ContentRuleAction.BLOCK
            else -> ContentRuleAction.ALLOW
        }
    }

    private data class AppRef(val label: String, val packageName: String)

    private fun appsMentionedNear(window: String, full: String): List<AppRef> {
        val apps = mutableListOf<AppRef>()
        val scope = "$window $full"
        if (scope.contains("youtube") || scope.contains("yt ")) {
            apps += AppRef("YouTube", PKG_YOUTUBE)
        }
        if (scope.contains("chrome") || scope.contains("browser") ||
            (scope.contains("anywhere") &&
                (scope.contains("youtube") || scope.contains("video")))
        ) {
            apps += AppRef("Chrome", PKG_CHROME)
        }
        return apps.distinctBy { it.packageName }
    }

    private fun parseSessionDurationMinutes(
        normalized: String,
        contentHits: List<ContentLengthHit>
    ): Int {
        val occupied = contentHits.map { it.range }

        fun overlapsContent(range: IntRange): Boolean =
            occupied.any { content ->
                range.first <= content.last && content.first <= range.last
            }

        SESSION_FOR_PATTERN.findAll(normalized).forEach { match ->
            if (overlapsContent(match.range)) return@forEach
            val amount = match.groupValues[1].toIntOrNull() ?: return@forEach
            toMinutes(amount, match.groupValues[2])?.let { return it }
        }

        SESSION_NEXT_PATTERN.findAll(normalized).forEach { match ->
            if (overlapsContent(match.range)) return@forEach
            val amount = match.groupValues[1].toIntOrNull() ?: return@forEach
            toMinutes(amount, match.groupValues[2])?.let { return it }
        }

        SESSION_DAY_YEAR_PATTERN.findAll(normalized).forEach { match ->
            if (overlapsContent(match.range)) return@forEach
            val before = normalized.substring(0, match.range.first).takeLast(24)
            if (CONTENT_COMPARE_CUES.containsMatchIn(before)) return@forEach
            val amount = match.groupValues[1].toIntOrNull() ?: return@forEach
            toMinutes(amount, match.groupValues[2])?.let { return it }
        }

        if (Regex("""\btoday\b""").containsMatchIn(normalized)) {
            return MINUTES_PER_DAY
        }

        HOUR_PATTERN.findAll(normalized).forEach { match ->
            if (overlapsContent(match.range)) return@forEach
            val before = normalized.substring(0, match.range.first).takeLast(24)
            if (CONTENT_COMPARE_CUES.containsMatchIn(before)) return@forEach
            val hours = match.groupValues[1].toIntOrNull() ?: return@forEach
            return hours * 60
        }
        MINUTE_PATTERN.findAll(normalized).forEach { match ->
            if (overlapsContent(match.range)) return@forEach
            val before = normalized.substring(0, match.range.first).takeLast(24)
            if (CONTENT_COMPARE_CUES.containsMatchIn(before)) return@forEach
            return match.groupValues[1].toIntOrNull() ?: DEFAULT_DURATION_MINUTES
        }

        return DEFAULT_DURATION_MINUTES
    }

    private fun toMinutes(amount: Int, unit: String): Int? {
        val u = unit.lowercase()
        return when {
            u.startsWith("min") -> amount
            u.startsWith("hour") || u.startsWith("hr") -> amount * 60
            u.startsWith("day") -> amount * MINUTES_PER_DAY
            u.startsWith("year") -> amount * MINUTES_PER_YEAR
            else -> null
        }
    }

    private fun detectClarification(
        normalized: String,
        contentRules: List<ContentRule>,
        lengthHits: List<ContentLengthHit>
    ): String? {
        if (INSTA_LESS.containsMatchIn(normalized)) {
            val hasConcrete = contentRules.any {
                it.packageName == PKG_INSTAGRAM &&
                    (it.surface == "messages" || it.surface == "reels" || it.value != null)
            }
            if (!hasConcrete) {
                return "What limit do you want on Instagram — a time cap, Reels only, or messages only?"
            }
        }

        if (STRICT_VAGUE.containsMatchIn(normalized) || MAKE_STRICT.containsMatchIn(normalized)) {
            val hasConcreteApps = hasConcreteRestrictionCue(normalized, contentRules)
            if (!hasConcreteApps) {
                return "What apps or content should I restrict today?"
            }
        }

        if (FOCUS_VAGUE.containsMatchIn(normalized) &&
            !hasConcreteRestrictionCue(normalized, contentRules) &&
            lengthHits.isEmpty()
        ) {
            return "Focus on what — which apps, how long, and what should stay blocked?"
        }

        val allowLong = contentRules.any {
            it.action == ContentRuleAction.ALLOW &&
                it.operator == "gt" &&
                it.contentType == "long_form_video"
        }
        val hasShorterBlock = contentRules.any {
            it.action == ContentRuleAction.BLOCK &&
                (it.operator == "lt" || it.operator == "lte") &&
                it.contentType == "long_form_video"
        }
        if (allowLong && !hasShorterBlock) {
            val mentionsShorterPolicy = normalized.contains("shorter") ||
                normalized.contains("less than") ||
                normalized.contains("under ") ||
                normalized.contains("block short") ||
                normalized.contains("nothing shorter") ||
                normalized.contains("no shorter")
            if (!mentionsShorterPolicy) {
                return "Should shorter videos be blocked, or are long videos simply allowed while shorter ones stay fine?"
            }
        }

        if (normalized.length < 12 &&
            lengthHits.isEmpty() &&
            contentRules.isEmpty() &&
            !ALLOW_KEYWORDS.any { normalized.contains(it) }
        ) {
            return "What exactly should I protect — which apps, for how long?"
        }

        return null
    }

    private fun hasConcreteRestrictionCue(
        normalized: String,
        contentRules: List<ContentRule>
    ): Boolean {
        return normalized.contains("youtube") ||
            normalized.contains("instagram") ||
            normalized.contains("insta") ||
            normalized.contains("chrome") ||
            normalized.contains("whatsapp") ||
            normalized.contains("shorts") ||
            normalized.contains("reel") ||
            normalized.contains("neso") ||
            normalized.contains("porn") ||
            normalized.contains("adult") ||
            contentRules.isNotEmpty()
    }

    private fun buildWarnings(
        normalized: String,
        sessionMinutes: Int,
        contentHits: List<ContentLengthHit>
    ): List<String> {
        val warnings = mutableListOf<String>()
        if (sessionMinutes == DEFAULT_DURATION_MINUTES &&
            !SESSION_FOR_PATTERN.containsMatchIn(normalized) &&
            !SESSION_NEXT_PATTERN.containsMatchIn(normalized) &&
            !SESSION_DAY_YEAR_PATTERN.containsMatchIn(normalized) &&
            !Regex("""\btoday\b""").containsMatchIn(normalized) &&
            contentHits.isNotEmpty()
        ) {
            warnings += "I set session time to the default $DEFAULT_DURATION_MINUTES minutes " +
                "because I only saw a content length rule, not how long the commitment should run."
        }
        if (sessionMinutes >= MINUTES_PER_YEAR) {
            warnings += "Long commitments still need Accessibility kept on — preview, not a finished permanent lock."
        }
        if (normalized.contains("rest normal") || normalized.contains("everything else normal") ||
            normalized.contains("rest is normal")
        ) {
            warnings += "Other apps stay normal unless a permanent commitment is already on."
        }
        return warnings
    }

    private fun buildHumanSummaries(
        normalized: String,
        contentRules: List<ContentRule>,
        suggestedAppRules: List<AppRule>
    ): HumanSummaries {
        val allowed = mutableListOf<String>()
        val blocked = mutableListOf<String>()
        val conditional = mutableListOf<String>()

        contentRules.forEach { rule ->
            val line = humanContentLine(rule)
            when (rule.action) {
                ContentRuleAction.ALLOW -> allowed += line
                ContentRuleAction.BLOCK -> blocked += line
                ContentRuleAction.WARN, ContentRuleAction.AI_DECIDE -> conditional += line
            }
        }

        suggestedAppRules.forEach { rule ->
            when (rule.behavior) {
                AppRuleBehavior.ALLOW -> allowed += rule.label
                AppRuleBehavior.BLOCK -> {
                    if (blocked.none { it.contains(rule.label, ignoreCase = true) }) {
                        blocked += rule.label
                    }
                }
                AppRuleBehavior.WARN, AppRuleBehavior.AI_DECIDE -> {
                    if (conditional.none { it.contains(rule.label, ignoreCase = true) } &&
                        allowed.none { it.contains(rule.label, ignoreCase = true) } &&
                        blocked.none { it.contains(rule.label, ignoreCase = true) }
                    ) {
                        conditional += "${rule.label} judged live"
                    }
                }
            }
        }

        if (normalized.contains("study") || normalized.contains("exam") ||
            normalized.contains("lecture") || normalized.contains("neso")
        ) {
            if (allowed.none { it.contains("study", ignoreCase = true) }) {
                allowed += "Study / lecture work"
            }
        }

        return HumanSummaries(
            allowed = allowed.distinct(),
            blocked = blocked.distinct(),
            conditional = conditional.distinct()
        )
    }

    private fun humanContentLine(rule: ContentRule): String {
        val app = rule.appLabel ?: "Content"
        return when {
            rule.operator != null && rule.value != null -> {
                val op = when (rule.operator) {
                    "gt" -> "longer than"
                    "gte" -> "at least"
                    "lt" -> "shorter than"
                    "lte" -> "up to"
                    else -> rule.operator
                }
                val action = when (rule.action) {
                    ContentRuleAction.ALLOW -> "allowed"
                    ContentRuleAction.BLOCK -> "blocked"
                    ContentRuleAction.WARN -> "warned"
                    ContentRuleAction.AI_DECIDE -> "checked live"
                }
                "$app videos $op ${rule.value} min → $action"
            }
            rule.surface == "messages" -> "$app messages"
            rule.surface == "reels" -> "$app Reels"
            rule.surface == "feed" -> "$app feed"
            rule.surface == "playlist" -> "$app playlist / channel"
            rule.contentType == "adult_sexual" -> "Adult content"
            else -> "$app ${rule.surface}"
        }
    }

    private fun parseSuggestedAppRules(
        normalized: String,
        contentRules: List<ContentRule>
    ): List<AppRule> {
        val suggestions = mutableListOf<AppRule>()

        if (normalized.contains("telegram")) {
            suggestions += AppRule(PKG_TELEGRAM, "Telegram", AppRuleBehavior.WARN)
        }
        if (normalized.contains("whatsapp")) {
            suggestions += AppRule(PKG_WHATSAPP, "WhatsApp", AppRuleBehavior.WARN)
        }

        val youtubeRules = contentRules.filter { it.packageName == PKG_YOUTUBE }
        if (normalized.contains("youtube") || normalized.contains("lecture") ||
            normalized.contains("neso") || youtubeRules.isNotEmpty()
        ) {
            // Length-threshold YouTube stays AI_DECIDE (content rules decide), not whole-app BLOCK.
            val wholeAppBlock = youtubeRules.any {
                it.action == ContentRuleAction.BLOCK && it.operator == null
            }
            val behavior = when {
                wholeAppBlock -> AppRuleBehavior.BLOCK
                youtubeRules.any { it.operator != null } -> AppRuleBehavior.AI_DECIDE
                youtubeRules.any { it.action == ContentRuleAction.AI_DECIDE } ->
                    AppRuleBehavior.AI_DECIDE
                else -> AppRuleBehavior.AI_DECIDE
            }
            suggestions += AppRule(PKG_YOUTUBE, "YouTube", behavior)
        }

        if (normalized.contains("chrome") || normalized.contains("browser") ||
            (normalized.contains("anywhere") && normalized.contains("youtube"))
        ) {
            val chromeBehavior = if (allowsBroadChromeUse(normalized)) {
                AppRuleBehavior.ALLOW
            } else {
                AppRuleBehavior.AI_DECIDE
            }
            suggestions += AppRule(PKG_CHROME, "Chrome", chromeBehavior)
        }

        if (mentionsInstagram(normalized)) {
            val igRules = contentRules.filter { it.packageName == PKG_INSTAGRAM }
            val behavior = when {
                igRules.any { it.surface == "messages" && it.action == ContentRuleAction.ALLOW } ->
                    AppRuleBehavior.AI_DECIDE
                igRules.any { it.action == ContentRuleAction.BLOCK } &&
                    igRules.none { it.action == ContentRuleAction.ALLOW } ->
                    AppRuleBehavior.BLOCK
                else -> AppRuleBehavior.BLOCK
            }
            suggestions += AppRule(PKG_INSTAGRAM, "Instagram", behavior)
        }

        return suggestions.distinctBy { it.packageName }
    }

    private fun mentionsInstagram(normalized: String): Boolean =
        normalized.contains("instagram") || normalized.contains("insta") ||
            normalized.contains("reels")

    private fun allowsBroadChromeUse(normalized: String): Boolean =
        normalized.contains("allow everything on chrome") ||
            normalized.contains("chrome allow everything") ||
            normalized.contains("anything on chrome") ||
            normalized.contains("everything in chrome")

    private fun findKeywords(normalizedText: String, keywords: List<String>): List<String> =
        keywords.filter { keyword -> normalizedText.contains(keyword) }

    private fun parseStrictness(normalizedText: String): StrictnessLevel = when {
        normalizedText.contains("monk mode") ||
            normalizedText.contains("hard mode") ||
            normalizedText.contains("fully restricted") ||
            normalizedText.contains("locked") ||
            normalizedText.contains("no escape") -> StrictnessLevel.LOCKED
        normalizedText.contains("strict mode") ||
            normalizedText.contains("no entertainment") ||
            normalizedText.contains("strict") ||
            normalizedText.contains("no distraction") -> StrictnessLevel.STRICT
        normalizedText.contains("soft") || normalizedText.contains("gentle") ->
            StrictnessLevel.SOFT
        normalizedText.contains("smart") -> StrictnessLevel.SMART
        else -> DEFAULT_STRICTNESS
    }

    companion object {
        private const val DEFAULT_DURATION_MINUTES = 30
        private const val MINUTES_PER_DAY = 24 * 60
        private const val MINUTES_PER_YEAR = 365 * MINUTES_PER_DAY

        private const val PKG_YOUTUBE = "com.google.android.youtube"
        private const val PKG_CHROME = "com.android.chrome"
        private const val PKG_INSTAGRAM = "com.instagram.android"
        private const val PKG_TELEGRAM = "org.telegram.messenger"
        private const val PKG_WHATSAPP = "com.whatsapp"

        private val ALLOW_KEYWORDS = listOf(
            "study", "lecture", "docs", "telegram", "whatsapp", "coding", "code",
            "github", "stackoverflow", "compiler", "architecture", "course", "class",
            "assignment", "project", "exam", "neso", "message", "messages", "dm"
        )

        private val BLOCK_KEYWORDS = listOf(
            "reels", "reel", "shorts", "short", "porn", "adult", "movie", "netflix",
            "prime", "hotstar", "games", "game", "shopping", "amazon", "flipkart",
            "memes", "meme", "news", "entertainment", "feed"
        )

        private val CONTENT_COMPARISON_PATTERN = Regex(
            """(longer|greater|more|shorter|less)\s+than\s+(\d+)\s*(minutes?|mins?|hours?|hrs?)""",
            RegexOption.IGNORE_CASE
        )

        private val LENGTH_IS_PATTERN = Regex(
            """(?:whose\s+)?length\s+is\s+(?:greater|more|longer)\s+than\s+(\d+)\s*(minutes?|mins?|hours?|hrs?)""",
            RegexOption.IGNORE_CASE
        )

        private val CONTENT_GT_SYMBOL_PATTERN = Regex(
            """>\s*(\d+)\s*(minutes?|mins?|hours?|hrs?)""",
            RegexOption.IGNORE_CASE
        )

        private val CONTENT_COMPARE_CUES = Regex(
            """(?:longer|greater|more|shorter|less)\s+than|length\s+is|>\s*$""",
            RegexOption.IGNORE_CASE
        )

        private val ONLY_ALLOW_CUE = Regex(
            """\bonly\s+(?:allow\s+)?""",
            RegexOption.IGNORE_CASE
        )

        private val SESSION_FOR_PATTERN = Regex(
            """\bfor\s+(?:the\s+)?(?:next\s+)?(\d+)\s*(minutes?|mins?|hours?|hrs?|days?|years?)\b""",
            RegexOption.IGNORE_CASE
        )

        private val SESSION_NEXT_PATTERN = Regex(
            """\bnext\s+(\d+)\s*(minutes?|mins?|hours?|hrs?|days?|years?)\b""",
            RegexOption.IGNORE_CASE
        )

        private val SESSION_DAY_YEAR_PATTERN = Regex(
            """\b(\d+)\s*(days?|years?)\b""",
            RegexOption.IGNORE_CASE
        )

        private val HOUR_PATTERN = Regex("""\b(\d+)\s*(?:hours?|hrs?)\b""", RegexOption.IGNORE_CASE)
        private val MINUTE_PATTERN =
            Regex("""\b(\d+)\s*(?:minutes?|mins?)\b""", RegexOption.IGNORE_CASE)

        private val INSTAGRAM_MESSAGES_ONLY = Regex(
            """(?:instagram|insta).{0,40}(?:only|just).{0,20}(?:message|messages|dm|dms|chat|chats|repl)""",
            RegexOption.IGNORE_CASE
        )

        private val INSTA_LESS = Regex(
            """(?:use\s+)?(?:instagram|insta)\s+less|less\s+(?:instagram|insta)""",
            RegexOption.IGNORE_CASE
        )

        private val STRICT_VAGUE = Regex(
            """\b(?:be\s+)?strict(?:\s+mode)?\s+today\b|\btoday\b.{0,12}\bstrict\b|\bstrict\b.{0,12}\btoday\b""",
            RegexOption.IGNORE_CASE
        )

        private val MAKE_STRICT = Regex(
            """\bmake\s+me\s+strict\b|\bstrict\s+today\b|\bmake\s+me\s+strict\s+aaj\b""",
            RegexOption.IGNORE_CASE
        )

        private val FOCUS_VAGUE = Regex(
            """\bfocus\s+mode\b|\bstart\s+focus\b|\bfocus\s+please\b|\bfocus\s+mode\s+chahiye\b""",
            RegexOption.IGNORE_CASE
        )

        private val DEFAULT_STRICTNESS = StrictnessLevel.STRICT
    }
}
