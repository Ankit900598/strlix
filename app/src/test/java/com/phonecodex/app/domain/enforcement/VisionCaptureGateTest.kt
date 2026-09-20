package com.phonecodex.app.domain.enforcement

import com.phonecodex.app.domain.model.DecisionType
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.ZoneOffset
import java.time.ZonedDateTime

class VisionCaptureGateTest {

    private val inWindowMs = ZonedDateTime.of(
        2026, 9, 20, 12, 0, 0, 0, IST
    ).toInstant().toEpochMilli()

    @Test
    fun expiredWindow_doesNotCapture() {
        val verdict = VisionCaptureGate.evaluate(
            waitInput(nowEpochMs = VisionExperiment.END_EPOCH_MS)
        )
        assertFalse(verdict.shouldCapture)
        assertEquals(EnforcementReasonCodes.VISION_EXPERIMENT_SKIPPED, verdict.reasonCode)
        assertEquals("window_expired", verdict.detail)
    }

    @Test
    fun toggleOff_doesNotCapture() {
        val verdict = VisionCaptureGate.evaluate(
            waitInput(enabled = false)
        )
        assertFalse(verdict.shouldCapture)
        assertEquals("toggle_off", verdict.detail)
    }

    @Test
    fun surfacePass_doesNotCapture() {
        val verdict = VisionCaptureGate.evaluate(
            waitInput(surfaceIsPass = true)
        )
        assertFalse(verdict.shouldCapture)
        assertEquals("surface_pass", verdict.detail)
    }

    @Test
    fun currentPlayerClock_doesNotCapture() {
        val verdict = VisionCaptureGate.evaluate(
            waitInput(hasCurrentPlayerClock = true)
        )
        assertFalse(verdict.shouldCapture)
        assertEquals("current_player_clock", verdict.detail)
    }

    @Test
    fun mediaAllowFromClock_doesNotCapture() {
        val verdict = VisionCaptureGate.evaluate(
            waitInput().copy(
                localReasonCode = EnforcementReasonCodes.MEDIA_ALLOW_WITHIN_LIMIT,
                localDecision = DecisionType.ALLOW,
                hasCurrentPlayerClock = true
            )
        )
        assertFalse(verdict.shouldCapture)
        assertEquals("current_player_clock", verdict.detail)
    }

    @Test
    fun mediaBlockFromClock_doesNotCapture() {
        val verdict = VisionCaptureGate.evaluate(
            waitInput().copy(
                localReasonCode = EnforcementReasonCodes.MEDIA_BLOCK_UNDER_MIN,
                localDecision = DecisionType.BLOCK,
                hasCurrentPlayerClock = true
            )
        )
        assertFalse(verdict.shouldCapture)
        assertTrue(
            verdict.detail == "current_player_clock" || verdict.detail == "local_block"
        )
    }

    @Test
    fun emergencyDialer_doesNotCapture() {
        val verdict = VisionCaptureGate.evaluate(
            waitInput(packageName = "com.android.dialer")
        )
        assertFalse(verdict.shouldCapture)
        assertEquals("forbidden_or_emergency_surface", verdict.detail)
    }

    @Test
    fun otpText_doesNotCapture() {
        val verdict = VisionCaptureGate.evaluate(
            waitInput(screenText = "Enter OTP 482193 to continue")
        )
        assertFalse(verdict.shouldCapture)
        assertEquals("forbidden_or_emergency_surface", verdict.detail)
    }

    @Test
    fun waitEnabledInWindow_wouldRequest() {
        val verdict = VisionCaptureGate.evaluate(waitInput())
        assertTrue(verdict.shouldCapture)
        assertEquals(EnforcementReasonCodes.VISION_COUNSEL, verdict.reasonCode)
    }

    @Test
    fun netmirrorBlankWait_wouldRequest() {
        val verdict = VisionCaptureGate.evaluate(
            waitInput(
                packageName = VideoPlatformRegistry.NETMIRROR,
                localReasonCode = EnforcementReasonCodes.VIDEO_APP_DURATION_UNAVAILABLE
            )
        )
        assertTrue(verdict.shouldCapture)
    }

    @Test
    fun experimentInactiveWhenExpiredEvenIfToggleOn() {
        assertFalse(
            VisionExperiment.isActive(
                nowEpochMs = VisionExperiment.END_EPOCH_MS,
                visionExperimentEnabled = true
            )
        )
        assertTrue(VisionExperiment.isActive(inWindowMs, true))
        assertFalse(VisionExperiment.isActive(inWindowMs, false))
    }

    private fun waitInput(
        nowEpochMs: Long = inWindowMs,
        enabled: Boolean = true,
        packageName: String = VideoPlatformRegistry.NETMIRROR,
        screenText: String = "Play Pause",
        surfaceIsPass: Boolean = false,
        hasCurrentPlayerClock: Boolean = false,
        localReasonCode: String = EnforcementReasonCodes.VIDEO_APP_DURATION_UNAVAILABLE
    ): VisionCaptureInput = VisionCaptureInput(
        nowEpochMs = nowEpochMs,
        visionExperimentEnabled = enabled,
        hasActiveSession = true,
        packageName = packageName,
        screenText = screenText,
        localReasonCode = localReasonCode,
        localDecision = DecisionType.ALLOW,
        surfaceIsPass = surfaceIsPass,
        hasCurrentPlayerClock = hasCurrentPlayerClock
    )

    companion object {
        private val IST: ZoneOffset = ZoneOffset.ofHoursMinutes(5, 30)
    }
}
