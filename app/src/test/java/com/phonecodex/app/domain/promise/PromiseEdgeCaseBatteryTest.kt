package com.phonecodex.app.domain.promise

import com.phonecodex.app.domain.model.ContentRuleAction
import com.phonecodex.app.domain.signals.ContentSignalDetector
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Phase 5 — edge-case battery for commitment OS trust.
 */
class PromiseEdgeCaseBatteryTest {

    private val parser = FocusPromiseParser()
    private val detector = ContentSignalDetector()

    @Test
    fun contentDurationDoesNotBecomeSessionDuration() {
        val draft = parser.parse(
            "only allow YouTube videos longer than 40 min for next 90 minutes"
        )
        assertEquals(90, draft.sessionDurationMinutes)
        assertTrue(draft.contentRules.any { it.value == 40 && it.operator == "gt" })
    }

    @Test
    fun allowExceptChromeLongYoutube() {
        val draft = parser.parse(
            "allow everything on chrome except youtube whose length is greater than 20 min for next 1 hrs"
        )
        assertTrue(PromiseIntentRules.allowsBroadChromeUse(draft.rawText))
        assertFalse(PromiseIntentRules.blocksShortForm(draft.rawText))
        assertEquals(
            com.phonecodex.app.domain.model.AppRuleBehavior.ALLOW,
            draft.suggestedAppRules.first { it.packageName == "com.android.chrome" }.behavior
        )
    }

    @Test
    fun instagramMessagesVsReelsSurface() {
        val draft = parser.parse("Instagram only for messages for 7 days. no reels")
        assertTrue(draft.contentRules.any { it.surface == "messages" && it.action == ContentRuleAction.ALLOW })
        assertTrue(draft.contentRules.any { it.surface == "reels" && it.action == ContentRuleAction.BLOCK })
    }

    @Test
    fun noPornDoesNotSuggestDocsOrDriveRules() {
        val draft = parser.parse("no porn for 1 year rest normal")
        assertTrue(draft.contentRules.any { it.contentType == "adult_sexual" })
        assertFalse(draft.suggestedAppRules.any { it.label.contains("Docs", ignoreCase = true) })
        assertTrue(
            PromiseIntentRules.isUnrelatedProductivityPackage(
                "com.google.android.apps.drive",
                draft.rawText
            )
        )
    }

    @Test
    fun shortsShelfVsPlayer() {
        assertFalse(
            detector.detect(
                "com.google.android.youtube",
                "Home Shorts Subscriptions Library Shorts shelf recommended for you"
            ).isYouTubeShorts
        )
        assertTrue(
            detector.detect(
                "com.google.android.youtube",
                "Funny clip Swipe up for more Shorts"
            ).isYouTubeShorts
        )
    }

    @Test
    fun chromeYoutubeLongVideoOverLimit() {
        val goal = "allow everything on chrome except youtube whose length is greater than 20 min"
        assertTrue(
            PromiseIntentRules.chromeYouTubeVideoExceedsGoalLimit(
                goal,
                "Hide player controls Time duration 1 hour 5 minutes YouTube"
            )
        )
        assertFalse(
            PromiseIntentRules.chromeYouTubeVideoExceedsGoalLimit(
                goal,
                "Hide player controls Time duration 8 minutes YouTube"
            )
        )
    }

    @Test
    fun chromeNormalSearchIsNotYoutubeSurface() {
        assertFalse(
            PromiseIntentRules.isYouTubeSurfaceInChrome(
                "Google Search weather Delhi results News Shopping"
            )
        )
    }

    @Test
    fun unclearPromisesRequireClarification() {
        assertTrue(parser.parse("focus mode").needsClarification)
        assertTrue(parser.parse("make me strict today").needsClarification)
        assertTrue(parser.parse("use insta less").needsClarification)
        assertTrue(
            parser.parse("allow YouTube videos longer than 40 min for next 1 hour")
                .needsClarification
        )
    }

    @Test
    fun safeAppsCatalogIncludesDocsDrive() {
        assertTrue(
            com.phonecodex.app.domain.safeapps.SafeAppsCatalog.isDefaultPackage(
                "com.google.android.apps.docs"
            )
        )
        assertTrue(
            com.phonecodex.app.domain.safeapps.SafeAppsCatalog.isDefaultPackage(
                "com.google.android.apps.drive"
            )
        )
        assertTrue(
            com.phonecodex.app.domain.safeapps.SafeAppsCatalog.isDefaultPackage(
                "com.android.settings"
            )
        )
    }
}
