package com.phonecodex.app.domain.enforcement

import com.phonecodex.app.domain.classifier.AiConfidenceGate
import com.phonecodex.app.domain.classifier.ContentClassification
import com.phonecodex.app.domain.model.DecisionType
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class VisionCounselMergeTest {

    @Test
    fun surfacePass_cannotCreateBlock() {
        val result = VisionCounselMerge.merge(
            localDecision = DecisionType.ALLOW,
            localReasonCode = EnforcementReasonCodes.SURFACE_PASS_PASSIVE,
            surfaceIsPass = true,
            vision = vision(DecisionType.BLOCK, VisionAdvisoryKinds.LIKELY_MOVIE),
            backendUsedImage = true
        )
        assertFalse(result.applyToOverlay)
        assertEquals(EnforcementReasonCodes.VISION_EXPERIMENT_SKIPPED, result.reasonCode)
        assertEquals("surface_pass", result.detail)
    }

    @Test
    fun clockAllow_cannotBeClearedOrOverridden() {
        val result = VisionCounselMerge.merge(
            localDecision = DecisionType.ALLOW,
            localReasonCode = EnforcementReasonCodes.MEDIA_ALLOW_WITHIN_LIMIT,
            surfaceIsPass = false,
            vision = vision(DecisionType.BLOCK, VisionAdvisoryKinds.LIKELY_SHORT_FORM),
            backendUsedImage = true
        )
        assertFalse(result.applyToOverlay)
        assertEquals("local_law_wins", result.detail)
    }

    @Test
    fun clockBlock_cannotBeCleared() {
        val result = VisionCounselMerge.merge(
            localDecision = DecisionType.BLOCK,
            localReasonCode = EnforcementReasonCodes.MEDIA_BLOCK_UNDER_MIN,
            surfaceIsPass = false,
            vision = vision(DecisionType.ALLOW, VisionAdvisoryKinds.LIKELY_LONG_FORM),
            backendUsedImage = true
        )
        assertFalse(result.applyToOverlay)
        assertEquals("local_block", result.detail)
    }

    @Test
    fun unusedImage_isIgnored() {
        val result = VisionCounselMerge.merge(
            localDecision = DecisionType.ALLOW,
            localReasonCode = EnforcementReasonCodes.VIDEO_APP_DURATION_UNAVAILABLE,
            surfaceIsPass = false,
            vision = vision(DecisionType.BLOCK, VisionAdvisoryKinds.LIKELY_SHORT_FORM),
            backendUsedImage = false
        )
        assertFalse(result.applyToOverlay)
        assertEquals("backend_image_unused", result.detail)
    }

    @Test
    fun waitMovieBlock_warnsAndNeverInventOverMax() {
        val result = VisionCounselMerge.merge(
            localDecision = DecisionType.ALLOW,
            localReasonCode = EnforcementReasonCodes.VIDEO_APP_DURATION_UNAVAILABLE,
            surfaceIsPass = false,
            vision = vision(DecisionType.BLOCK, VisionAdvisoryKinds.LIKELY_MOVIE, 0.95),
            backendUsedImage = true
        )
        assertTrue(result.applyToOverlay)
        assertEquals(DecisionType.WARN, result.classification?.decision)
        assertEquals(EnforcementReasonCodes.VISION_COUNSEL, result.reasonCode)
        assertNotEquals(EnforcementReasonCodes.MEDIA_BLOCK_OVER_MAX, result.reasonCode)
    }

    @Test
    fun waitShortForm_canSupportBlock() {
        val result = VisionCounselMerge.merge(
            localDecision = DecisionType.ALLOW,
            localReasonCode = EnforcementReasonCodes.MEDIA_WAIT_NO_PLAYER_CLOCK,
            surfaceIsPass = false,
            vision = vision(DecisionType.BLOCK, VisionAdvisoryKinds.LIKELY_SHORT_FORM, 0.92),
            backendUsedImage = true
        )
        assertTrue(result.applyToOverlay)
        assertEquals(DecisionType.BLOCK, result.classification?.decision)
        assertEquals(EnforcementReasonCodes.VISION_COUNSEL, result.reasonCode)
    }

    @Test
    fun waitUnknown_doesNotApplyOverlay() {
        val result = VisionCounselMerge.merge(
            localDecision = DecisionType.ALLOW,
            localReasonCode = EnforcementReasonCodes.VIDEO_APP_DURATION_UNAVAILABLE,
            surfaceIsPass = false,
            vision = vision(DecisionType.WARN, VisionAdvisoryKinds.UNKNOWN, 0.4),
            backendUsedImage = true
        )
        assertFalse(result.applyToOverlay)
        assertEquals(EnforcementReasonCodes.VISION_COUNSEL, result.reasonCode)
    }

    private fun vision(
        decision: DecisionType,
        category: String,
        confidence: Double = 0.9
    ): ContentClassification = ContentClassification(
        decision = decision,
        confidence = confidence,
        reason = "frame counsel",
        source = AiConfidenceGate.NETWORK_AI_SOURCE,
        reasonCategory = category,
        usedImage = true
    )
}
