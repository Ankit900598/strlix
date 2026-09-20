package com.phonecodex.app.ui.home

import com.phonecodex.app.domain.model.AppRule
import com.phonecodex.app.domain.model.AppRuleBehavior
import com.phonecodex.app.domain.model.ContentRule
import com.phonecodex.app.domain.model.ContentRuleAction
import com.phonecodex.app.domain.model.FocusPromise
import com.phonecodex.app.domain.model.StrictnessLevel
import com.phonecodex.app.domain.promise.CompiledPromiseMapper
import com.phonecodex.app.domain.promise.CompiledPromiseResponse
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Confirmation UX must stay human: categories, not package dumps.
 */
class ConfirmationUserCopyTest {

    @Test
    fun userFacingBlob_neverContainsPackageNames() {
        val draft = FocusPromise(
            rawText = "at most 10 shorts today, never adult shorts",
            sessionDurationMinutes = 1440,
            allowedKeywords = emptyList(),
            blockedKeywords = emptyList(),
            strictness = StrictnessLevel.STRICT,
            suggestedAppRules = listOf(
                AppRule("com.google.android.youtube", "YouTube", AppRuleBehavior.ALLOW),
                AppRule("org.schabi.newpipe", "NewPipe", AppRuleBehavior.ALLOW),
                AppRule("com.android.chrome", "Chrome", AppRuleBehavior.ALLOW),
                AppRule("com.instagram.android", "Instagram", AppRuleBehavior.ALLOW)
            ),
            contentRules = listOf(
                ContentRule(
                    appLabel = null,
                    packageName = "com.google.android.youtube",
                    surface = "shorts",
                    contentType = "short_form_video",
                    operator = "lte",
                    value = 10,
                    unit = "count",
                    action = ContentRuleAction.ALLOW
                )
            ),
            allowedSummaries = listOf("first 10 short-form videos today"),
            blockedSummaries = listOf("adult/sexual shorts"),
            conditionalSummaries = listOf(
                "Applies to: YouTube, NewPipe, Instagram, Facebook, TikTok, Snapchat, Chrome"
            ),
            warnings = listOf(
                "I interpreted 'shorts' as all short-form video, including reels-style apps. Change?"
            )
        )

        val ui = buildPromiseUnderstanding(draft, source = UnderstandingSource.PROMISE_COMPILER)
        val blob = ui.userFacingTextBlob()
        assertFalse(ConfirmationUserCopy.containsPackageName(blob))
        assertFalse(blob.contains("com.google", ignoreCase = true))
        assertFalse(blob.contains("org.schabi", ignoreCase = true))
        assertFalse(blob.contains("NewPipe", ignoreCase = true))
        assertNotNull(ui.appliesToLabel)
        assertTrue(ui.appliesToLabel!!.contains("short-video", ignoreCase = true))
        assertTrue(ui.managedApps.isEmpty())
    }

    @Test
    fun newPipeShownOnlyWhenUserMentionedIt() {
        val mentioned = FocusPromise(
            rawText = "block NewPipe shorts for 1 hour",
            sessionDurationMinutes = 60,
            allowedKeywords = emptyList(),
            blockedKeywords = emptyList(),
            strictness = StrictnessLevel.STRICT,
            suggestedAppRules = listOf(
                AppRule("org.schabi.newpipe", "NewPipe", AppRuleBehavior.BLOCK)
            )
        )
        val uiMentioned = buildPromiseUnderstanding(mentioned)
        assertTrue(uiMentioned.managedApps.any { it.equals("NewPipe", ignoreCase = true) })

        val silent = FocusPromise(
            rawText = "block shorts for 1 hour",
            sessionDurationMinutes = 60,
            allowedKeywords = emptyList(),
            blockedKeywords = emptyList(),
            strictness = StrictnessLevel.STRICT,
            suggestedAppRules = listOf(
                AppRule("org.schabi.newpipe", "NewPipe", AppRuleBehavior.BLOCK)
            )
        )
        val uiSilent = buildPromiseUnderstanding(silent)
        assertFalse(uiSilent.userFacingTextBlob().contains("NewPipe", ignoreCase = true))
    }

    @Test
    fun compiledResponseWithScopePackages_doesNotLeakIntoConfirmation() {
        val response = CompiledPromiseResponse(
            rawText = "at most 10 shorts today never adult",
            sessionDurationMinutes = 1440,
            strictness = "STRICT",
            allowedSummaries = listOf("first 10 short-form today"),
            blockedSummaries = listOf("adult always blocked"),
            conditionalSummaries = listOf(
                "Applies to: YouTube, Instagram, Facebook, TikTok, NewPipe, Chrome"
            ),
            contentRules = emptyList(),
            clarificationQuestion = null,
            cautionMessages = listOf(
                "I interpreted 'shorts' as all short-form video, including reels-style apps. Change?"
            ),
            source = "azure_promise_compiler",
            confidence = 0.9,
            suggestedAppRules = listOf(
                com.phonecodex.app.domain.promise.CompiledAppRuleDto(
                    "org.schabi.newpipe",
                    "NewPipe",
                    "ALLOW"
                ),
                com.phonecodex.app.domain.promise.CompiledAppRuleDto(
                    "com.google.android.youtube",
                    "YouTube",
                    "ALLOW"
                )
            ),
            scopePackages = listOf(
                "com.google.android.youtube",
                "org.schabi.newpipe",
                "com.android.chrome"
            ),
            interpretationNotes = listOf(
                "I interpreted 'shorts' as all short-form video, including reels-style apps. Change?"
            )
        )
        val draft = CompiledPromiseMapper.toFocusPromise(response)
        // Internal scopePackages stay on DTO / rules — UI must sanitize.
        val ui = buildPromiseUnderstanding(draft, source = UnderstandingSource.PROMISE_COMPILER)
        assertFalse(ConfirmationUserCopy.containsPackageName(ui.userFacingTextBlob()))
        assertFalse(ui.userFacingTextBlob().contains("NewPipe", ignoreCase = true))
        assertTrue(ui.canStart)
    }

    /**
     * Worst-case backend DTO: raw package IDs planted in EVERY user-facing field
     * position the confirmation UI renders. Nothing may leak "com." / "org.schabi".
     */
    @Test
    fun packageIdsInEveryUserFacingField_renderAsCategoryWordsNotPackages() {
        val yt = "com.google.android.youtube"
        val np = "org.schabi.newpipe"
        val response = CompiledPromiseResponse(
            rawText = "10 shorts today max",
            sessionDurationMinutes = 1440,
            strictness = "STRICT",
            allowedSummaries = listOf("first 10 shorts on $yt"),
            blockedSummaries = listOf("$np always", "shorts on $yt after 10"),
            conditionalSummaries = listOf("Applies to: $yt, $np"),
            contentRules = listOf(
                com.phonecodex.app.domain.promise.CompiledContentRuleDto(
                    appLabel = yt,
                    packageName = yt,
                    surface = "shorts",
                    contentType = "short_form_video",
                    operator = "lte",
                    value = 10,
                    unit = "count",
                    action = "ALLOW"
                )
            ),
            clarificationQuestion = "Should $np count toward the $yt quota?",
            cautionMessages = listOf("I expanded shorts to $np too"),
            source = "azure_promise_compiler",
            confidence = 0.9,
            suggestedAppRules = listOf(
                com.phonecodex.app.domain.promise.CompiledAppRuleDto(yt, yt, "ALLOW"),
                com.phonecodex.app.domain.promise.CompiledAppRuleDto(np, np, "ALLOW")
            ),
            scopePackages = listOf(yt, np, "com.android.chrome"),
            interpretationNotes = listOf("Interpreted shorts as $yt shorts and $np"),
            clarificationOptions = listOf(
                com.phonecodex.app.domain.promise.ClarificationOptionDto(
                    id = "A",
                    label = "$yt only",
                    description = "Count only $yt shorts",
                    recommended = true,
                    policyPreview = "Quota applies to $yt"
                ),
                com.phonecodex.app.domain.promise.ClarificationOptionDto(
                    id = "B",
                    label = np,
                    description = "Include $np",
                    recommended = false,
                    policyPreview = "Quota applies to $yt and $np"
                )
            ),
            clarificationRequired = true,
            canStartCommitment = false,
            userFacingConfirmation = com.phonecodex.app.domain.promise.UserFacingConfirmationDto(
                understood = "I understood: 10 shorts on $yt and $np today",
                allowed = listOf("first 10 short plays on $yt"),
                blocked = listOf("$np shorts after quota"),
                time = "Today until midnight on $yt",
                appliesTo = "$yt, $np, com.android.chrome",
                checkThis = listOf("I included $np as a shorts app"),
                safetyNotes = listOf("adult content stays blocked on $yt")
            )
        )

        val draft = CompiledPromiseMapper.toFocusPromise(response)
        val ui = buildPromiseUnderstanding(draft, source = UnderstandingSource.PROMISE_COMPILER)
        val blob = ui.userFacingTextBlob()

        assertFalse("package regex leak in: $blob", ConfirmationUserCopy.containsPackageName(blob))
        assertFalse("com. leak in: $blob", blob.contains("com.", ignoreCase = true))
        assertFalse("org.schabi leak in: $blob", blob.contains("org.schabi", ignoreCase = true))
        // Copy stays informative — category words, not empty rows.
        assertTrue(blob.contains("YouTube/video apps"))
        // Clarification stays fail-closed with leak-heavy DTO.
        assertFalse(ui.canStart)
        assertEquals(2, ui.clarificationOptions.size)
        // Every option must remain tappable (non-blank label) after sanitizing.
        assertTrue(ui.clarificationOptions.all { it.label.isNotBlank() })
    }

    @Test
    fun sanitize_mapsKnownPackagesToCategoryWords() {
        val promise = "10 shorts today"
        assertEquals(
            "YouTube/video apps",
            ConfirmationUserCopy.sanitize("com.google.android.youtube", promise)
        )
        assertEquals(
            "YouTube/video apps",
            ConfirmationUserCopy.sanitize("org.schabi.newpipe", promise)
        )
        assertEquals(
            "short-form video",
            ConfirmationUserCopy.sanitize("com.instagram.android", promise)
        )
        assertEquals(
            "browser video",
            ConfirmationUserCopy.sanitize("com.android.chrome", promise)
        )
        assertEquals(
            "adult content",
            ConfirmationUserCopy.sanitize("com.example.pornapp", promise)
        )
        // Unknown packages are dropped, not echoed.
        assertEquals("", ConfirmationUserCopy.sanitize("net.example.mystery", promise))
        // ReVanced-style app.* IDs are caught too.
        assertEquals(
            "YouTube/video apps",
            ConfirmationUserCopy.sanitize("app.revanced.android.youtube", promise)
        )
        // Duplicate category words collapse instead of repeating.
        assertEquals(
            "Blocked: YouTube/video apps",
            ConfirmationUserCopy.sanitize(
                "Blocked: com.google.android.youtube, org.schabi.newpipe",
                promise
            )
        )
    }

    @Test
    fun sanitize_doesNotMangleNormalSentences() {
        val promise = "study for 2 hours"
        val text = "Open the app. Then study for 2 hours and check this later."
        assertEquals(text, ConfirmationUserCopy.sanitize(text, promise))
    }

    @Test
    fun unrecognizedChoiceWarning_onlyWhenInvalidOptionIdSelected() {
        assertFalse(
            ConfirmationUserCopy.shouldShowUnrecognizedClarificationChoice(null, listOf("A", "B"))
        )
        assertFalse(
            ConfirmationUserCopy.shouldShowUnrecognizedClarificationChoice("", listOf("A", "B"))
        )
        assertFalse(
            ConfirmationUserCopy.shouldShowUnrecognizedClarificationChoice("A", emptyList())
        )
        assertFalse(
            ConfirmationUserCopy.shouldShowUnrecognizedClarificationChoice("A", listOf("A", "B"))
        )
        assertTrue(
            ConfirmationUserCopy.shouldShowUnrecognizedClarificationChoice("Z", listOf("A", "B"))
        )

        val ghost = FocusPromise(
            rawText = "allow video longer than 50 min for one hours shorter video block",
            sessionDurationMinutes = 60,
            allowedKeywords = emptyList(),
            blockedKeywords = emptyList(),
            strictness = StrictnessLevel.STRICT,
            suggestedAppRules = emptyList(),
            contentRules = listOf(
                ContentRule(
                    appLabel = null,
                    packageName = null,
                    surface = "video",
                    contentType = "long_form_video",
                    operator = "gt",
                    value = 50,
                    unit = "minutes",
                    action = ContentRuleAction.ALLOW
                ),
                ContentRule(
                    appLabel = null,
                    packageName = null,
                    surface = "video",
                    contentType = "long_form_video",
                    operator = "lte",
                    value = 50,
                    unit = "minutes",
                    action = ContentRuleAction.BLOCK
                )
            ),
            warnings = listOf(ConfirmationUserCopy.UNRECOGNIZED_CLARIFICATION_CHOICE),
            checkThisNotes = listOf(ConfirmationUserCopy.UNRECOGNIZED_CLARIFICATION_CHOICE),
            clarificationRequired = true,
            canStartCommitment = false,
            understoodSummary = "For one hour, only videos longer than 50 minutes are allowed; shorter videos are blocked."
        )
        val ui = buildPromiseUnderstanding(ghost, source = UnderstandingSource.PROMISE_COMPILER)
        assertTrue(ui.canStart)
        assertFalse(
            ui.cautions.any { ConfirmationUserCopy.isUnrecognizedClarificationChoice(it) }
        )
        assertFalse(ui.userFacingTextBlob().contains("not recognized", ignoreCase = true))

        val invalidPick = ghost.copy(
            clarificationQuestion = "Which scope?",
            clarificationOptions = listOf(
                com.phonecodex.app.domain.model.ClarificationOption(
                    id = "A",
                    label = "Chrome / browser videos",
                    description = "Browser only"
                ),
                com.phonecodex.app.domain.model.ClarificationOption(
                    id = "B",
                    label = "All video apps",
                    description = "Every video app"
                )
            ),
            clarificationRequired = true,
            canStartCommitment = false
        )
        val blocked = buildPromiseUnderstanding(
            draft = invalidPick,
            source = UnderstandingSource.PROMISE_COMPILER,
            selectedClarificationOptionId = "Z"
        )
        assertFalse(blocked.canStart)
        assertTrue(
            blocked.cautions.any { ConfirmationUserCopy.isUnrecognizedClarificationChoice(it) }
        )
    }

    @Test
    fun packageOnlyAppliesTo_fallsBackToCategoryNeverBlankOrRaw() {
        val draft = FocusPromise(
            rawText = "10 shorts today",
            sessionDurationMinutes = 1440,
            allowedKeywords = emptyList(),
            blockedKeywords = emptyList(),
            strictness = StrictnessLevel.STRICT,
            suggestedAppRules = emptyList(),
            userFacingAppliesTo = "com.google.android.youtube",
            canStartCommitment = true
        )
        val ui = buildPromiseUnderstanding(draft, source = UnderstandingSource.PROMISE_COMPILER)
        assertEquals("YouTube/video apps", ui.appliesToLabel)
    }
}
