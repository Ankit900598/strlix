package com.phonecodex.app.domain.promise

object PromiseIntentRules {

    fun blocksShortForm(goal: String): Boolean {
        val normalized = goal.lowercase()
        return SHORT_FORM_BLOCK_PHRASES.any { phrase -> normalized.contains(phrase) } ||
            STUDY_ONLY_PHRASES.any { phrase -> normalized.contains(phrase) } ||
            MONK_PHRASES.any { phrase -> normalized.contains(phrase) }
    }

    fun allowsShortForm(goal: String): Boolean {
        val normalized = goal.lowercase()
        return SHORT_FORM_ALLOW_PHRASES.any { phrase -> normalized.contains(phrase) } ||
            SHORT_FORM_QUOTA_REGEX.containsMatchIn(normalized)
    }

    fun allowsBroadChromeUse(goal: String): Boolean {
        val normalized = goal.lowercase()
        return normalized.contains("allow everything on chrome") ||
            normalized.contains("chrome allow everything") ||
            normalized.contains("anything on chrome") ||
            normalized.contains("everything in chrome")
    }

    private val STUDY_ONLY_PHRASES = listOf(
        "only study",
        "study only",
        "only lecture",
        "lecture only",
        "educational only",
        "only educational"
    )

    private val MONK_PHRASES = listOf(
        "monk",
        "no entertainment",
        "zero entertainment",
        "no distraction",
        "no timepass"
    )

    private val SHORT_FORM_BLOCK_PHRASES = listOf(
        "no shorts",
        "block shorts",
        "don't watch shorts",
        "dont watch shorts",
        "no reels",
        "block reels",
        "no short video",
        "block short video"
    )

    private val SHORT_FORM_ALLOW_PHRASES = listOf(
        "allow shorts",
        "shorts allowed",
        "can watch shorts",
        "allow reels",
        "reels allowed"
    )

    private val SHORT_FORM_QUOTA_REGEX =
        Regex("\\b(?:allow\\s*)?\\d+\\s*(?:shorts?|reels?|short\\s+videos?)\\b")
}
