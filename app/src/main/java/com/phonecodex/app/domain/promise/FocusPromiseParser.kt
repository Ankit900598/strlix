package com.phonecodex.app.domain.promise

import com.phonecodex.app.domain.model.AppRule
import com.phonecodex.app.domain.model.AppRuleBehavior
import com.phonecodex.app.domain.model.FocusPromise
import com.phonecodex.app.domain.model.StrictnessLevel

class FocusPromiseParser {

    fun parse(rawText: String): FocusPromise {
        val normalizedText = rawText.trim().lowercase()

        return FocusPromise(
            rawText = rawText.trim(),
            durationMinutes = parseDurationMinutes(normalizedText),
            allowedKeywords = findKeywords(normalizedText, ALLOW_KEYWORDS),
            blockedKeywords = findKeywords(normalizedText, BLOCK_KEYWORDS),
            strictness = parseStrictness(normalizedText),
            suggestedAppRules = parseSuggestedAppRules(normalizedText)
        )
    }

    private fun parseSuggestedAppRules(normalizedText: String): List<AppRule> {
        val suggestions = mutableListOf<AppRule>()

        if (normalizedText.contains("telegram")) {
            suggestions.add(
                AppRule(
                    packageName = "org.telegram.messenger",
                    label = "Telegram",
                    behavior = AppRuleBehavior.WARN
                )
            )
        }
        if (normalizedText.contains("whatsapp")) {
            suggestions.add(
                AppRule(
                    packageName = "com.whatsapp",
                    label = "WhatsApp",
                    behavior = AppRuleBehavior.WARN
                )
            )
        }
        if (normalizedText.contains("youtube") || normalizedText.contains("lecture")) {
            suggestions.add(
                AppRule(
                    packageName = "com.google.android.youtube",
                    label = "YouTube",
                    behavior = AppRuleBehavior.AI_DECIDE
                )
            )
        }
        if (
            normalizedText.contains("chrome") ||
            normalizedText.contains("docs") ||
            normalizedText.contains("browser")
        ) {
            suggestions.add(
                AppRule(
                    packageName = "com.android.chrome",
                    label = "Chrome",
                    behavior = AppRuleBehavior.AI_DECIDE
                )
            )
        }
        if (normalizedText.contains("instagram") || normalizedText.contains("reels")) {
            suggestions.add(
                AppRule(
                    packageName = "com.instagram.android",
                    label = "Instagram",
                    behavior = AppRuleBehavior.BLOCK
                )
            )
        }

        return suggestions.distinctBy { it.packageName }
    }

    private fun parseDurationMinutes(normalizedText: String): Int {
        HOUR_PATTERN.find(normalizedText)?.let { match ->
            val hours = match.groupValues[1].toIntOrNull() ?: return DEFAULT_DURATION_MINUTES
            return hours * 60
        }

        MINUTE_PATTERN.find(normalizedText)?.let { match ->
            return match.groupValues[1].toIntOrNull() ?: DEFAULT_DURATION_MINUTES
        }

        return DEFAULT_DURATION_MINUTES
    }

    private fun findKeywords(normalizedText: String, keywords: List<String>): List<String> {
        return keywords.filter { keyword -> normalizedText.contains(keyword) }
    }

    private fun parseStrictness(normalizedText: String): StrictnessLevel {
        return when {
            normalizedText.contains("monk mode") ||
                normalizedText.contains("hard mode") ||
                normalizedText.contains("fully restricted") ||
                normalizedText.contains("locked") ||
                normalizedText.contains("no escape") -> {
                StrictnessLevel.LOCKED
            }
            normalizedText.contains("strict mode") ||
                normalizedText.contains("no entertainment") ||
                normalizedText.contains("strict") ||
                normalizedText.contains("no distraction") -> {
                StrictnessLevel.STRICT
            }
            normalizedText.contains("soft") || normalizedText.contains("gentle") -> {
                StrictnessLevel.SOFT
            }
            normalizedText.contains("smart") -> {
                StrictnessLevel.SMART
            }
            else -> DEFAULT_STRICTNESS
        }
    }

    companion object {
        private const val DEFAULT_DURATION_MINUTES = 30

        private val ALLOW_KEYWORDS = listOf(
            "study",
            "lecture",
            "docs",
            "telegram",
            "whatsapp",
            "coding",
            "code",
            "github",
            "stackoverflow",
            "compiler",
            "architecture",
            "course",
            "class",
            "assignment",
            "project",
            "exam"
        )

        private val BLOCK_KEYWORDS = listOf(
            "reels",
            "reel",
            "shorts",
            "short",
            "porn",
            "adult",
            "movie",
            "netflix",
            "prime",
            "hotstar",
            "games",
            "game",
            "shopping",
            "amazon",
            "flipkart",
            "memes",
            "meme",
            "news",
            "entertainment"
        )

        private val HOUR_PATTERN = Regex("\\b(\\d+)\\s*(?:hours?|hrs?)\\b")
        private val MINUTE_PATTERN = Regex("\\b(\\d+)\\s*(?:minutes?|mins?)\\b")

        private val DEFAULT_STRICTNESS = StrictnessLevel.STRICT
    }
}
