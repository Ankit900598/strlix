package com.phonecodex.app.ui.home

import com.phonecodex.app.domain.model.AppRule
import com.phonecodex.app.domain.model.AppRuleBehavior
import com.phonecodex.app.domain.model.ContentRule
import com.phonecodex.app.domain.model.ContentRuleAction
import com.phonecodex.app.domain.model.FocusPromise
import com.phonecodex.app.domain.model.StrictnessLevel
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class PromiseUnderstandingTest {

    @Test
    fun clarificationBlocksStart() {
        val draft = FocusPromise(
            rawText = "be strict today",
            sessionDurationMinutes = 1440,
            allowedKeywords = emptyList(),
            blockedKeywords = emptyList(),
            strictness = StrictnessLevel.STRICT,
            suggestedAppRules = emptyList(),
            clarificationQuestion = "What apps or content should I restrict today?"
        )

        val ui = buildPromiseUnderstanding(draft)

        assertFalse(ui.canStart)
        assertEquals(draft.clarificationQuestion, ui.clarificationQuestion)
        assertEquals("1 day", ui.sessionTimeLabel)
    }

    @Test
    fun contentAndSessionShownSeparately() {
        val draft = FocusPromise(
            rawText = "block YouTube videos longer than 20 min for next 1 hour",
            sessionDurationMinutes = 60,
            allowedKeywords = listOf("study"),
            blockedKeywords = listOf("shorts"),
            strictness = StrictnessLevel.STRICT,
            suggestedAppRules = listOf(
                AppRule("com.google.android.youtube", "YouTube", AppRuleBehavior.BLOCK)
            ),
            contentRules = listOf(
                ContentRule(
                    appLabel = "YouTube",
                    packageName = "com.google.android.youtube",
                    surface = "video",
                    contentType = "long_form_video",
                    operator = "gt",
                    value = 20,
                    unit = "minutes",
                    action = ContentRuleAction.BLOCK
                )
            )
        )

        val ui = buildPromiseUnderstanding(draft)

        assertTrue(ui.canStart)
        assertEquals("1 hour", ui.sessionTimeLabel)
        assertTrue(ui.blockedLabel.contains("YouTube"))
        assertTrue(ui.blockedLabel.contains("20"))
    }

    @Test
    fun formatDuration_yearsAndDays() {
        assertEquals("7 days", formatDuration(7 * 24 * 60))
        assertEquals("1 year", formatDuration(365 * 24 * 60))
        assertEquals("1 hour", formatDuration(60))
        assertEquals("45 minutes", formatDuration(45))
    }

    @Test
    fun alwaysBlockedLabels_appearInBlocked() {
        val draft = FocusPromise(
            rawText = "study for 30 minutes",
            sessionDurationMinutes = 30,
            allowedKeywords = listOf("study"),
            blockedKeywords = emptyList(),
            strictness = StrictnessLevel.STRICT,
            suggestedAppRules = emptyList()
        )

        val ui = buildPromiseUnderstanding(draft, alwaysBlockedLabels = listOf("adult content"))

        assertTrue(ui.blockedLabel.contains("adult content"))
        assertNotNull(ui.allowedLabel)
    }

    @Test
    fun prefersHumanSummaries_andSessionTimeLabel() {
        val draft = FocusPromise(
            rawText = "only allow YouTube videos longer than 40 min for next 2 hours",
            sessionDurationMinutes = 120,
            allowedKeywords = emptyList(),
            blockedKeywords = emptyList(),
            strictness = StrictnessLevel.STRICT,
            suggestedAppRules = emptyList(),
            allowedSummaries = listOf("YouTube videos longer than 40 min → allowed"),
            blockedSummaries = listOf("YouTube videos up to 40 min → blocked"),
            conditionalSummaries = listOf("YouTube judged live"),
            clarificationQuestion = null
        )

        val ui = buildPromiseUnderstanding(draft)

        assertTrue(ui.canStart)
        assertEquals("2 hours", ui.sessionTimeLabel)
        assertTrue(ui.allowedLabel.contains("longer than 40"))
        assertTrue(ui.blockedLabel.contains("up to 40") || ui.blockedLabel.contains("40"))
        assertEquals("YouTube judged live", ui.conditionalLabel)
    }
}
