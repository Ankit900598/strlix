package com.phonecodex.app.domain.enforcement

import com.phonecodex.app.domain.model.StudyWorldSettings
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class EnforcementScopeLawTest {

    private val youtubePlayer =
        "Hide player controls Play Pause 00:15 / 12:00 YouTube"
    private val chromeYoutubeUrl =
        "https://www.youtube.com/watch?v=abc Hide player controls Play Pause 00:15 / 12:00"
    private val chromeGmail = "https://mail.google.com/mail Inbox Primary"
    private val youtubeBrands = listOf(EnforcementScopeLaw.BRAND_YOUTUBE)

    @Test
    fun emptyScope_matchesEverything() {
        assertTrue(
            EnforcementScopeLaw.matches(
                VideoPlatformRegistry.CHROME,
                chromeGmail,
                emptyList(),
                emptyList()
            )
        )
    }

    @Test
    fun youtubeContentBrand_matchesOfficialAppNewPipeChromeHostAndVanced() {
        assertTrue(
            EnforcementScopeLaw.isYouTubeSurface(
                VideoPlatformRegistry.YOUTUBE,
                youtubePlayer
            )
        )
        assertTrue(
            EnforcementScopeLaw.isYouTubeSurface(
                VideoPlatformRegistry.NEWPIPE,
                "Play Pause 00:15 / 00:59"
            )
        )
        assertTrue(
            EnforcementScopeLaw.isYouTubeSurface(
                VideoPlatformRegistry.CHROME,
                chromeYoutubeUrl
            )
        )
        assertTrue(
            EnforcementScopeLaw.isYouTubeClientPackage("com.vanced.android.youtube")
        )
        assertTrue(
            EnforcementScopeLaw.matches(
                "com.vanced.android.youtube",
                youtubePlayer,
                emptyList(),
                youtubeBrands
            )
        )
    }

    @Test
    fun youtubePlayerAccessibility_chromeWithoutUrl_isYouTubeSurface() {
        val screen = "Time elapsed 1 secondTime duration 31 minutes, 33 seconds"
        assertTrue(EnforcementScopeLaw.looksLikeYouTubePlayerAccessibility(screen))
        assertTrue(
            EnforcementScopeLaw.isYouTubeSurface(VideoPlatformRegistry.CHROME, screen)
        )
        assertTrue(
            EnforcementScopeLaw.matches(
                VideoPlatformRegistry.CHROME,
                screen,
                emptyList(),
                youtubeBrands
            )
        )
    }

    @Test
    fun youtubeContentBrand_doesNotMatchGmailOrNews() {
        assertFalse(
            EnforcementScopeLaw.isYouTubeSurface(
                VideoPlatformRegistry.CHROME,
                chromeGmail
            )
        )
        assertFalse(
            EnforcementScopeLaw.matches(
                VideoPlatformRegistry.CHROME,
                chromeGmail,
                emptyList(),
                youtubeBrands
            )
        )
    }

    @Test
    fun youtubeAppOnlyPackages_doNotMatchChromeYoutubeHost() {
        assertFalse(
            EnforcementScopeLaw.matches(
                VideoPlatformRegistry.CHROME,
                chromeYoutubeUrl,
                listOf(VideoPlatformRegistry.YOUTUBE),
                emptyList()
            )
        )
        assertTrue(
            EnforcementScopeLaw.matches(
                VideoPlatformRegistry.YOUTUBE,
                youtubePlayer,
                listOf(VideoPlatformRegistry.YOUTUBE),
                emptyList()
            )
        )
    }

    @Test
    fun settingsHelper_usesPersistedBrands() {
        val settings = StudyWorldSettings(
            durationMinutes = 60,
            lockAttemptThreshold = 3,
            blockAttemptCooldownMinutes = 2,
            minVideoLengthBlockMinutes = 40,
            enforcementContentBrands = youtubeBrands
        )
        assertTrue(
            EnforcementScopeLaw.matches(
                VideoPlatformRegistry.CHROME,
                chromeYoutubeUrl,
                settings
            )
        )
        assertFalse(
            EnforcementScopeLaw.matches(
                VideoPlatformRegistry.CHROME,
                chromeGmail,
                settings
            )
        )
    }
}
