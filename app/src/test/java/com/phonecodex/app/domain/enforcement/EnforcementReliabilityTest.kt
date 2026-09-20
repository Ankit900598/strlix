package com.phonecodex.app.domain.enforcement

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class VideoPlatformRegistryTest {

    @Test
    fun registersOfficialYouTubeChromeAndNewPipe() {
        assertTrue(VideoPlatformRegistry.isOfficialYouTube(VideoPlatformRegistry.YOUTUBE))
        assertTrue(VideoPlatformRegistry.isChrome(VideoPlatformRegistry.CHROME))
        assertTrue(VideoPlatformRegistry.isNewPipe(VideoPlatformRegistry.NEWPIPE))
        assertTrue(VideoPlatformRegistry.enforcesMediaSurfaces(VideoPlatformRegistry.NEWPIPE))
    }

    @Test
    fun registersShortFormSocialPackages() {
        assertTrue(VideoPlatformRegistry.isKnownVideoPlatform(VideoPlatformRegistry.INSTAGRAM))
        assertTrue(VideoPlatformRegistry.isKnownVideoPlatform(VideoPlatformRegistry.FACEBOOK))
        assertTrue(VideoPlatformRegistry.isKnownVideoPlatform(VideoPlatformRegistry.TIKTOK))
        assertTrue(VideoPlatformRegistry.isKnownVideoPlatform(VideoPlatformRegistry.SNAPCHAT))
    }

    @Test
    fun unknownPackage_notRegistered() {
        assertFalse(VideoPlatformRegistry.isRegistered("com.example.random"))
        assertFalse(VideoPlatformRegistry.enforcesMediaSurfaces("com.example.random"))
    }

    @Test
    fun netmirror_enforcesMediaSurfaces() {
        assertTrue(VideoPlatformRegistry.isRegistered(VideoPlatformRegistry.NETMIRROR))
        assertTrue(VideoPlatformRegistry.enforcesMediaSurfaces(VideoPlatformRegistry.NETMIRROR))
        assertTrue(
            VideoPlatformRegistry.looksLikeUnknownStreamingPackage(VideoPlatformRegistry.NETMIRROR)
        )
    }
}

class OverlayLifecycleGateTest {

    @Test
    fun retainsOwnPackageAndSystemUi() {
        assertTrue(
            OverlayLifecycleGate.shouldRetainForNoise(
                OverlayLifecycleGate.OWN_PACKAGE,
                "com.google.android.youtube"
            )
        )
        assertTrue(
            OverlayLifecycleGate.shouldRetainForNoise(
                "com.android.systemui",
                "com.google.android.youtube"
            )
        )
        assertTrue(
            OverlayLifecycleGate.shouldRetainForNoise(
                "com.google.android.youtube",
                "com.google.android.youtube"
            )
        )
        assertFalse(
            OverlayLifecycleGate.shouldRetainForNoise(
                "com.android.chrome",
                "com.google.android.youtube"
            )
        )
    }

    @Test
    fun awayDebounceRequiresElapsedTime() {
        assertFalse(
            OverlayLifecycleGate.shouldClearAfterAway(
                candidatePackage = "com.miui.home",
                trackedCandidate = "com.miui.home",
                awaySinceMillis = 1_000L,
                nowMillis = 1_500L,
                debounceMs = 1_200L
            )
        )
        assertTrue(
            OverlayLifecycleGate.shouldClearAfterAway(
                candidatePackage = "com.miui.home",
                trackedCandidate = "com.miui.home",
                awaySinceMillis = 1_000L,
                nowMillis = 2_300L,
                debounceMs = 1_200L
            )
        )
    }

    @Test
    fun decisionHoldPreventsChurn() {
        assertTrue(
            OverlayLifecycleGate.shouldHoldSameDecision(
                packageName = "com.google.android.youtube",
                decision = "BLOCK",
                lastPackage = "com.google.android.youtube",
                lastDecision = "BLOCK",
                lastAppliedAtMillis = 1000L,
                nowMillis = 1500L,
                holdMs = 1500L
            )
        )
        assertFalse(
            OverlayLifecycleGate.shouldHoldSameDecision(
                packageName = "com.google.android.youtube",
                decision = "ALLOW",
                lastPackage = "com.google.android.youtube",
                lastDecision = "BLOCK",
                lastAppliedAtMillis = 1000L,
                nowMillis = 1100L,
                holdMs = 1500L
            )
        )
    }

    @Test
    fun warningClearsOnAllow() {
        assertTrue(OverlayLifecycleGate.shouldClearWarningOnAllow())
    }
}

class QuotaEnforcementGateTest {

    @Test
    fun countsFirstEventsThenBlocksAfterLimit() {
        val gate = QuotaEnforcementGate()
        val first = gate.evaluate("shorts", "sig-1", limit = 2)
        assertEquals(QuotaVerdict.ALLOW_UNDER_LIMIT, first.verdict)
        assertEquals(1, first.count)

        val second = gate.evaluate("shorts", "sig-2", limit = 2)
        assertEquals(QuotaVerdict.ALLOW_UNDER_LIMIT, second.verdict)
        assertEquals(2, second.count)

        val third = gate.evaluate("shorts", "sig-3", limit = 2)
        assertEquals(QuotaVerdict.BLOCK_OVER_LIMIT, third.verdict)
        assertEquals(3, third.count)
    }

    @Test
    fun duplicateSignatureDoesNotDoubleCount() {
        val gate = QuotaEnforcementGate()
        gate.evaluate("shorts", "same", limit = 3)
        val dup = gate.evaluate("shorts", "same", limit = 3)
        assertEquals(QuotaVerdict.DUPLICATE_IGNORED, dup.verdict)
        assertEquals(1, dup.count)
    }

    @Test
    fun parseShortsQuotaFromGoal() {
        assertEquals(40, QuotaEnforcementGate.parseShortsQuotaLimit("allow 40 shorts then stop"))
        assertEquals(null, QuotaEnforcementGate.parseShortsQuotaLimit("no shorts today"))
    }
}

class EnforcementEventGateThrottleTest {

    @Test
    fun throttlesSamePackageWithinInterval() {
        assertTrue(
            EnforcementEventGate.shouldThrottleClassificationRequest(
                packageName = "com.android.chrome",
                lastRequestPackage = "com.android.chrome",
                lastRequestAtMillis = 1000L,
                nowMillis = 2000L,
                classificationInFlight = false,
                minIntervalMs = 2500L
            )
        )
    }

    @Test
    fun allowsNewPackageImmediately() {
        assertFalse(
            EnforcementEventGate.shouldThrottleClassificationRequest(
                packageName = "com.google.android.youtube",
                lastRequestPackage = "com.android.chrome",
                lastRequestAtMillis = 1000L,
                nowMillis = 1100L,
                classificationInFlight = false,
                minIntervalMs = 2500L
            )
        )
    }

    @Test
    fun inFlightAlwaysThrottles() {
        assertTrue(
            EnforcementEventGate.shouldThrottleClassificationRequest(
                packageName = "com.android.chrome",
                lastRequestPackage = null,
                lastRequestAtMillis = 0L,
                nowMillis = 5000L,
                classificationInFlight = true
            )
        )
    }
}
