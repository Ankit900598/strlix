package com.phonecodex.app.domain.enforcement

/**
 * Pulls href-like tokens from Accessibility strings already on screen:
 * Chrome omnibox, YouTube share sheets, pasted links.
 *
 * Local text parsing only. Does not fetch URLs, open them, screenshot the
 * page, or send video/audio to Azure. Silent AV capture is private-screen
 * surveillance and is never a default enforcement path.
 */
object AccessibilityUrlExtractor {

    /**
     * Host/path tokens that look like a video URL. Lowercased, trailing
     * punctuation stripped. Order is first-seen, duplicates removed.
     */
    fun extract(screenText: String): List<String> {
        if (screenText.isBlank()) return emptyList()
        val haystack = screenText.lowercase()
        val found = linkedSetOf<String>()
        for (match in URL_TOKEN_REGEX.findAll(haystack)) {
            val token = sanitize(match.value)
            if (token.isNotEmpty()) found += token
        }
        for (match in SHORT_PATH_REGEX.findAll(haystack)) {
            val token = sanitize(match.value)
            if (token.isNotEmpty()) found += token
        }
        return found.toList()
    }

    fun containsYouTubeUrl(screenText: String): Boolean =
        extract(screenText).any { isYouTubeHost(it) } ||
            YOUTUBE_HOST_INLINE.containsMatchIn(screenText.lowercase())

    fun isYouTubeHost(url: String): Boolean {
        val token = sanitize(url)
        return token.contains("youtube.com") ||
            token.contains("youtu.be") ||
            token.contains("youtube-nocookie.com")
    }

    fun containsYouTubeShortsUrl(screenText: String): Boolean =
        extract(screenText).any { isYouTubeShortsUrl(it) } ||
            YOUTUBE_SHORTS_INLINE.containsMatchIn(screenText.lowercase())

    fun containsInstagramReelUrl(screenText: String, packageName: String): Boolean {
        val urls = extract(screenText)
        val onInstagram = VideoPlatformRegistry.isInstagram(packageName) ||
            urls.any { it.contains("instagram.com") || it.contains("instagr.am") }
        if (!onInstagram) return false
        if (urls.any { isInstagramReelUrl(it) }) return true
        return VideoPlatformRegistry.isInstagram(packageName) &&
            INSTAGRAM_REEL_PATH.containsMatchIn(screenText.lowercase())
    }

    fun containsShortFormVideoUrl(screenText: String, packageName: String): Boolean =
        containsYouTubeShortsUrl(screenText) ||
            containsInstagramReelUrl(screenText, packageName)

    /**
     * `/shorts/` and `youtube.com/shorts` are Shorts.
     * Bare `youtu.be/ID` is a generic shortener (lecture or Short) — only
     * treat as Shorts when the query says `feature=shorts`.
     */
    fun isYouTubeShortsUrl(url: String): Boolean {
        val token = sanitize(url)
        if (token.contains("/shorts/") ||
            token.contains("youtube.com/shorts") ||
            token.contains("youtu.be/shorts")
        ) {
            return true
        }
        return isYoutuBeHost(token) && YOUTU_BE_SHORTS_QUERY.containsMatchIn(token)
    }

    fun isInstagramReelUrl(url: String): Boolean =
        INSTAGRAM_REEL_PATH.containsMatchIn(sanitize(url))

    private fun isYoutuBeHost(url: String): Boolean =
        url.contains("youtu.be/") || url.startsWith("youtu.be")

    private fun sanitize(raw: String): String =
        raw.trim().trimEnd(')', ']', '}', ',', '.', ';', '!', '?', '"', '\'', '»')

    /** youtube.com / youtu.be / instagram.com tokens including query strings. */
    private val URL_TOKEN_REGEX = Regex(
        """(?:https?://)?(?:www\.)?(?:m\.)?(?:youtube\.com|youtu\.be|instagram\.com|instagr\.am)[^\s<>"'|]+"""
    )

    /** Path-only hrefs: `/shorts/ID`, `/reel/ID`, `/reels/ID`. */
    private val SHORT_PATH_REGEX = Regex(
        """/(?:shorts|reels?)/[a-zA-Z0-9_-]+"""
    )

    private val YOUTUBE_HOST_INLINE = Regex(
        """(?:^|[^\w])(?:(?:m|music|www)\.)?(?:youtube\.com|youtu\.be|youtube-nocookie\.com)\b"""
    )

    private val YOUTUBE_SHORTS_INLINE = Regex(
        """(?:youtube\.com/shorts|/shorts/)"""
    )

    private val YOUTU_BE_SHORTS_QUERY = Regex(
        """[?&](?:feature=shorts|shorts=1)\b"""
    )

    private val INSTAGRAM_REEL_PATH = Regex(
        """/(?:reel|reels)/"""
    )
}
