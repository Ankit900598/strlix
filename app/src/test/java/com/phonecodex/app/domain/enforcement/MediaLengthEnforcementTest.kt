package com.phonecodex.app.domain.enforcement

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import com.phonecodex.app.domain.promise.PromiseIntentRules

class MediaLengthEnforcementTest {

    private val lengthPromise =
        "for 1 hour do not allow to watch any video whose length is greater than 40 min"

    private val minLengthPromise =
        "do not allow videos shorter than 30 minutes for next 1 hour"

    @Test
    fun normalChromePage_passes_underLengthOnlyPromise() {
        val decision = MediaLengthEnforcement.decide(
            packageName = MediaLengthEnforcement.CHROME_PACKAGE,
            goal = lengthPromise,
            screenText = "Wikipedia Android (operating system) Edit Search",
            structuredMaxBlockMinutes = 40
        )
        assertEquals(MediaLengthLocalDecision.PASS, decision)
    }

    @Test
    fun chromeGoogleResults_withVideosTab_doesNotBlock() {
        val screenText =
            "Google Search Videos Short videos Images Shopping All filters " +
                "About 1,200,000 results YouTube 1 hour 25 minutes some channel"
        assertFalse(PromiseIntentRules.isActiveVideoPlayerSurface(screenText))
        val decision = MediaLengthEnforcement.decide(
            packageName = MediaLengthEnforcement.CHROME_PACKAGE,
            goal = lengthPromise,
            screenText = screenText,
            structuredMaxBlockMinutes = 40
        )
        assertEquals(MediaLengthLocalDecision.PASS, decision)
        assertFalse(
            PromiseIntentRules.chromeYouTubeVideoExceedsGoalLimit(
                goal = lengthPromise,
                screenText = screenText,
                structuredMaxBlockMinutes = 40
            )
        )
    }

    @Test
    fun chromeHomepage_incognitoProfileTiles_doesNotBlock() {
        val screenText =
            "Google New incognito tab Profile Other bookmarks Chrome tips " +
                "Art and photos Short videos"
        val decision = MediaLengthEnforcement.decide(
            packageName = MediaLengthEnforcement.CHROME_PACKAGE,
            goal = lengthPromise,
            screenText = screenText,
            structuredMaxBlockMinutes = 40
        )
        assertEquals(MediaLengthLocalDecision.PASS, decision)
    }

    @Test
    fun chromeYouTube_overLimit_blocks() {
        val decision = MediaLengthEnforcement.decide(
            packageName = MediaLengthEnforcement.CHROME_PACKAGE,
            goal = lengthPromise,
            screenText = "Hide player controls Time duration 1 hour 25 minutes YouTube",
            structuredMaxBlockMinutes = 40
        )
        assertEquals(MediaLengthLocalDecision.BLOCK, decision)
    }

    @Test
    fun chromeYouTube_underLimit_allows() {
        val decision = MediaLengthEnforcement.decide(
            packageName = MediaLengthEnforcement.CHROME_PACKAGE,
            goal = lengthPromise,
            screenText = "Hide player controls Time duration 12 minutes YouTube",
            structuredMaxBlockMinutes = 40
        )
        assertEquals(MediaLengthLocalDecision.ALLOW, decision)
    }

    @Test
    fun chromeYouTube_withoutDuration_waits() {
        val decision = MediaLengthEnforcement.decide(
            packageName = MediaLengthEnforcement.CHROME_PACKAGE,
            goal = lengthPromise,
            screenText = "Hide player controls Search YouTube Playback Settings",
            structuredMaxBlockMinutes = 40
        )
        assertEquals(MediaLengthLocalDecision.WAIT, decision)
    }

    @Test
    fun chromeWatchUrl_withLongDuration_blocks() {
        val decision = MediaLengthEnforcement.decide(
            packageName = MediaLengthEnforcement.CHROME_PACKAGE,
            goal = lengthPromise,
            screenText = "youtube.com/watch?v=abc123 Time duration 1 hour 10 minutes",
            structuredMaxBlockMinutes = 40
        )
        assertEquals(MediaLengthLocalDecision.BLOCK, decision)
    }

    @Test
    fun nativeYouTube_overLimit_blocks() {
        val decision = MediaLengthEnforcement.decide(
            packageName = MediaLengthEnforcement.YOUTUBE_PACKAGE,
            goal = lengthPromise,
            screenText = "Time duration 2 hours 5 minutes Subscribe Share",
            structuredMaxBlockMinutes = 40
        )
        assertEquals(MediaLengthLocalDecision.BLOCK, decision)
    }

    @Test
    fun nativeYouTube_withoutDuration_waits_notAi() {
        val decision = MediaLengthEnforcement.decide(
            packageName = MediaLengthEnforcement.YOUTUBE_PACKAGE,
            goal = lengthPromise,
            screenText = "Hide player controls Search Playback Settings",
            structuredMaxBlockMinutes = 40
        )
        assertEquals(MediaLengthLocalDecision.WAIT, decision)
    }

    @Test
    fun nativeYouTubeHome_returnsPass_notWarn() {
        val decision = MediaLengthEnforcement.decide(
            packageName = MediaLengthEnforcement.YOUTUBE_PACKAGE,
            goal = lengthPromise,
            screenText = "Home Shorts Subscriptions Library",
            structuredMaxBlockMinutes = 40
        )
        assertEquals(MediaLengthLocalDecision.PASS, decision)
    }

    @Test
    fun nativeYouTubeSearch_withThumbnailDurations_doesNotBlock() {
        val screenText =
            "Search results 1:25:30 45 minutes 12:04 Home Shorts Library"
        assertFalse(PromiseIntentRules.isActiveVideoPlayerSurface(screenText))
        val decision = MediaLengthEnforcement.decide(
            packageName = MediaLengthEnforcement.YOUTUBE_PACKAGE,
            goal = lengthPromise,
            screenText = screenText,
            structuredMaxBlockMinutes = 40
        )
        assertEquals(MediaLengthLocalDecision.PASS, decision)
    }

    @Test
    fun bareYouTubeWord_isNotActivePlayer() {
        assertFalse(
            PromiseIntentRules.isActiveVideoPlayerSurface(
                "Google Search Videos Short videos youtube.com results"
            )
        )
        assertTrue(
            PromiseIntentRules.isActiveVideoPlayerSurface(
                "Hide player controls YouTube"
            )
        )
    }

    @Test
    fun newPipe_overLimit_blocks() {
        val decision = MediaLengthEnforcement.decide(
            packageName = VideoPlatformRegistry.NEWPIPE,
            goal = lengthPromise,
            screenText = "Play Pause 00:10 / 55:00 Related",
            structuredMaxBlockMinutes = 40
        )
        assertEquals(MediaLengthLocalDecision.BLOCK, decision)
    }

    @Test
    fun newPipe_underLimit_allows() {
        val decision = MediaLengthEnforcement.decide(
            packageName = VideoPlatformRegistry.NEWPIPE,
            goal = lengthPromise,
            screenText = "Play Pause 00:10 / 12:00 Related",
            structuredMaxBlockMinutes = 40
        )
        assertEquals(MediaLengthLocalDecision.ALLOW, decision)
    }

    @Test
    fun noLengthPromise_returnsNone() {
        val decision = MediaLengthEnforcement.decide(
            packageName = MediaLengthEnforcement.CHROME_PACKAGE,
            goal = "study mode for 1 hour no shorts",
            screenText = "Wikipedia Android",
            structuredMaxBlockMinutes = null
        )
        assertEquals(MediaLengthLocalDecision.NONE, decision)
    }

    @Test
    fun minLengthFloor_activeShortWithoutClock_blocks() {
        val decision = MediaLengthEnforcement.decide(
            packageName = VideoPlatformRegistry.YOUTUBE,
            goal = "allow only videos longer than 40 minutes for 1 hrs",
            screenText = "Home Shorts Subscriptions Remix this short Pause",
            structuredMaxBlockMinutes = null,
            structuredMinBlockMinutes = 40
        )
        assertEquals(MediaLengthLocalDecision.BLOCK, decision)
    }

    @Test
    fun shorterThanPromise_isMediaLengthLimit() {
        assertTrue(PromiseIntentRules.hasMediaLengthLimit(minLengthPromise))
        assertEquals(30, PromiseIntentRules.extractGoalMinVideoLimitMinutes(minLengthPromise))
    }

    @Test
    fun chromeYouTubeHome_shorterThanPromise_passes() {
        val screen =
            "YouTube Home Search Shorts Subscriptions You Explore Podcasts " +
                "Intelligence Zscaler’s Jay Chaudhry… 52 minutes"
        assertEquals(
            MediaLengthLocalDecision.PASS,
            MediaLengthEnforcement.decide(
                MediaLengthEnforcement.CHROME_PACKAGE,
                minLengthPromise,
                screen,
                structuredMaxBlockMinutes = null,
                structuredMinBlockMinutes = null
            )
        )
    }

    @Test
    fun chromeWatch_activeTitle_withOnlyRecommendationDurations_waitsNotBlocks() {
        val screen =
            "m.youtube.com/watch?v=abc " +
                "Chip design from the bottom up – Reiner Pope " +
                "Show player controls " +
                "Can This Vibe Coder... 8 minutes 55 seconds " +
                "Andrew Tate... 4 minutes 48 seconds " +
                "Introducing GPT-6 Astra... 2 minutes 43 seconds"
        val detailed = MediaLengthEnforcement.decideDetailed(
            packageName = MediaLengthEnforcement.CHROME_PACKAGE,
            goal = minLengthPromise,
            screenText = screen,
            structuredMaxBlockMinutes = null,
            structuredMinBlockMinutes = 30
        )
        assertEquals(MediaLengthLocalDecision.WAIT, detailed.decision)
        assertEquals(DurationSource.RECOMMENDATION_IGNORED, detailed.durationSource)
        assertNull(detailed.currentPlayerDurationSeconds)
    }

    @Test
    fun activePlayer_clockUnderMin_blocks() {
        assertEquals(
            MediaLengthLocalDecision.BLOCK,
            MediaLengthEnforcement.decide(
                packageName = VideoPlatformRegistry.NEWPIPE,
                goal = minLengthPromise,
                screenText = "Play Pause 00:15 / 00:59",
                structuredMaxBlockMinutes = null,
                structuredMinBlockMinutes = 30
            )
        )
    }

    @Test
    fun activePlayer_clockOverMin_allows() {
        assertEquals(
            MediaLengthLocalDecision.ALLOW,
            MediaLengthEnforcement.decide(
                packageName = VideoPlatformRegistry.NEWPIPE,
                goal = minLengthPromise,
                screenText = "Play Pause 00:10 / 52:00",
                structuredMaxBlockMinutes = null,
                structuredMinBlockMinutes = 30
            )
        )
    }

    @Test
    fun rematerializedChromeScope_doesNotEnforceOnYouTube() {
        val player = "Hide player controls Time duration 1 hour 25 minutes YouTube"
        assertEquals(
            MediaLengthLocalDecision.NONE,
            MediaLengthEnforcement.decide(
                packageName = VideoPlatformRegistry.YOUTUBE,
                goal = lengthPromise,
                screenText = player,
                structuredMaxBlockMinutes = 40,
                enforcementScopePackages = listOf(VideoPlatformRegistry.CHROME)
            )
        )
        assertEquals(
            MediaLengthLocalDecision.BLOCK,
            MediaLengthEnforcement.decide(
                packageName = VideoPlatformRegistry.CHROME,
                goal = lengthPromise,
                screenText = player,
                structuredMaxBlockMinutes = 40,
                enforcementScopePackages = listOf(VideoPlatformRegistry.CHROME)
            )
        )
    }

    @Test
    fun rematerializedYouTubeScope_doesNotEnforceOnChrome() {
        val player = "Hide player controls Time duration 1 hour 25 minutes YouTube"
        assertEquals(
            MediaLengthLocalDecision.NONE,
            MediaLengthEnforcement.decide(
                packageName = VideoPlatformRegistry.CHROME,
                goal = lengthPromise,
                screenText = player,
                structuredMaxBlockMinutes = 40,
                enforcementScopePackages = listOf(VideoPlatformRegistry.YOUTUBE)
            )
        )
        assertEquals(
            MediaLengthLocalDecision.BLOCK,
            MediaLengthEnforcement.decide(
                packageName = VideoPlatformRegistry.YOUTUBE,
                goal = lengthPromise,
                screenText = player,
                structuredMaxBlockMinutes = 40,
                enforcementScopePackages = listOf(VideoPlatformRegistry.YOUTUBE)
            )
        )
    }
}
