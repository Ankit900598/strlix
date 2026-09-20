package com.phonecodex.app.domain.enforcement

import com.phonecodex.app.domain.guardrail.PermanentGuardrailEvaluator
import com.phonecodex.app.domain.model.ClarificationOption
import com.phonecodex.app.domain.model.DecisionType
import com.phonecodex.app.domain.model.FocusPromise
import com.phonecodex.app.domain.model.PermanentGuardrail
import com.phonecodex.app.domain.model.StrictnessLevel
import com.phonecodex.app.domain.safeapps.SafeAppsCatalog
import com.phonecodex.app.ui.home.UnderstandingSource
import com.phonecodex.app.ui.home.buildPromiseUnderstanding
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Promise Enforcement Reliability Gate — 15 invariant families.
 * One user promise must not randomly block passive screens, recs, or wrong apps.
 */
class ReliabilityGateInvariantsTest {

    private val min30 =
        "do not allow videos shorter than 30 minutes for next 1 hour"
    private val gt40 =
        "allow only videos longer than 40 min for 1 hour"
    private val shorts10 =
        "I want at most 10 shorts today, never adult shorts"
    private val pornYear =
        "No porn for 1 year, rest phone normal"

    private val ytHomeShortsShelf =
        "YouTube Home Search Shorts Subscriptions You Explore " +
            "recommended for you 0:45 1:12 52 minutes"
    private val chromeSearchVideoTitles =
        "Google Search Videos Short videos Images About 1,200,000 results " +
            "filters Operating System lecture 12:04 45 minutes"
    private val watchRecsNoPlayerClock =
        "Hide player controls Search Playback Settings youtube.com/watch?v=abc123 " +
            "Up next 2 minutes 4 minutes 8 minutes recommended"
    private val playerUnder30 =
        "Play Pause 00:15 / 00:59 short clip Hide player controls"
    private val playerOver40 =
        "Play Pause 00:15 / 45:00 lecture Hide player controls Time duration 45 minutes"
    private val ytShortPlay =
        "Hide player controls Shorts player swipe up for next 0:45 title"

    // --- Context invariant ---

    @Test
    fun context_passiveRecommendation_cannotMediaLengthBlock() {
        val ctx = EnforcementContext.from(VideoPlatformRegistry.YOUTUBE, ytHomeShortsShelf)
        assertEquals(ActivityState.PASSIVE, ctx.activityState)
        assertNotEquals(EnforcementDurationSource.CURRENT_PLAYER, ctx.durationSource)
        assertFalse(ctx.mayApplyMediaLengthBlock())
        assertEquals(
            MediaLengthLocalDecision.PASS,
            MediaLengthEnforcement.decide(
                VideoPlatformRegistry.YOUTUBE,
                min30,
                ytHomeShortsShelf,
                structuredMaxBlockMinutes = null,
                structuredMinBlockMinutes = 30
            )
        )
    }

    @Test
    fun context_activePlayerCurrentClock_mayMediaLengthBlock() {
        val ctx = EnforcementContext.from(VideoPlatformRegistry.NEWPIPE, playerUnder30)
        assertTrue(ctx.isActivePlayerState)
        assertEquals(EnforcementDurationSource.CURRENT_PLAYER, ctx.durationSource)
        assertTrue(ctx.mayApplyMediaLengthBlock())
    }

    // 1. Passive YouTube/Chrome home + Shorts shelf — no BLOCK/COUNT

    @Test
    fun family1_passiveHomeShortsShelf_noBlockNoCount() {
        for (pkg in listOf(VideoPlatformRegistry.YOUTUBE, VideoPlatformRegistry.CHROME)) {
            val gate = SurfaceEnforcementGate.evaluate(
                pkg,
                ytHomeShortsShelf,
                min30,
                structuredMinBlockMinutes = 30
            )
            assertTrue("$pkg surface PASS", gate.isPass)
            assertFalse(SurfaceEnforcementGate.aiMayWarnOrBlock(gate))
            assertEquals(
                MediaLengthLocalDecision.PASS,
                MediaLengthEnforcement.decide(pkg, min30, ytHomeShortsShelf, null, 30)
            )
            val quota = ShortFormQuotaGate().evaluate(pkg, ytHomeShortsShelf, 10)
            assertEquals(ShortFormQuotaAction.SKIP_NOT_SHORT_PLAY, quota.action)
            assertFalse(quota.counted)
        }
    }

    // 2. Chrome search results with video titles — no BLOCK/COUNT

    @Test
    fun family2_chromeSearchResults_noBlockNoCount() {
        val pkg = VideoPlatformRegistry.CHROME
        assertTrue(SurfaceDetector.detect(pkg, chromeSearchVideoTitles).isPassive)
        assertEquals(
            MediaLengthLocalDecision.PASS,
            MediaLengthEnforcement.decide(pkg, gt40, chromeSearchVideoTitles, null, 40)
        )
        val quota = ShortFormQuotaGate().evaluate(pkg, chromeSearchVideoTitles, 10)
        assertEquals(ShortFormQuotaAction.SKIP_NOT_SHORT_PLAY, quota.action)
        val gate = SurfaceEnforcementGate.evaluate(pkg, chromeSearchVideoTitles, shorts10)
        assertTrue(gate.isPass)
        assertFalse(SurfaceEnforcementGate.aiMayWarnOrBlock(gate))
    }

    // 3. Watch page + rec durations, no current player clock — WAIT not BLOCK

    @Test
    fun family3_watchRecsWithoutPlayerClock_waitNeverBlock() {
        val parsed = VideoDurationParser.parse(watchRecsNoPlayerClock)
        assertNull(parsed.currentPlayerDurationSeconds)
        assertTrue(parsed.recommendationDurationsSeconds.isNotEmpty())
        assertEquals(DurationSource.RECOMMENDATION_IGNORED, parsed.source)

        val detailed = MediaLengthEnforcement.decideDetailed(
            packageName = VideoPlatformRegistry.YOUTUBE,
            goal = min30,
            screenText = watchRecsNoPlayerClock,
            structuredMaxBlockMinutes = null,
            structuredMinBlockMinutes = 30
        )
        assertEquals(MediaLengthLocalDecision.WAIT, detailed.decision)
        assertNotEquals(MediaLengthLocalDecision.BLOCK, detailed.decision)
        val ctx = EnforcementContext.from(VideoPlatformRegistry.YOUTUBE, watchRecsNoPlayerClock)
        assertFalse(ctx.mayApplyMediaLengthBlock())
    }

    // 4. Current player 00:15/00:59 under no-videos-under-30 — BLOCK

    @Test
    fun family4_currentPlayerUnder30_blocks() {
        val decision = MediaLengthEnforcement.decide(
            VideoPlatformRegistry.NEWPIPE,
            min30,
            playerUnder30,
            structuredMaxBlockMinutes = null,
            structuredMinBlockMinutes = 30
        )
        assertEquals(MediaLengthLocalDecision.BLOCK, decision)
        val ctx = EnforcementContext.from(VideoPlatformRegistry.NEWPIPE, playerUnder30)
        assertTrue(ctx.mayApplyMediaLengthBlock())
    }

    // 5. Current player 00:15/45:00 under allow >40 min — ALLOW

    @Test
    fun family5_currentPlayerOver40_allows() {
        assertNull(
            "allow-only longer must not parse as a max ceiling",
            com.phonecodex.app.domain.promise.PromiseIntentRules.extractGoalMaxVideoLimitMinutes(gt40)
        )
        assertEquals(
            40,
            com.phonecodex.app.domain.promise.PromiseIntentRules.extractGoalMinVideoLimitMinutes(gt40)
        )
        val decision = MediaLengthEnforcement.decide(
            VideoPlatformRegistry.NEWPIPE,
            gt40,
            playerOver40,
            structuredMaxBlockMinutes = null,
            structuredMinBlockMinutes = 40
        )
        assertEquals(MediaLengthLocalDecision.ALLOW, decision)
        val shortDecision = MediaLengthEnforcement.decide(
            VideoPlatformRegistry.NEWPIPE,
            gt40,
            playerUnder30,
            structuredMaxBlockMinutes = null,
            structuredMinBlockMinutes = 40
        )
        assertEquals(MediaLengthLocalDecision.BLOCK, shortDecision)
    }

    // 6. Same surface abstraction across YT / Chrome / NewPipe / clone

    @Test
    fun family6_videoClientsShareSurfaceAbstraction() {
        val packages = listOf(
            VideoPlatformRegistry.YOUTUBE,
            VideoPlatformRegistry.CHROME,
            VideoPlatformRegistry.NEWPIPE,
            "com.vanced.android.youtube"
        )
        for (pkg in packages) {
            assertTrue("$pkg must enforce media surfaces", VideoPlatformRegistry.enforcesMediaSurfaces(pkg))
            assertEquals(
                "$pkg home PASS",
                MediaLengthLocalDecision.PASS,
                MediaLengthEnforcement.decide(pkg, min30, ytHomeShortsShelf, null, 30)
            )
            val playerText = if (pkg == VideoPlatformRegistry.NEWPIPE) {
                playerUnder30
            } else {
                "Hide player controls Time duration 59 seconds Shorts player swipe up for next"
            }
            val active = MediaLengthEnforcement.decide(pkg, min30, playerText, null, 30)
            assertTrue(
                "$pkg active must BLOCK or WAIT, not PASS: $active",
                active == MediaLengthLocalDecision.BLOCK || active == MediaLengthLocalDecision.WAIT
            )
        }
    }

    // 7. Quota 10: first 10 allow, 11th block, shelves never count

    @Test
    fun family7_quotaFirst10ThenBlock_passiveNeverCounts() {
        val gate = ShortFormQuotaGate()
        repeat(10) { i ->
            val d = gate.evaluate(
                VideoPlatformRegistry.YOUTUBE,
                "$ytShortPlay clip$i",
                10
            )
            assertEquals("play ${i + 1}", ShortFormQuotaAction.ALLOW_AND_COUNT, d.action)
            assertEquals(i + 1, d.count)
        }
        val eleventh = gate.evaluate(
            VideoPlatformRegistry.YOUTUBE,
            "$ytShortPlay clip11",
            10
        )
        assertEquals(ShortFormQuotaAction.BLOCK_QUOTA_EXCEEDED, eleventh.action)
        assertEquals(10, eleventh.count)

        val before = eleventh.count
        val shelf = gate.evaluate(VideoPlatformRegistry.YOUTUBE, ytHomeShortsShelf, 10)
        assertEquals(ShortFormQuotaAction.SKIP_NOT_SHORT_PLAY, shelf.action)
        assertEquals(before, shelf.count)
        assertFalse(shelf.counted)
    }

    // 8. Adult short blocks immediately, quota unchanged

    @Test
    fun family8_adultShort_blocksWithoutConsumingQuota() {
        val gate = ShortFormQuotaGate()
        gate.evaluate(VideoPlatformRegistry.YOUTUBE, "$ytShortPlay clean1", 10)
        assertEquals(1, gate.currentCount())
        val adult = gate.evaluate(
            VideoPlatformRegistry.YOUTUBE,
            "$ytShortPlay porn xxx nsfw",
            10
        )
        assertEquals(ShortFormQuotaAction.BLOCK_ADULT, adult.action)
        assertEquals(1, adult.count)
        assertFalse(adult.counted)
    }

    // 9. Permanent no-porn: WhatsApp / Drive / launcher stay clean without strong signal

    @Test
    fun family9_permanentNoPorn_neutralAppsStayOpen() {
        val evaluator = PermanentGuardrailEvaluator()
        val guardrails = listOf(pornGuardrail())
        for ((pkg, text) in listOf(
            "com.whatsapp" to "Hey, lecture notes for OS exam tomorrow",
            "com.google.android.apps.docs" to "Drive My Drive Shared with me lecture.pdf",
            "com.miui.home" to "Phone Messages Chrome WhatsApp Drive"
        )) {
            val match = evaluator.evaluate(pkg, text, guardrails)
            assertTrue(
                "$pkg must not BLOCK without adult signal: $match",
                match == null || match.decision != DecisionType.BLOCK
            )
        }
        val strong = evaluator.evaluate(
            "com.android.chrome",
            "visit xvideos now",
            guardrails
        )
        assertNotNull(strong)
        assertEquals(DecisionType.BLOCK, strong!!.decision)
    }

    // 10. Ambiguous promise cannot Start without clarification

    @Test
    fun family10_ambiguousPromise_startBlocked() {
        val draft = FocusPromise(
            rawText = "google video 30 min",
            sessionDurationMinutes = 60,
            allowedKeywords = emptyList(),
            blockedKeywords = emptyList(),
            strictness = StrictnessLevel.STRICT,
            suggestedAppRules = emptyList(),
            clarificationQuestion = "When you said Google video, what did you mean?",
            clarificationOptions = listOf(
                ClarificationOption("A", "Videos in Chrome", "Browser only", true),
                ClarificationOption("B", "All video apps", "Every video app", false)
            ),
            clarificationRequired = true,
            canStartCommitment = true
        )
        val ui = buildPromiseUnderstanding(draft, source = UnderstandingSource.PROMISE_COMPILER)
        assertFalse(ui.canStart)
        assertEquals("Needs one clarification", ui.statusLabel)
    }

    // 11. MIUI launcher is not a violation

    @Test
    fun family11_miuiHome_launcherPassNeverViolation() {
        val pkg = "com.miui.home"
        val text = "Phone Messages Chrome WhatsApp YouTube Drive"
        val detection = SurfaceDetector.detect(pkg, text)
        assertEquals(SurfaceDetectionResult.LAUNCHER, detection.surface)
        val ctx = EnforcementContext.from(pkg, text)
        assertEquals(SurfaceFamily.LAUNCHER, ctx.surfaceFamily)
        assertEquals(ActivityState.PASSIVE, ctx.activityState)
        assertFalse(ctx.mayApplyMediaLengthBlock())
        val gate = SurfaceEnforcementGate.evaluate(pkg, text, min30, structuredMinBlockMinutes = 30)
        assertTrue(gate.isPass)
        assertNotEquals(
            MediaLengthLocalDecision.BLOCK,
            MediaLengthEnforcement.decide(pkg, min30, text, null, 30)
        )
        assertTrue(SafeAppsCatalog.isDefaultPackage(pkg))
    }

    // 12. Backend AI cannot override Surface Gate PASS

    @Test
    fun family12_aiCannotOverrideSurfacePass() {
        val gate = SurfaceEnforcementGate.evaluate(
            VideoPlatformRegistry.CHROME,
            ytHomeShortsShelf,
            min30,
            structuredMinBlockMinutes = 30
        )
        assertTrue(gate.isPass)
        assertFalse(SurfaceEnforcementGate.aiMayWarnOrBlock(gate))
        val log = EnforcementDecisionLog.format(
            packageName = VideoPlatformRegistry.CHROME,
            surface = gate.detection.surface.name,
            rule = "Surface Gate",
            decision = "PASS",
            reasonCode = EnforcementReasonCodes.AI_SUPPRESSED_BY_SURFACE_GATE,
            reason = "AI WARN suppressed",
            activity = "passive",
            durationSource = "recommendation"
        )
        assertTrue(log.contains("code=${EnforcementReasonCodes.AI_SUPPRESSED_BY_SURFACE_GATE}"))
        assertTrue(log.contains("durationSource=recommendation"))
    }

    // 13. Emergency / safe apps remain allowed

    @Test
    fun family13_emergencyAndSafeAppsRemainAllowed() {
        for (pkg in listOf(
            "com.android.dialer",
            "com.google.android.dialer",
            "com.android.contacts",
            "com.openai.chatgpt",
            "com.whatsapp",
            "com.google.android.apps.docs"
        )) {
            assertTrue("$pkg must stay in SafeAppsCatalog", SafeAppsCatalog.isDefaultPackage(pkg))
        }
        val evaluator = PermanentGuardrailEvaluator()
        val match = evaluator.evaluate(
            "com.android.dialer",
            "Call emergency 112",
            listOf(pornGuardrail())
        )
        assertTrue(match == null || match.decision != DecisionType.BLOCK)
    }

    // 14. Own-package a11y events retain overlay (do not hide/show wrongly)

    @Test
    fun family14_ownPackageEventsRetainOverlay() {
        assertTrue(OverlayLifecycleGate.isOwnPackage("com.phonecodex.app"))
        assertTrue(
            OverlayLifecycleGate.shouldRetainForNoise(
                eventPackage = "com.phonecodex.app",
                targetPackage = VideoPlatformRegistry.YOUTUBE
            )
        )
        assertFalse(
            OverlayLifecycleGate.shouldRetainForNoise(
                eventPackage = "com.miui.home",
                targetPackage = VideoPlatformRegistry.YOUTUBE
            )
        )
    }

    // 15. Overlay clear only on true context exit

    @Test
    fun family15_overlayClearsOnExit_notOnSameAppFlicker() {
        assertTrue(OverlayLifecycleGate.shouldClearOverlayOnPassiveAllow(sessionLocked = false))
        assertTrue(OverlayLifecycleGate.shouldClearOverlayOnPassiveAllow(sessionLocked = true))
        assertTrue(
            OverlayLifecycleGate.shouldRetainForNoise(
                eventPackage = VideoPlatformRegistry.YOUTUBE,
                targetPackage = VideoPlatformRegistry.YOUTUBE
            )
        )
        val now = 10_000L
        assertFalse(
            OverlayLifecycleGate.shouldClearAfterAway(
                candidatePackage = "com.miui.home",
                trackedCandidate = "com.miui.home",
                awaySinceMillis = now - 200,
                nowMillis = now
            )
        )
        assertTrue(
            OverlayLifecycleGate.shouldClearAfterAway(
                candidatePackage = "com.miui.home",
                trackedCandidate = "com.miui.home",
                awaySinceMillis = now - OverlayLifecycleGate.AWAY_DEBOUNCE_MS,
                nowMillis = now
            )
        )
        assertTrue(
            OverlayLifecycleGate.shouldHoldSameDecision(
                packageName = VideoPlatformRegistry.YOUTUBE,
                decision = "BLOCK",
                lastPackage = VideoPlatformRegistry.YOUTUBE,
                lastDecision = "BLOCK",
                lastAppliedAtMillis = now - 200,
                nowMillis = now
            )
        )
        assertFalse(
            OverlayLifecycleGate.shouldHoldSameDecision(
                packageName = VideoPlatformRegistry.YOUTUBE,
                decision = "ALLOW",
                lastPackage = VideoPlatformRegistry.YOUTUBE,
                lastDecision = "BLOCK",
                lastAppliedAtMillis = now - 200,
                nowMillis = now
            )
        )
    }

    @Test
    fun reasonCodes_logLineHasStableCodeAndDurationSource() {
        val line = EnforcementDecisionLog.format(
            packageName = VideoPlatformRegistry.YOUTUBE,
            surface = "HOME",
            rule = "Surface Gate",
            decision = "PASS",
            reasonCode = EnforcementReasonCodes.SURFACE_PASS_PASSIVE,
            reason = SurfaceEnforcementGate.PASS_REASON,
            activity = "passive",
            durationSource = "none"
        )
        assertTrue(line.contains("code=SURFACE_PASS_PASSIVE"))
        assertTrue(line.contains("activity=passive"))
        assertTrue(line.contains("durationSource=none"))
    }

    private fun pornGuardrail(): PermanentGuardrail =
        PermanentGuardrail(
            id = "porn_guardrail",
            name = "Block Porn",
            enabled = true,
            blockedKeywords = emptySet(),
            blockedPackages = emptySet(),
            createdAtMillis = 0L,
            expiresAtMillis = null
        )
}
