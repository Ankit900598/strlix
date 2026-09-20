package com.phonecodex.app.domain.enforcement

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class EntertainmentBanGateTest {

    private val monk =
        "Monk mode for 4 hours. Only calls and study. No social, no shorts, no games."
    private val calculusOnly =
        "allow only calculus lecture videos longer than 30 minutes for 1 hour"
    private val chromeComments = "Comments Add a comment Top comments View replies"
    private val ytHome =
        "YouTube Home Search Shorts Subscriptions You Explore recommended for you 0:45 1:12"
    private val pornPlayer =
        "Hide player controls Time duration 12 minutes Playback Settings Watch now"
    private val lecturePlayer =
        "Play Pause 00:15 / 45:00 calculus lecture Hide player controls Time duration 45 minutes"

    @Test
    fun monk_chromeComments_blocks() {
        assertEquals(
            EntertainmentBanAction.BLOCK,
            EntertainmentBanGate.evaluate(VideoPlatformRegistry.CHROME, chromeComments, monk)
        )
        val gate = SurfaceEnforcementGate.evaluate(
            VideoPlatformRegistry.CHROME,
            chromeComments,
            monk
        )
        assertFalse(gate.isPass)
        assertTrue(gate.reason.contains("Entertainment ban"))
    }

    @Test
    fun monk_youtubeHome_blocks() {
        assertTrue(
            EntertainmentBanGate.shouldBlock(VideoPlatformRegistry.YOUTUBE, ytHome, monk)
        )
        assertFalse(
            SurfaceEnforcementGate.evaluate(VideoPlatformRegistry.YOUTUBE, ytHome, monk).isPass
        )
    }

    @Test
    fun monk_instagramExplore_blocks() {
        assertTrue(
            EntertainmentBanGate.shouldBlock(
                VideoPlatformRegistry.INSTAGRAM,
                "Explore Profile Suggested for you Stories Reels shelf",
                monk
            )
        )
    }

    @Test
    fun monk_chromePornPlayer_blocks_evenWithoutAdultKeyword() {
        assertEquals(
            EntertainmentBanAction.BLOCK,
            EntertainmentBanGate.evaluate(VideoPlatformRegistry.CHROME, pornPlayer, monk)
        )
    }

    @Test
    fun monk_chromeCalculusLecture_allowsStudy() {
        assertEquals(
            EntertainmentBanAction.ALLOW_STUDY,
            EntertainmentBanGate.evaluate(VideoPlatformRegistry.CHROME, lecturePlayer, monk)
        )
    }

    @Test
    fun lengthOnlyPromise_doesNotEntertainmentBan() {
        assertEquals(
            EntertainmentBanAction.NONE,
            EntertainmentBanGate.evaluate(VideoPlatformRegistry.CHROME, chromeComments, calculusOnly)
        )
        assertTrue(
            SurfaceEnforcementGate.evaluate(
                VideoPlatformRegistry.CHROME,
                chromeComments,
                calculusOnly,
                structuredMinBlockMinutes = 30
            ).isPass
        )
    }

    @Test
    fun noShortsOnly_youtubeHome_stillPasses() {
        val goal = "no shorts for 1 hour"
        assertEquals(
            EntertainmentBanAction.NONE,
            EntertainmentBanGate.evaluate(VideoPlatformRegistry.YOUTUBE, ytHome, goal)
        )
        assertTrue(
            SurfaceEnforcementGate.evaluate(VideoPlatformRegistry.YOUTUBE, ytHome, goal).isPass
        )
    }

    @Test
    fun monk_dialer_isNotEntertainmentPackage() {
        assertEquals(
            EntertainmentBanAction.NONE,
            EntertainmentBanGate.evaluate("com.android.dialer", "Call keypad", monk)
        )
    }

    @Test
    fun monk_fachatFreechat_blocksEvenWhenLocked() {
        val pkg = EntertainmentClassDetector.FACHAT_FREECHAT
        assertTrue(EntertainmentClassDetector.looksLikeDatingLiveCall(pkg, ""))
        assertEquals(
            EntertainmentBanAction.BLOCK,
            EntertainmentBanGate.evaluate(pkg, "Home Discover Match", monk)
        )
        assertTrue(SessionLockLaw.shouldKeepLockingPackage(pkg))
        assertFalse(SessionLockLaw.mayUseAppWhileLocked(pkg))
        assertTrue(
            EntertainmentBanGate.mustEvaluate(
                packageName = pkg,
                screenText = "Home",
                goal = monk,
                enforcementScopePackages = NAMED_VIDEO_SCOPE
            )
        )
    }

    @Test
    fun monk_jolaVideoCall_blocks() {
        val jola = EntertainmentClassDetector.JOLA_VIDEO
        val screen = "Discover Following You have not followed anyone yet 60% OFF"
        assertTrue(EntertainmentClassDetector.looksLikeDatingLiveCall(jola, screen))
        assertEquals(
            EntertainmentBanAction.BLOCK,
            EntertainmentBanGate.evaluate(jola, screen, monk)
        )
        assertTrue(
            EntertainmentBanGate.mustEvaluate(
                packageName = jola,
                screenText = screen,
                goal = monk,
                enforcementScopePackages = NAMED_VIDEO_SCOPE
            )
        )
    }

    @Test
    fun monk_tinderAndChamet_block() {
        assertEquals(
            EntertainmentBanAction.BLOCK,
            EntertainmentBanGate.evaluate("com.tinder", "Discover matches", monk)
        )
        assertEquals(
            EntertainmentBanAction.BLOCK,
            EntertainmentBanGate.evaluate(
                "com.hkfuliao.chamet",
                "Live girls Video call Start matching",
                monk
            )
        )
    }

    @Test
    fun monk_contactsAndChatGpt_allow() {
        for (pkg in listOf("com.android.contacts", "com.openai.chatgpt")) {
            assertEquals(
                pkg,
                EntertainmentBanAction.NONE,
                EntertainmentBanGate.evaluate(pkg, "Home", monk)
            )
            assertFalse(
                pkg,
                EntertainmentBanGate.mustEvaluate(
                    packageName = pkg,
                    screenText = "Home",
                    goal = monk,
                    enforcementScopePackages = NAMED_VIDEO_SCOPE
                )
            )
        }
    }

    @Test
    fun monk_unknownChatApp_blocksWithoutPackageList() {
        val unknown = "com.xyz.randomchat"
        assertFalse(EntertainmentClassDetector.looksLikeDatingLiveCall(unknown, "Home Discover"))
        assertEquals(
            EntertainmentBanAction.BLOCK,
            EntertainmentBanGate.evaluate(unknown, "Home Discover", monk)
        )
        assertTrue(
            EntertainmentBanGate.mustEvaluate(
                packageName = unknown,
                screenText = "Home Discover",
                goal = monk,
                enforcementScopePackages = NAMED_VIDEO_SCOPE
            )
        )
        assertTrue(SessionLockLaw.shouldKeepLockingPackage(unknown, "Home", monk))
        assertFalse(SessionLockLaw.mayUseAppWhileLocked(unknown, "Home", monk))
    }

    @Test
    fun monk_calendarAndPhonePe_allow() {
        for (pkg in listOf("com.google.android.calendar", "com.phonepe.app")) {
            assertEquals(
                pkg,
                EntertainmentBanAction.NONE,
                EntertainmentBanGate.evaluate(pkg, "Home", monk)
            )
            assertFalse(
                pkg,
                EntertainmentBanGate.mustEvaluate(
                    packageName = pkg,
                    screenText = "Home",
                    goal = monk,
                    enforcementScopePackages = NAMED_VIDEO_SCOPE
                )
            )
            assertTrue(SessionLockLaw.mayUseAppWhileLocked(pkg, "Home", monk))
        }
    }

    @Test
    fun monk_playStoreBrowse_blocksSoUnknownAppsCannotInstall() {
        assertEquals(
            EntertainmentBanAction.BLOCK,
            EntertainmentBanGate.evaluate(
                "com.android.vending",
                "Play Store Install Ratings",
                monk
            )
        )
        assertTrue(
            EntertainmentBanGate.mustEvaluate(
                packageName = "com.android.vending",
                screenText = "Play Store Install Ratings",
                goal = monk,
                enforcementScopePackages = NAMED_VIDEO_SCOPE
            )
        )
    }

    @Test
    fun monk_playStoreInstallConfirmation_blocks() {
        val confirm = "Do you want to install this application App permissions Cancel"
        assertEquals(
            SurfaceDetectionResult.INSTALL_FLOW,
            SurfaceDetector.detect("com.android.vending", confirm).surface
        )
        assertEquals(
            EntertainmentBanAction.BLOCK,
            EntertainmentBanGate.evaluate("com.android.vending", confirm, monk)
        )
        assertTrue(
            EntertainmentBanGate.mustEvaluate(
                packageName = "com.google.android.packageinstaller",
                screenText = confirm,
                goal = monk,
                enforcementScopePackages = NAMED_VIDEO_SCOPE
            )
        )
        assertEquals(
            EntertainmentBanAction.BLOCK,
            EntertainmentBanGate.evaluate(
                "com.google.android.packageinstaller",
                confirm,
                monk
            )
        )
    }

    @Test
    fun noGames_blocksGamesAndPlayGameListing_allowsUnknownChat() {
        val noGames = "no games for 4 hours"
        assertEquals(
            EntertainmentBanAction.BLOCK,
            EntertainmentBanGate.evaluate(
                "com.dts.freefireth",
                "Play now Multiplayer",
                noGames
            )
        )
        assertEquals(
            EntertainmentBanAction.BLOCK,
            EntertainmentBanGate.evaluate(
                "com.android.vending",
                "Free Fire Games Casual Contains ads In-app purchases Install",
                noGames
            )
        )
        assertEquals(
            EntertainmentBanAction.NONE,
            EntertainmentBanGate.evaluate("com.xyz.randomchat", "Home Discover", noGames)
        )
        assertEquals(
            EntertainmentBanAction.NONE,
            EntertainmentBanGate.evaluate(
                "com.android.vending",
                "Khan Academy Education 4.8 Install",
                noGames
            )
        )
        assertFalse(SessionLockLaw.shouldKeepLockingPackage("com.xyz.randomchat", "Home", noGames))
    }

    @Test
    fun noSocial_failClosesUnknownChat_allowsUtility() {
        val noSocial = "no social media tonight"
        assertEquals(
            EntertainmentBanAction.BLOCK,
            EntertainmentBanGate.evaluate(VideoPlatformRegistry.INSTAGRAM, "Explore", noSocial)
        )
        assertEquals(
            EntertainmentBanAction.BLOCK,
            EntertainmentBanGate.evaluate("com.xyz.randomchat", "Home Discover", noSocial)
        )
        assertEquals(
            EntertainmentBanAction.NONE,
            EntertainmentBanGate.evaluate("com.phonepe.app", "Home", noSocial)
        )
    }

    @Test
    fun movieOnly_doesNotFailCloseUnknownChat() {
        val movies = "no movies tonight"
        assertEquals(
            EntertainmentBanAction.NONE,
            EntertainmentBanGate.evaluate("com.xyz.randomchat", "Home Discover", movies)
        )
        assertFalse(
            EntertainmentBanGate.mustEvaluate(
                packageName = "com.xyz.randomchat",
                screenText = "Home Discover",
                goal = movies,
                enforcementScopePackages = NAMED_VIDEO_SCOPE
            )
        )
    }

    @Test
    fun lengthOnlyPromise_doesNotInventDatingOrInstallBan() {
        assertEquals(
            EntertainmentBanAction.NONE,
            EntertainmentBanGate.evaluate(
                EntertainmentClassDetector.JOLA_VIDEO,
                "Discover Following Video call",
                calculusOnly
            )
        )
        assertEquals(
            EntertainmentBanAction.NONE,
            EntertainmentBanGate.evaluate(
                "com.google.android.packageinstaller",
                "Do you want to install this application",
                calculusOnly
            )
        )
        assertFalse(
            EntertainmentBanGate.shouldOverrideNamedScopeAllow(
                EntertainmentClassDetector.JOLA_VIDEO,
                "Discover Following",
                calculusOnly
            )
        )
    }

    companion object {
        private val NAMED_VIDEO_SCOPE = listOf(
            VideoPlatformRegistry.YOUTUBE,
            VideoPlatformRegistry.CHROME,
            VideoPlatformRegistry.NEWPIPE,
            VideoPlatformRegistry.INSTAGRAM,
            VideoPlatformRegistry.FACEBOOK,
            VideoPlatformRegistry.TIKTOK,
            VideoPlatformRegistry.SNAPCHAT
        )
    }
}
