package com.phonecodex.app.domain.signals

import com.phonecodex.app.domain.model.ContentSignals

class ContentSignalDetector {

    fun detect(packageName: String, screenText: String): ContentSignals {
        val matchedSignals = mutableListOf<String>()
        val normalizedText = screenText.lowercase()

        val isYouTubeShorts = packageName == YOUTUBE_PACKAGE &&
            detectYouTubeShortsBlock(normalizedText, matchedSignals)

        val isLikelySearchOrLecture = packageName == YOUTUBE_PACKAGE &&
            detectYouTubeStudyLikeContent(normalizedText, matchedSignals)

        val isChromeAdultOrPorn = packageName == CHROME_PACKAGE &&
            detectChromeAdultContent(normalizedText, matchedSignals)

        val isChromeStudyLike = packageName == CHROME_PACKAGE &&
            detectChromeStudyLikeContent(normalizedText, matchedSignals)

        return ContentSignals(
            isYouTubeShorts = isYouTubeShorts,
            isLikelySearchOrLecture = isLikelySearchOrLecture,
            isChromeAdultOrPorn = isChromeAdultOrPorn,
            isChromeStudyLike = isChromeStudyLike,
            matchedSignals = matchedSignals
        )
    }

    private fun detectYouTubeShortsBlock(
        normalizedText: String,
        matchedSignals: MutableList<String>
    ): Boolean {
        val strongSignals = findStrongYouTubeShortsSignals(normalizedText)
        if (strongSignals.isNotEmpty()) {
            strongSignals.forEach { signal ->
                matchedSignals.add("youtube_shorts_strong:$signal")
            }
            return true
        }

        findWeakYouTubeShortsSignals(normalizedText).forEach { signal ->
            matchedSignals.add("youtube_shorts_weak:$signal")
        }
        return false
    }

    private fun findStrongYouTubeShortsSignals(normalizedText: String): List<String> {
        val strongSignals = mutableListOf<String>()

        SHORTS_PLAYER_KEYWORDS.forEach { keyword ->
            if (normalizedText.contains(keyword)) {
                strongSignals.add(keyword.replace(' ', '_'))
            }
        }

        if (normalizedText.contains("/shorts/")) {
            strongSignals.add("/shorts/")
        }

        val hasPlayerAction = strongSignals.isNotEmpty()
        val shortsNavSelected = SHORTS_NAV_SELECTED_PATTERNS.any { pattern ->
            pattern.containsMatchIn(normalizedText)
        }
        if (shortsNavSelected && (normalizedText.contains("/shorts/") || hasPlayerAction)) {
            strongSignals.add("shorts_navigation_selected")
        }

        return strongSignals.distinct()
    }

    private fun findWeakYouTubeShortsSignals(normalizedText: String): List<String> {
        val weakSignals = mutableListOf<String>()

        if (containsShortsWord(normalizedText)) {
            weakSignals.add("shorts_word")
        }
        if (normalizedText.contains("#shorts")) {
            weakSignals.add("#shorts")
        }
        if (SHORT_DURATION_PATTERNS.any { pattern -> pattern.containsMatchIn(normalizedText) }) {
            weakSignals.add("short_duration")
        }
        if (SHORTS_NAV_SELECTED_PATTERNS.any { pattern -> pattern.containsMatchIn(normalizedText) }) {
            weakSignals.add("shorts_navigation_selected")
        }
        if (looksLikeShortsShelf(normalizedText)) {
            weakSignals.add("shorts_shelf")
        }

        return weakSignals.distinct()
    }

    private fun containsShortsWord(normalizedText: String): Boolean {
        return SHORTS_WORD_PATTERN.containsMatchIn(normalizedText)
    }

    private fun looksLikeShortsShelf(normalizedText: String): Boolean {
        return containsShortsWord(normalizedText) &&
            YOUTUBE_HOME_SHELF_KEYWORDS.any { keyword -> normalizedText.contains(keyword) }
    }

    private fun detectYouTubeStudyLikeContent(
        normalizedText: String,
        matchedSignals: MutableList<String>
    ): Boolean {
        var matched = false

        YOUTUBE_STUDY_LIKE_KEYWORDS.forEach { keyword ->
            if (normalizedText.contains(keyword)) {
                matchedSignals.add("youtube_study_like:$keyword")
                matched = true
            }
        }

        return matched
    }

    private fun detectChromeAdultContent(
        normalizedText: String,
        matchedSignals: MutableList<String>
    ): Boolean {
        var matched = false

        CHROME_ADULT_KEYWORDS.forEach { keyword ->
            if (normalizedText.contains(keyword)) {
                matchedSignals.add("chrome_adult:$keyword")
                matched = true
            }
        }

        return matched
    }

    private fun detectChromeStudyLikeContent(
        normalizedText: String,
        matchedSignals: MutableList<String>
    ): Boolean {
        var matched = false

        CHROME_STUDY_LIKE_KEYWORDS.forEach { keyword ->
            if (normalizedText.contains(keyword)) {
                matchedSignals.add("chrome_study_like:$keyword")
                matched = true
            }
        }

        return matched
    }

    companion object {
        private const val YOUTUBE_PACKAGE = "com.google.android.youtube"
        private const val CHROME_PACKAGE = "com.android.chrome"

        private val SHORTS_WORD_PATTERN = Regex("\\bshorts\\b")

        private val SHORTS_NAV_SELECTED_PATTERNS = listOf(
            Regex("shorts.*selected"),
            Regex("selected.*shorts")
        )

        private val SHORT_DURATION_PATTERNS = listOf(
            Regex("\\b0:\\d{2}\\b"),
            Regex("\\b0 minutes?\\b")
        )

        private val SHORTS_PLAYER_KEYWORDS = listOf(
            "remix this short",
            "use this sound",
            "see more videos using this sound",
            "swipe up"
        )

        private val YOUTUBE_HOME_SHELF_KEYWORDS = listOf(
            "home",
            "subscriptions",
            "explore",
            "recommended",
            "for you",
            "mix",
            "continue watching"
        )

        private val YOUTUBE_STUDY_LIKE_KEYWORDS = listOf(
            "lecture",
            "course",
            "tutorial",
            "playlist",
            "search",
            "documentation",
            "math",
            "dsa",
            "algorithm"
        )

        private val CHROME_ADULT_KEYWORDS = listOf(
            "porn",
            "xxx",
            "sex",
            "nude",
            "onlyfans",
            "adult",
            "xvideos",
            "pornhub"
        )

        private val CHROME_STUDY_LIKE_KEYWORDS = listOf(
            "docs",
            "documentation",
            "tutorial",
            "course",
            "lecture",
            "math",
            "dsa",
            "algorithm",
            "stackoverflow",
            "github",
            "compiler",
            "architecture"
        )
    }
}
