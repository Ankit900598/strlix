package com.phonecodex.app.domain.enforcement

import com.phonecodex.app.domain.model.ContextSnapshot
import com.phonecodex.app.domain.model.DecisionType
import com.phonecodex.app.domain.model.FocusSession
import com.phonecodex.app.domain.model.FocusWorld
import com.phonecodex.app.domain.model.SessionStatus
import com.phonecodex.app.domain.model.StrictnessLevel
import com.phonecodex.app.domain.model.WorldMode
import com.phonecodex.app.domain.policy.PolicyEngine
import com.phonecodex.app.domain.safeapps.SafeAppsCatalog
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class SessionLockLawTest {

    private val engine = PolicyEngine()
    private val world = FocusWorld(
        id = "study",
        name = "Study",
        mode = WorldMode.STUDY,
        defaultStrictness = StrictnessLevel.STRICT,
        allowedPackages = emptySet(),
        blockedPackages = emptySet(),
        conditionalPackages = emptySet()
    )

    @Test
    fun locked_doesNotBrickContactsChatGptDialerOrSearchApp() {
        val unlocked = listOf(
            "com.android.contacts",
            "com.google.android.contacts",
            "com.openai.chatgpt",
            "com.android.dialer",
            "com.google.android.googlequicksearchbox",
            "com.google.android.calendar",
            "com.android.phone"
        )
        for (pkg in unlocked) {
            assertTrue("$pkg must stay usable after lock", SessionLockLaw.mayUseAppWhileLocked(pkg))
            assertFalse(SessionLockLaw.shouldKeepLockingPackage(pkg))
            assertEquals(
                "$pkg policy",
                DecisionType.ALLOW,
                engine.evaluate(world, lockedSession(), context(pkg)).decision
            )
        }
    }

    @Test
    fun locked_monkUnknownChatStaysBlocked_utilitiesStayOpen() {
        val monk = "Monk mode for 4 hours. Only calls and study."
        assertTrue(
            SessionLockLaw.shouldKeepLockingPackage("com.xyz.randomchat", "Home", monk)
        )
        assertTrue(
            SessionLockLaw.shouldKeepLockingPackage("com.android.vending", "Play Store", monk)
        )
        assertTrue(SessionLockLaw.mayUseAppWhileLocked("com.google.android.calendar", "", monk))
        assertTrue(SessionLockLaw.mayUseAppWhileLocked("com.phonepe.app", "", monk))
        assertTrue(SessionLockLaw.mayUseAppWhileLocked("com.openai.chatgpt", "", monk))
        assertEquals(
            DecisionType.LOCK,
            engine.evaluate(world, lockedSession(), context("com.xyz.randomchat")).decision
        )
        assertEquals(
            DecisionType.ALLOW,
            engine.evaluate(world, lockedSession(), context("com.phonepe.app")).decision
        )
    }

    @Test
    fun locked_keepsDatingAndPackageInstallerBlocked() {
        assertTrue(
            SessionLockLaw.shouldKeepLockingPackage(EntertainmentClassDetector.JOLA_VIDEO)
        )
        assertTrue(SessionLockLaw.shouldKeepLockingPackage("com.tinder"))
        assertTrue(
            SessionLockLaw.shouldKeepLockingPackage(EntertainmentClassDetector.FACHAT_FREECHAT)
        )
        assertTrue(
            SessionLockLaw.shouldKeepLockingPackage("com.google.android.packageinstaller")
        )
        assertFalse(SessionLockLaw.shouldKeepLockingPackage("com.android.contacts"))
        assertFalse(SessionLockLaw.shouldKeepLockingPackage("com.openai.chatgpt"))
    }

    @Test
    fun locked_keepsYoutubeChromeInstagramBlocked() {
        for (pkg in listOf(
            VideoPlatformRegistry.YOUTUBE,
            VideoPlatformRegistry.CHROME,
            VideoPlatformRegistry.INSTAGRAM,
            VideoPlatformRegistry.TIKTOK
        )) {
            assertTrue(SessionLockLaw.shouldKeepLockingPackage(pkg))
            assertEquals(
                DecisionType.LOCK,
                engine.evaluate(world, lockedSession(), context(pkg)).decision
            )
        }
    }

    @Test
    fun locked_youtubeContentPromise_keepsChromeShortsBlocked() {
        val screen = "m.youtube.com/shorts Back Search Like Share The Blueprint for Success #motivation"
        assertTrue(
            SessionLockLaw.shouldKeepLockingPackage(
                packageName = VideoPlatformRegistry.CHROME,
                screenText = screen,
                goal = "for 1 hour allow only YouTube video longer than 40 minutes",
                contentBrands = listOf("youtube")
            )
        )
        assertFalse(
            SessionLockLaw.mayUseAppWhileLocked(
                packageName = VideoPlatformRegistry.CHROME,
                screenText = screen,
                goal = "for 1 hour allow only YouTube video longer than 40 minutes",
                contentBrands = listOf("youtube")
            )
        )
    }

    @Test
    fun locked_youtubeContentPromise_allowsNormalChromePage() {
        val screen = "Google Search weather tomorrow"
        assertTrue(
            SessionLockLaw.mayUseAppWhileLocked(
                packageName = VideoPlatformRegistry.CHROME,
                screenText = screen,
                goal = "for 1 hour allow only YouTube video longer than 40 minutes",
                contentBrands = listOf("youtube")
            )
        )
    }

    @Test
    fun active_unknownChatGptIsNotLock() {
        val decision = engine.evaluate(
            world,
            lockedSession().copy(status = SessionStatus.ACTIVE, attemptCount = 0),
            context("com.openai.chatgpt")
        )
        assertEquals(DecisionType.WARN, decision.decision)
    }

    @Test
    fun overlayAllowClearsEvenWhenSessionLocked() {
        assertTrue(OverlayLifecycleGate.shouldClearOverlayOnPassiveAllow(sessionLocked = true))
        assertTrue(OverlayLifecycleGate.shouldClearOverlayOnPassiveAllow(sessionLocked = false))
    }

    @Test
    fun contactsAndChatGptAreSafeDefaults() {
        assertTrue(SafeAppsCatalog.isDefaultPackage("com.android.contacts"))
        assertTrue(SafeAppsCatalog.isDefaultPackage("com.openai.chatgpt"))
        assertTrue(SafeAppsCatalog.isDefaultPackage("com.android.phone"))
    }

    private fun lockedSession(): FocusSession = FocusSession(
        id = "s1",
        worldId = "study",
        goal = "Monk mode for 4 hours. Only calls and study.",
        startTimeMillis = 1L,
        deadlineMillis = 2L,
        status = SessionStatus.LOCKED,
        attemptCount = 3,
        strictness = StrictnessLevel.STRICT
    )

    private fun context(packageName: String) = ContextSnapshot(
        timestampMillis = 1L,
        packageName = packageName,
        appLabel = packageName,
        screenText = "Home",
        url = null
    )
}
