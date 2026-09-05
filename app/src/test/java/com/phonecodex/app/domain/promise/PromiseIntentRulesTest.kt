package com.phonecodex.app.domain.promise

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PromiseIntentRulesTest {

    @Test
    fun studyOnlyBlocksShortForm() {
        assertTrue(PromiseIntentRules.blocksShortForm("Only study videos for 30 minutes"))
    }

    @Test
    fun explicitShortsAllowanceWinsForQuotaPromises() {
        assertTrue(PromiseIntentRules.allowsShortForm("Allow 40 shorts today but no adult content"))
    }

    @Test
    fun chromeExceptionDoesNotMeanShortsBan() {
        val goal = "allow everything on chrome except youtube whose length is greater than 20 min for next 1 hrs"

        assertTrue(PromiseIntentRules.allowsBroadChromeUse(goal))
        assertFalse(PromiseIntentRules.blocksShortForm(goal))
        assertTrue(PromiseIntentRules.hasLongYouTubeLimit(goal))
    }

    @Test
    fun blockOnlyLongYoutube_doesNotBanShorts() {
        val goal = "block YouTube videos longer than 20 min for next 1 hour"

        assertTrue(PromiseIntentRules.hasLongYouTubeLimit(goal))
        assertFalse(PromiseIntentRules.blocksShortForm(goal))
    }

    @Test
    fun chromeYouTubePlayerSurfaceDetected() {
        assertTrue(
            PromiseIntentRules.isYouTubeSurfaceInChrome(
                "Hide player controls Playback Settings Search YouTube More options"
            )
        )
    }

    @Test
    fun chromeYouTubeDurationOverGoalLimitDetected() {
        val goal = "allow everything on chrome except youtube whose length is greater than 20 min"

        assertTrue(
            PromiseIntentRules.chromeYouTubeVideoExceedsGoalLimit(
                goal = goal,
                screenText = "Hide player controls Time duration 1 hour 25 minutes YouTube"
            )
        )
    }

    @Test
    fun chromeYouTubeDurationUnderGoalLimitAllowedByRule() {
        val goal = "allow everything on chrome except youtube whose length is greater than 20 min"

        assertFalse(
            PromiseIntentRules.chromeYouTubeVideoExceedsGoalLimit(
                goal = goal,
                screenText = "Hide player controls Time duration 12 minutes YouTube"
            )
        )
    }

    @Test
    fun chromeYouTubeSurfaceWithoutDurationWaitsForMoreText() {
        val goal = "allow everything on chrome except youtube whose length is greater than 20 min"

        assertTrue(
            PromiseIntentRules.needsMoreChromeYouTubeDurationText(
                goal = goal,
                screenText = "Hide player controls Search YouTube"
            )
        )
    }

    @Test
    fun explicitNoShortsBlocksShortForm() {
        assertTrue(PromiseIntentRules.blocksShortForm("Use YouTube for OS lectures but no shorts"))
    }

    @Test
    fun driveDocsAreUnrelatedProductivityUnlessNamedBlocked() {
        assertTrue(
            PromiseIntentRules.isUnrelatedProductivityPackage(
                "com.google.android.apps.docs",
                "no porn for 1 year rest normal"
            )
        )
        assertFalse(
            PromiseIntentRules.isUnrelatedProductivityPackage(
                "com.google.android.apps.docs",
                "block docs and drive for 2 hours"
            )
        )
    }
}
