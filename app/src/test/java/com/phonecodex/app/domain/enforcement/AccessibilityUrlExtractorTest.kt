package com.phonecodex.app.domain.enforcement

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AccessibilityUrlExtractorTest {

    @Test
    fun extractsChromeOmniboxAndPathTokens() {
        val urls = AccessibilityUrlExtractor.extract(
            "Address bar https://www.youtube.com/shorts/dQw4w9WgXcQ " +
                "also /shorts/abcXYZ12"
        )
        assertTrue(urls.any { AccessibilityUrlExtractor.isYouTubeShortsUrl(it) })
        assertTrue(AccessibilityUrlExtractor.containsYouTubeShortsUrl(
            "youtube.com/shorts/dQw4w9WgXcQ"
        ))
    }

    @Test
    fun youtubeShortsHostWithoutTrailingSlash_isShorts() {
        assertTrue(
            AccessibilityUrlExtractor.containsYouTubeShortsUrl(
                "https://m.youtube.com/shorts"
            )
        )
    }

    @Test
    fun youtuBeWithoutShortsQuery_isNotShortsUrl() {
        assertFalse(
            AccessibilityUrlExtractor.isYouTubeShortsUrl("https://youtu.be/abcdefghijk")
        )
        assertFalse(
            AccessibilityUrlExtractor.containsYouTubeShortsUrl(
                "Address bar https://youtu.be/abcdefghijk"
            )
        )
    }

    @Test
    fun youtuBeFeatureShorts_isShortsUrl() {
        assertTrue(
            AccessibilityUrlExtractor.isYouTubeShortsUrl(
                "https://youtu.be/abcXYZ12?feature=shorts"
            )
        )
    }

    @Test
    fun instagramReelPath_onlyWhenOnIg() {
        val reel = "https://www.instagram.com/reels/CxyzABC123"
        assertTrue(AccessibilityUrlExtractor.isInstagramReelUrl(reel))
        assertTrue(
            AccessibilityUrlExtractor.containsInstagramReelUrl(
                reel,
                VideoPlatformRegistry.INSTAGRAM
            )
        )
        assertFalse(
            AccessibilityUrlExtractor.containsInstagramReelUrl(
                "Explore Reels shelf Profile",
                VideoPlatformRegistry.INSTAGRAM
            )
        )
        assertTrue(
            AccessibilityUrlExtractor.containsInstagramReelUrl(
                reel,
                VideoPlatformRegistry.CHROME
            )
        )
    }

    @Test
    fun youtubeWatchAndYoutuBe_areYouTubeHosts() {
        assertTrue(
            AccessibilityUrlExtractor.containsYouTubeUrl(
                "Address bar https://www.youtube.com/watch?v=abcdefghijk"
            )
        )
        assertTrue(AccessibilityUrlExtractor.isYouTubeHost("https://youtu.be/abcdefghijk"))
        assertFalse(
            AccessibilityUrlExtractor.containsYouTubeUrl(
                "https://mail.google.com/mail Inbox"
            )
        )
    }

    @Test
    fun homeNavWordShorts_isNotAShortsUrl() {
        assertFalse(
            AccessibilityUrlExtractor.containsYouTubeShortsUrl(
                "Home Shorts Subscriptions Library"
            )
        )
    }
}
