package com.phonecodex.app.domain.signals

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ContentSignalDetectorTest {

    private val detector = ContentSignalDetector()

    @Test
    fun youtubeHomeShortsShelf_doesNotSetYouTubeShortsBlock() {
        val signals = detector.detect(
            packageName = YOUTUBE_PACKAGE,
            screenText = "Home Shorts Subscriptions Library Shorts shelf recommended for you"
        )

        assertFalse(signals.isYouTubeShorts)
    }

    @Test
    fun youtubeShortsPlayerSwipeUp_setsYouTubeShortsBlock() {
        val signals = detector.detect(
            packageName = YOUTUBE_PACKAGE,
            screenText = "Funny clip Swipe up for more Shorts"
        )

        assertTrue(signals.isYouTubeShorts)
    }

    @Test
    fun youtubeShortsUrl_setsYouTubeShortsBlock() {
        val signals = detector.detect(
            packageName = YOUTUBE_PACKAGE,
            screenText = "Share https://www.youtube.com/shorts/abcXYZ12 Copy link"
        )
        assertTrue(signals.isYouTubeShorts)
    }

    @Test
    fun youtubeShortsPlayerUseThisSound_setsYouTubeShortsBlock() {
        val signals = detector.detect(
            packageName = YOUTUBE_PACKAGE,
            screenText = "Trending audio Use this sound Remix this Short"
        )

        assertTrue(signals.isYouTubeShorts)
    }

    @Test
    fun youtubeLongVideo_doesNotSetYouTubeShortsBlock() {
        val signals = detector.detect(
            packageName = YOUTUBE_PACKAGE,
            screenText = "Full DSA Course Introduction 1 hour 12 minutes lecture playlist"
        )

        assertFalse(signals.isYouTubeShorts)
        assertTrue(signals.isLikelySearchOrLecture)
    }

    @Test
    fun youtubeSearchAlone_doesNotCountAsStudyLike() {
        val signals = detector.detect(
            packageName = YOUTUBE_PACKAGE,
            screenText = "Search What to watch Home Shorts"
        )

        assertFalse(signals.isLikelySearchOrLecture)
    }

    @Test
    fun chromeNewsHeadline_sexEducation_isNotAdult() {
        val signals = detector.detect(
            packageName = "com.android.chrome",
            screenText = "BBC News Sex education curriculum debate for adult learners"
        )
        assertFalse(signals.isChromeAdultOrPorn)
    }

    @Test
    fun chromePornhub_isAdult() {
        val signals = detector.detect(
            packageName = "com.android.chrome",
            screenText = "Pornhub video xxx nsfw"
        )
        assertTrue(signals.isChromeAdultOrPorn)
    }

    @Test
    fun chromeShamaniShort_isNotAdultFromVideoIdOrTitle() {
        val signals = detector.detect(
            packageName = "com.android.chrome",
            screenText = "Raj Shamani Shorts m.youtube.com/watch?v=abPornXy12Q 646K views"
        )
        assertFalse(signals.isChromeAdultOrPorn)
    }

    companion object {
        private const val YOUTUBE_PACKAGE = "com.google.android.youtube"
    }
}
