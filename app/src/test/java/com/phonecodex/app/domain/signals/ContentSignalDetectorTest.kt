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
    }

    companion object {
        private const val YOUTUBE_PACKAGE = "com.google.android.youtube"
    }
}
