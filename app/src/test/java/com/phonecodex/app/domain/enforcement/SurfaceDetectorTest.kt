package com.phonecodex.app.domain.enforcement

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class SurfaceDetectorTest {

    @Test
    fun chromeSearchVideosTab_isSearch_notPlayer() {
        val text =
            "Google Search Videos Short videos Images Shopping All filters " +
                "About 1,200,000 results YouTube 1 hour 25 minutes"
        val detection = SurfaceDetector.detect(VideoPlatformRegistry.CHROME, text)
        assertEquals(SurfaceDetectionResult.SEARCH, detection.surface)
        assertFalse(detection.isActivePlayer)
    }

    @Test
    fun youtubeRemixShort_isActiveShortPlayer_notHome() {
        val detection = SurfaceDetector.detect(
            VideoPlatformRegistry.YOUTUBE,
            "Home Shorts Subscriptions Remix this short Pause like comment"
        )
        assertEquals(SurfaceDetectionResult.SHORT_FORM_PLAYER, detection.surface)
        assertTrue(detection.isActivePlayer)
        assertTrue(detection.isShortFormPlay)
    }

    @Test
    fun youtubeHome_isHome_notPlayer() {
        val detection = SurfaceDetector.detect(
            VideoPlatformRegistry.YOUTUBE,
            "Home Shorts Subscriptions Library"
        )
        assertEquals(SurfaceDetectionResult.HOME, detection.surface)
        assertFalse(detection.isActivePlayer)
        assertTrue(detection.isPassive)
    }

    @Test
    fun chromeYouTubeHome_withRecDuration_isPassiveNotPlayer() {
        val text =
            "YouTube Home Search Shorts Subscriptions You Explore Podcasts " +
                "Intelligence Zscaler’s Jay Chaudhry… 52 minutes"
        val detection = SurfaceDetector.detect(VideoPlatformRegistry.CHROME, text)
        assertTrue(detection.isPassive)
        assertFalse(detection.isActivePlayer)
    }

    @Test
    fun youtubeFullscreenPlayer_isActivePlayer() {
        val detection = SurfaceDetector.detect(
            VideoPlatformRegistry.YOUTUBE,
            "Hide player controls Time duration 1 hour 25 minutes Subscribe"
        )
        assertTrue(detection.isActivePlayer)
        assertEquals(SurfaceDetectionResult.LONG_FORM_PLAYER, detection.surface)
        assertFalse(detection.isPassive)
    }

    @Test
    fun youtubeNonFullscreenPlayer_withPlaybackSettings_isActivePlayer() {
        val detection = SurfaceDetector.detect(
            VideoPlatformRegistry.YOUTUBE,
            "Show player controls Playback Settings Search"
        )
        assertTrue(detection.isActivePlayer)
    }

    @Test
    fun bareVideosWord_isNotActivePlayer() {
        assertFalse(
            SurfaceDetector.detect(
                VideoPlatformRegistry.CHROME,
                "Art and photos Short videos New tab"
            ).isActivePlayer
        )
    }

    @Test
    fun newPipeClockPair_parsesActivePlayerAndDuration() {
        val detection = SurfaceDetector.detect(
            VideoPlatformRegistry.NEWPIPE,
            "Play Pause 00:15 / 45:00 Related videos"
        )
        assertTrue(detection.isActivePlayer)
        assertEquals(45, detection.durationMinutes)
    }

    @Test
    fun newPipeShortClip_underNinetySeconds_isShortForm() {
        val detection = SurfaceDetector.detect(
            VideoPlatformRegistry.NEWPIPE,
            "Play Pause 00:15 / 00:59 Let’s talk now… Samay Raina"
        )
        assertEquals(SurfaceDetectionResult.SHORT_FORM_PLAYER, detection.surface)
        assertEquals(59, detection.durationSeconds)
        assertEquals(0, VideoDurationParser.extractPrimaryDurationMinutes("00:15 / 00:59"))
    }

    @Test
    fun chromeOmniboxShortsUrl_isActiveShort() {
        val detection = SurfaceDetector.detect(
            VideoPlatformRegistry.CHROME,
            "Address bar https://www.youtube.com/shorts/dQw4w9WgXcQ " +
                "youtube.com/shorts/dQw4w9WgXcQ"
        )
        assertEquals(SurfaceDetectionResult.SHORT_FORM_PLAYER, detection.surface)
        assertTrue(detection.isActivePlayer)
        assertTrue(detection.isShortFormPlay)
    }

    @Test
    fun youtubeShareSheetShortsPath_isActiveShort() {
        val detection = SurfaceDetector.detect(
            VideoPlatformRegistry.YOUTUBE,
            "Share Copy link https://youtube.com/shorts/abcXYZ12 feature=share"
        )
        assertEquals(SurfaceDetectionResult.SHORT_FORM_PLAYER, detection.surface)
        assertTrue(detection.isShortFormPlay)
    }

    @Test
    fun youtubeUseThisSound_isActiveShort() {
        val detection = SurfaceDetector.detect(
            VideoPlatformRegistry.YOUTUBE,
            "Trending audio Use this sound Pause like comment"
        )
        assertEquals(SurfaceDetectionResult.SHORT_FORM_PLAYER, detection.surface)
        assertTrue(detection.isShortFormPlay)
    }

    @Test
    fun chromeUseThisSound_isActiveShort() {
        val detection = SurfaceDetector.detect(
            VideoPlatformRegistry.CHROME,
            "YouTube Use this sound Pause like comment"
        )
        assertEquals(SurfaceDetectionResult.SHORT_FORM_PLAYER, detection.surface)
        assertTrue(detection.isShortFormPlay)
    }

    @Test
    fun lectureClock_00_15_over_38_25_isNotShortFromDuration() {
        val detection = SurfaceDetector.detect(
            VideoPlatformRegistry.NEWPIPE,
            "Play Pause 00:15 / 38:25 OS lecture"
        )
        assertEquals(2305, detection.durationSeconds)
        assertFalse(detection.isShortFormPlay)
        assertEquals(SurfaceDetectionResult.LONG_FORM_PLAYER, detection.surface)
        assertFalse(
            VideoDurationParser.isShortFormItemLengthSeconds(
                detection.durationSeconds,
                SurfaceDetector.SHORT_FORM_MAX_SECONDS
            )
        )
    }

    @Test
    fun watchTime2305Seconds_doesNotClassifyAsShort() {
        val detection = SurfaceDetector.detect(
            VideoPlatformRegistry.YOUTUBE,
            "Hide player controls Playback Settings watched 2305 seconds lecture"
        )
        assertFalse(detection.isShortFormPlay)
        assertNull(VideoDurationParser.extractPrimaryDurationSeconds(
            "Hide player controls Playback Settings watched 2305 seconds lecture"
        ))
        assertTrue(detection.isActivePlayer)
    }

    @Test
    fun youtuBeLectureLink_isNotShortFromUrlAlone() {
        val detection = SurfaceDetector.detect(
            VideoPlatformRegistry.CHROME,
            "Address bar https://youtu.be/abcdefghijk Hide player controls " +
                "Play Pause 00:15 / 38:25 OS lecture"
        )
        assertFalse(detection.isShortFormPlay)
        assertEquals(SurfaceDetectionResult.LONG_FORM_PLAYER, detection.surface)
    }

    @Test
    fun youtuBeFeatureShorts_isActiveShort() {
        val detection = SurfaceDetector.detect(
            VideoPlatformRegistry.CHROME,
            "Address bar https://youtu.be/abcXYZ12?feature=shorts"
        )
        assertEquals(SurfaceDetectionResult.SHORT_FORM_PLAYER, detection.surface)
        assertTrue(detection.isShortFormPlay)
    }

    @Test
    fun instagramReelUrl_isActiveShort() {
        val detection = SurfaceDetector.detect(
            VideoPlatformRegistry.INSTAGRAM,
            "https://www.instagram.com/reel/CxyzABC123 audio original"
        )
        assertEquals(SurfaceDetectionResult.SHORT_FORM_PLAYER, detection.surface)
        assertTrue(detection.isShortFormPlay)
    }

    @Test
    fun youtubeHomeShelf_stillPassive() {
        val detection = SurfaceDetector.detect(
            VideoPlatformRegistry.YOUTUBE,
            "Home Shorts Subscriptions Library recommended for you 0:45 1:12"
        )
        assertEquals(SurfaceDetectionResult.HOME, detection.surface)
        assertFalse(detection.isActivePlayer)
        assertFalse(detection.isShortFormPlay)
        assertTrue(detection.isPassive)
    }
}
