package com.phonecodex.app.domain.promise

object PromiseIntentRules {

    fun blocksShortForm(goal: String): Boolean {
        val normalized = goal.lowercase()
        // Long-video thresholds alone must not imply a Shorts ban.
        if (hasLongYouTubeLimit(normalized) &&
            SHORT_FORM_BLOCK_PHRASES.none { phrase -> normalized.contains(phrase) } &&
            STUDY_ONLY_PHRASES.none { phrase -> normalized.contains(phrase) } &&
            MONK_PHRASES.none { phrase -> normalized.contains(phrase) }
        ) {
            return false
        }
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

    fun hasLongYouTubeLimit(goal: String): Boolean {
        val normalized = goal.lowercase()
        return normalized.contains("youtube") &&
            LONG_VIDEO_LIMIT_REGEX.containsMatchIn(normalized)
    }

    fun isYouTubeSurfaceInChrome(screenText: String): Boolean {
        val normalized = screenText.lowercase()
        return normalized.contains("youtube") ||
            normalized.contains("youtu.be") ||
            normalized.contains("youtube.com") ||
            normalized.contains("hide player controls") ||
            normalized.contains("show player controls")
    }

    fun chromeYouTubeVideoExceedsGoalLimit(goal: String, screenText: String): Boolean {
        val limitMinutes = extractGoalLongVideoLimitMinutes(goal) ?: return false
        val videoMinutes = extractScreenVideoDurationMinutes(screenText) ?: return false
        return videoMinutes > limitMinutes
    }

    fun needsMoreChromeYouTubeDurationText(goal: String, screenText: String): Boolean {
        return hasLongYouTubeLimit(goal) &&
            isYouTubeSurfaceInChrome(screenText) &&
            extractScreenVideoDurationMinutes(screenText) == null
    }

    /** Drive / Docs / Gmail — allow unless the promise names them as blocked. */
    fun isUnrelatedProductivityPackage(packageName: String, goal: String): Boolean {
        if (packageName !in PRODUCTIVITY_PACKAGES) return false
        val normalized = goal.lowercase()
        val blocksDocs = (normalized.contains("block") || normalized.contains("no ")) &&
            (normalized.contains("docs") || normalized.contains("drive") ||
                normalized.contains("gmail"))
        return !blocksDocs
    }

    private val PRODUCTIVITY_PACKAGES = setOf(
        "com.google.android.apps.docs",
        "com.google.android.apps.docs.editors.docs",
        "com.google.android.apps.docs.editors.sheets",
        "com.google.android.apps.docs.editors.slides",
        "com.google.android.apps.drive",
        "com.google.android.gm"
    )

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

    private val LONG_VIDEO_LIMIT_REGEX =
        Regex(
            "\\b(?:greater than|more than|over|longer than|above|" +
                "length\\s+is\\s+(?:greater|more|longer)\\s+than)\\s*\\d+\\s*" +
                "(?:min|mins|minutes?|hrs?|hours?)\\b"
        )

    private val GOAL_LIMIT_REGEX =
        Regex(
            "\\b(?:greater than|more than|over|longer than|above|" +
                "length\\s+is\\s+(?:greater|more|longer)\\s+than)\\s*(\\d+)\\s*" +
                "(min|mins|minutes?|hrs?|hours?)\\b"
        )

    private val SCREEN_HOUR_DURATION_REGEX =
        Regex(
            "\\b(?:time duration\\s*)?(\\d+)\\s*(?:hours?|hrs?)\\s*(\\d+)?\\s*" +
                "(?:minutes?|mins?)?\\b"
        )

    private val SCREEN_MINUTE_DURATION_REGEX =
        Regex("\\b(?:time duration\\s*)?(\\d+)\\s*(?:minutes?|mins?)\\b")

    private val CLOCK_DURATION_REGEX =
        Regex("\\b(\\d{1,2}):(\\d{2})(?::(\\d{2}))?\\b")

    private fun extractGoalLongVideoLimitMinutes(goal: String): Int? {
        val match = GOAL_LIMIT_REGEX.find(goal.lowercase()) ?: return null
        val amount = match.groupValues[1].toIntOrNull() ?: return null
        val unit = match.groupValues[2]
        return if (unit.startsWith("h")) amount * 60 else amount
    }

    private fun extractScreenVideoDurationMinutes(screenText: String): Int? {
        val normalized = screenText.lowercase()
        SCREEN_HOUR_DURATION_REGEX.find(normalized)?.let { match ->
            val hours = match.groupValues[1].toIntOrNull() ?: return@let
            val minutes = match.groupValues.getOrNull(2)?.toIntOrNull() ?: 0
            return hours * 60 + minutes
        }
        SCREEN_MINUTE_DURATION_REGEX.find(normalized)?.let { match ->
            return match.groupValues[1].toIntOrNull()
        }
        CLOCK_DURATION_REGEX.findAll(normalized)
            .mapNotNull { match ->
                val first = match.groupValues[1].toIntOrNull() ?: return@mapNotNull null
                val second = match.groupValues[2].toIntOrNull() ?: return@mapNotNull null
                val third = match.groupValues.getOrNull(3)?.toIntOrNull()
                if (third != null) first * 60 + second else first
            }
            .maxOrNull()
            ?.let { return it }
        return null
    }
}
