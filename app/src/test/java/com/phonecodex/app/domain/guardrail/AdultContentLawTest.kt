package com.phonecodex.app.domain.guardrail

import com.phonecodex.app.domain.enforcement.OverlayLifecycleGate
import com.phonecodex.app.domain.enforcement.VideoPlatformRegistry
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AdultContentLawTest {

    @Test
    fun youtubeVideoIdContainingPorn_isNotAHit() {
        val tree =
            "Like Dislike Comment Share Remix Raj Shamani Shorts " +
                "https://m.youtube.com/watch?v=abPornXy12Q 646K views 7 days ago"
        val verdict = AdultContentLaw.inspect(VideoPlatformRegistry.CHROME, tree)
        assertEquals(AdultContentLaw.Decision.NONE, verdict.decision)
        assertFalse(AdultContentLaw.isHardBlock(tree))
    }

    @Test
    fun shamaniShortsChromeTree_isNotAdult() {
        val tree =
            "Home Shorts Subscriptions You " +
                "Raj Shamani Shorts 646K views · 7 days ago " +
                "m.youtube.com/playlist Like Dislike Comment Share Remix"
        val verdict = AdultContentLaw.inspect(VideoPlatformRegistry.CHROME, tree)
        assertEquals(AdultContentLaw.Decision.NONE, verdict.decision)
    }

    @Test
    fun overlayEchoBlockPorn_isStripped() {
        val echo =
            "Outside your promise You promised this. " +
                "Permanent guardrail: Block Porn (matched: strong: porn)"
        val verdict = AdultContentLaw.inspect(VideoPlatformRegistry.CHROME, echo)
        assertEquals(AdultContentLaw.Decision.NONE, verdict.decision)
        assertFalse(AdultContentLaw.stripSelfEcho(echo).contains("porn"))
    }

    @Test
    fun smashedOverlayCopy_doesNotCreateStickyPornHit() {
        val smashed = "Outsiddeyourpromisee Permanenttguardrail:BlockkPornn(matchedd:strongg:pornn)"
        assertFalse(AdultContentLaw.isHardBlock(smashed))
    }

    @Test
    fun onePornWordOnChrome_isIgnoredNotBlocked() {
        val verdict = AdultContentLaw.inspect(
            VideoPlatformRegistry.CHROME,
            "Raj Shamani podcast mentions porn once in a comment"
        )
        assertEquals(AdultContentLaw.Decision.NONE, verdict.decision)
        assertFalse(verdict.isHardBlock)
    }

    @Test
    fun onePornWordOnQuietApp_isWarn() {
        val verdict = AdultContentLaw.inspect(
            "com.lonely.notes",
            "download porn tonight"
        )
        assertEquals(AdultContentLaw.Decision.WARN, verdict.decision)
    }

    @Test
    fun twoWeakWords_blockEvenOnChrome() {
        val verdict = AdultContentLaw.inspect(
            VideoPlatformRegistry.CHROME,
            "nsfw nude clip"
        )
        assertEquals(AdultContentLaw.Decision.BLOCK, verdict.decision)
        assertTrue(AdultContentLaw.isHardBlock("nsfw nude clip"))
    }

    @Test
    fun pornhubSite_isHardBlock() {
        val verdict = AdultContentLaw.inspect(
            VideoPlatformRegistry.CHROME,
            "Pornhub video player"
        )
        assertEquals(AdultContentLaw.Decision.BLOCK, verdict.decision)
        assertEquals(listOf("pornhub"), verdict.strongSites)
    }

    @Test
    fun systemUiAndOwnPackage_areSkipped() {
        val text = "pornhub xvideos"
        assertEquals(
            AdultContentLaw.Decision.NONE,
            AdultContentLaw.inspect("com.android.systemui", text).decision
        )
        assertEquals(
            AdultContentLaw.Decision.NONE,
            AdultContentLaw.inspect(OverlayLifecycleGate.OWN_PACKAGE, text).decision
        )
    }
}
