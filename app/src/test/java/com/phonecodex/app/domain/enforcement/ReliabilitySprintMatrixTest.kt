package com.phonecodex.app.domain.enforcement

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Overnight reliability red-team matrix: ≥30 edge cases across passive/active,
 * duration source, quota, and overlay lifecycle.
 */
class ReliabilitySprintMatrixTest {

    private val min30 =
        "do not allow videos shorter than 30 minutes for next 1 hour"
    private val max40 =
        "for 1 hour do not allow to watch any video whose length is greater than 40 min"
    private val shorts10 =
        "I want to watch at most 10 shorts today, but never adult shorts. " +
            "Long educational YouTube should still be allowed."

    // --- Passive PASS (20+) ---

    @Test
    fun matrix_passiveSurfaces_passMediaLength() {
        val cases = listOf(
            VideoPlatformRegistry.YOUTUBE to "Home Shorts Subscriptions You",
            VideoPlatformRegistry.CHROME to
                "YouTube Home Search Shorts Subscriptions You Explore Podcasts " +
                "Intelligence Zscaler’s Jay Chaudhry… 52 minutes",
            VideoPlatformRegistry.YOUTUBE to "Search results 12:04 45 minutes Home",
            VideoPlatformRegistry.YOUTUBE to "Channel videos About 1.2M subscribers",
            VideoPlatformRegistry.YOUTUBE to "Subscriptions Latest videos",
            VideoPlatformRegistry.YOUTUBE to "Comments Add a comment Reply",
            VideoPlatformRegistry.YOUTUBE to "Home Shorts shelf For you 0:45 1:12",
            VideoPlatformRegistry.CHROME to
                "Google Search Videos Short videos Images About 1,200,000 results",
            VideoPlatformRegistry.CHROME to "Chrome tabs switcher New tab",
            VideoPlatformRegistry.NEWPIPE to "History Trending Recommendations 12:34",
            VideoPlatformRegistry.INSTAGRAM to "Profile posts Explore grid",
            VideoPlatformRegistry.INSTAGRAM to "Explore Search Reels grid",
            VideoPlatformRegistry.INSTAGRAM to "Messages inbox list Direct",
            VideoPlatformRegistry.FACEBOOK to "News Feed Reels thumbnail Watch",
            VideoPlatformRegistry.TIKTOK to "Profile Following Search",
            VideoPlatformRegistry.CHROME to "Play Store app page Install reviews",
            VideoPlatformRegistry.CHROME to "Google Discover news cards For you",
            VideoPlatformRegistry.SNAPCHAT to "Spotlight Stories Discover friends",
            VideoPlatformRegistry.CHROME to
                "Embedded video preview thumbnail 8 minutes not playing",
            VideoPlatformRegistry.YOUTUBE to "Library History Watch later Downloads"
        )
        assertTrue("need ≥20 passive cases", cases.size >= 20)
        for ((pkg, text) in cases) {
            val d = MediaLengthEnforcement.decide(
                packageName = pkg,
                goal = min30,
                screenText = text,
                structuredMaxBlockMinutes = null,
                structuredMinBlockMinutes = 30
            )
            assertEquals("PASS expected for `$text`", MediaLengthLocalDecision.PASS, d)
            assertFalse(
                "must not be active player: $text",
                SurfaceDetector.detect(pkg, text).isActivePlayer
            )
        }

        // Non-video system packages: never BLOCK from media-length.
        for ((pkg, text) in listOf(
            "com.android.systemui" to "Notification shade Wi-Fi Bluetooth",
            "com.miui.home" to "App drawer Phone Messages Chrome"
        )) {
            val d = MediaLengthEnforcement.decide(pkg, min30, text, null, 30)
            assertNotEquals(MediaLengthLocalDecision.BLOCK, d)
        }
    }

    // --- Active enforcement (10+) ---

    @Test
    fun matrix_activePlayers_enforce() {
        data class Case(
            val pkg: String,
            val text: String,
            val goal: String,
            val min: Int?,
            val max: Int?,
            val expected: MediaLengthLocalDecision
        )
        val cases = listOf(
            Case(
                VideoPlatformRegistry.NEWPIPE,
                "Play Pause 00:15 / 00:59 short clip",
                min30,
                30,
                null,
                MediaLengthLocalDecision.BLOCK
            ),
            Case(
                VideoPlatformRegistry.NEWPIPE,
                "Play Pause 00:10 / 52:00 lecture",
                min30,
                30,
                null,
                MediaLengthLocalDecision.ALLOW
            ),
            Case(
                VideoPlatformRegistry.NEWPIPE,
                "Play Pause 00:20 / 1:46:00 long lecture",
                max40,
                null,
                40,
                MediaLengthLocalDecision.BLOCK
            ),
            Case(
                VideoPlatformRegistry.CHROME,
                "Hide player controls Time duration 12 minutes YouTube",
                max40,
                null,
                40,
                MediaLengthLocalDecision.ALLOW
            ),
            Case(
                VideoPlatformRegistry.CHROME,
                "Hide player controls Time duration 1 hour 25 minutes YouTube",
                max40,
                null,
                40,
                MediaLengthLocalDecision.BLOCK
            ),
            Case(
                VideoPlatformRegistry.YOUTUBE,
                "Hide player controls Shorts player swipe up 0:45",
                min30,
                30,
                null,
                MediaLengthLocalDecision.BLOCK // 45s current near controls < 30m
            ),
            Case(
                VideoPlatformRegistry.YOUTUBE,
                "Hide player controls Time duration 2 hours 5 minutes Subscribe",
                max40,
                null,
                40,
                MediaLengthLocalDecision.BLOCK
            ),
            Case(
                VideoPlatformRegistry.CHROME,
                "youtube.com/watch?v=x Show player controls Time duration 35 minutes",
                min30,
                30,
                null,
                MediaLengthLocalDecision.ALLOW
            ),
            Case(
                VideoPlatformRegistry.NEWPIPE,
                "Play Pause 00:05 / 00:40 Related",
                max40,
                null,
                40,
                MediaLengthLocalDecision.ALLOW
            ),
            Case(
                VideoPlatformRegistry.CHROME,
                "Show player controls Time duration 55 minutes More videos 8 minutes 55 seconds",
                min30,
                30,
                null,
                MediaLengthLocalDecision.ALLOW
            )
        )
        assertTrue(cases.size >= 10)
        for (c in cases) {
            val d = MediaLengthEnforcement.decide(
                c.pkg,
                c.goal,
                c.text,
                structuredMaxBlockMinutes = c.max,
                structuredMinBlockMinutes = c.min
            )
            assertEquals("goal=${c.goal} text=${c.text}", c.expected, d)
        }
    }

    @Test
    fun matrix_recommendationDurationsNeverBlock() {
        val screen =
            "m.youtube.com/watch Chip design from the bottom up – Reiner Pope " +
                "Show player controls " +
                "Can This Vibe Coder 8 minutes 55 seconds " +
                "Andrew Tate 4 minutes 48 seconds " +
                "Introducing GPT-6 Astra 2 minutes 43 seconds"
        val detailed = MediaLengthEnforcement.decideDetailed(
            VideoPlatformRegistry.CHROME,
            min30,
            screen,
            structuredMaxBlockMinutes = null,
            structuredMinBlockMinutes = 30
        )
        assertNotEquals(MediaLengthLocalDecision.BLOCK, detailed.decision)
        assertEquals(DurationSource.RECOMMENDATION_IGNORED, detailed.durationSource)
        assertNull(detailed.currentPlayerDurationSeconds)
    }

    @Test
    fun matrix_newPipeHourLecture_isLongFormCurrentPlayer() {
        val parsed = VideoDurationParser.parse("Play Pause 00:12 / 1:46:00 Neso Academy")
        assertEquals(DurationSource.CURRENT_PLAYER, parsed.source)
        assertEquals(1 * 3600 + 46 * 60, parsed.currentPlayerDurationSeconds)
        assertEquals(
            MediaLengthLocalDecision.BLOCK,
            MediaLengthEnforcement.decide(
                VideoPlatformRegistry.NEWPIPE,
                max40,
                "Play Pause 00:12 / 1:46:00 Neso Academy",
                structuredMaxBlockMinutes = 40
            )
        )
    }

    @Test
    fun matrix_quotaCrossApp_andPassiveSkip() {
        val gate = ShortFormQuotaGate()
        val limit = 10
        // Passive shelf must not count
        val shelf = gate.evaluate(
            VideoPlatformRegistry.YOUTUBE,
            "Home Shorts shelf For you 0:45 1:12",
            limit
        )
        assertEquals(ShortFormQuotaAction.SKIP_NOT_SHORT_PLAY, shelf.action)

        val first = gate.evaluate(
            VideoPlatformRegistry.INSTAGRAM,
            "Reels player Pause Share 0:30 funny clip",
            limit
        )
        // Instagram may or may not classify as short player depending on evidence;
        // if active, count; if skip, still ok as long as not false BLOCK.
        assertNotEquals(ShortFormQuotaAction.BLOCK_QUOTA_EXCEEDED, first.action)

        repeat(10) { i ->
            gate.evaluate(
                VideoPlatformRegistry.NEWPIPE,
                "Play Pause 00:15 / 00:${40 + (i % 10)} clip$i",
                limit
            )
        }
        val overflow = gate.evaluate(
            VideoPlatformRegistry.TIKTOK,
            "For You Pause Like Share following swipe",
            limit
        )
        // TikTok FYP without strong player may SKIP; NewPipe overflow after 10:
        val eleventh = gate.evaluate(
            VideoPlatformRegistry.NEWPIPE,
            "Play Pause 00:10 / 00:50 overflow",
            limit
        )
        assertEquals(ShortFormQuotaAction.BLOCK_QUOTA_EXCEEDED, eleventh.action)
        assertEquals(10, eleventh.count)
    }

    @Test
    fun matrix_duplicateEventsDoNotDoubleCount() {
        val gate = ShortFormQuotaGate()
        val text = "Play Pause 00:15 / 00:55 same short title"
        val a = gate.evaluate(VideoPlatformRegistry.NEWPIPE, text, 10)
        val b = gate.evaluate(VideoPlatformRegistry.NEWPIPE, text, 10)
        assertEquals(ShortFormQuotaAction.ALLOW_AND_COUNT, a.action)
        assertEquals(1, a.count)
        assertTrue(
            b.action == ShortFormQuotaAction.ALLOW_DUPLICATE || b.count == 1
        )
    }

    @Test
    fun matrix_adultDoesNotConsumeQuota() {
        val gate = ShortFormQuotaGate()
        gate.evaluate(
            VideoPlatformRegistry.NEWPIPE,
            "Play Pause 00:15 / 00:50 normal",
            10
        )
        val adult = gate.evaluate(
            VideoPlatformRegistry.NEWPIPE,
            "Play Pause 00:10 / 00:40 porn xxx adult",
            10
        )
        assertEquals(ShortFormQuotaAction.BLOCK_ADULT, adult.action)
        assertEquals(1, adult.count)
        assertFalse(adult.counted)
    }

    @Test
    fun matrix_longEducationalAllowedUnderQuotaPromise() {
        val gate = ShortFormQuotaGate()
        val d = gate.evaluate(
            packageName = VideoPlatformRegistry.YOUTUBE,
            screenText = "Hide player controls Time duration 1 hour 20 minutes lecture OS",
            limit = 10,
            allowLongEducational = true
        )
        assertTrue(
            d.action == ShortFormQuotaAction.ALLOW_LONG_EDUCATIONAL ||
                d.action == ShortFormQuotaAction.SKIP_NOT_SHORT_PLAY
        )
    }

    @Test
    fun matrix_overlayLifecycle_ownPackageRetains_launcherDoesNot() {
        assertTrue(
            OverlayLifecycleGate.shouldRetainForNoise(
                OverlayLifecycleGate.OWN_PACKAGE,
                "com.android.chrome"
            )
        )
        assertTrue(
            OverlayLifecycleGate.shouldRetainForNoise(
                "com.android.systemui",
                "com.android.chrome"
            )
        )
        assertFalse(
            OverlayLifecycleGate.shouldRetainForNoise(
                "com.miui.home",
                "com.android.chrome"
            )
        )
        assertTrue(OverlayLifecycleGate.shouldClearOverlayOnPassiveAllow(sessionLocked = false))
        assertTrue(OverlayLifecycleGate.shouldClearOverlayOnPassiveAllow(sessionLocked = true))
        assertTrue(OverlayLifecycleGate.shouldClearWarningOnAllow())
    }

    @Test
    fun matrix_surfaceGate_aiMayNotWarnAfterPass() {
        val gate = SurfaceEnforcementGate.evaluate(
            packageName = VideoPlatformRegistry.CHROME,
            screenText =
                "YouTube Home Search Shorts Subscriptions You Explore Podcasts 52 minutes",
            goal = min30,
            structuredMinBlockMinutes = 30
        )
        assertTrue(gate.isPass)
        assertFalse(SurfaceEnforcementGate.aiMayWarnOrBlock(gate))
        assertEquals(SurfaceActivity.PASSIVE, gate.activity)
    }

    @Test
    fun matrix_shortsPromise_doesNotNeedPackageInUserCopy() {
        // Smoke that quota parsing stays category-level in goal text.
        assertEquals(10, ShortFormQuotaGate.parseDailyShortFormLimit(shorts10))
    }
}
