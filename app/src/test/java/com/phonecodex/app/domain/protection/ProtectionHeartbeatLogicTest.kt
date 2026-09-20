package com.phonecodex.app.domain.protection

import com.phonecodex.app.domain.model.FocusSession
import com.phonecodex.app.domain.model.SessionStatus
import com.phonecodex.app.domain.model.StrictnessLevel
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ProtectionHeartbeatLogicTest {

    private val activeSession = FocusSession(
        id = "session-1",
        worldId = "study",
        goal = "Study",
        startTimeMillis = 1_000L,
        deadlineMillis = 3_600_000L,
        status = SessionStatus.ACTIVE,
        attemptCount = 0,
        strictness = StrictnessLevel.STRICT
    )

    @Test
    fun shouldKeepRunning_trueForActiveOrLockedSession() {
        assertTrue(ProtectionHeartbeatLogic.shouldKeepRunning(activeSession))
        assertTrue(
            ProtectionHeartbeatLogic.shouldKeepRunning(
                activeSession.copy(status = SessionStatus.LOCKED)
            )
        )
    }

    @Test
    fun shouldKeepRunning_falseWithoutSession() {
        assertFalse(ProtectionHeartbeatLogic.shouldKeepRunning(null))
        assertFalse(
            ProtectionHeartbeatLogic.shouldKeepRunning(
                activeSession.copy(status = SessionStatus.ENDED)
            )
        )
    }

    @Test
    fun shouldRecordAccessibilityViolation_onlyWhenProtectionIsOffDuringSession() {
        assertTrue(
            ProtectionHeartbeatLogic.shouldRecordAccessibilityViolation(
                session = activeSession,
                accessibilityEnabled = false,
                disabledContinuouslyMillis = ProtectionHeartbeatLogic.A11Y_DISABLE_GRACE_MS
            )
        )
        assertFalse(
            ProtectionHeartbeatLogic.shouldRecordAccessibilityViolation(
                session = activeSession,
                accessibilityEnabled = true,
                disabledContinuouslyMillis = ProtectionHeartbeatLogic.A11Y_DISABLE_GRACE_MS
            )
        )
        assertFalse(
            ProtectionHeartbeatLogic.shouldRecordAccessibilityViolation(
                session = null,
                accessibilityEnabled = false,
                disabledContinuouslyMillis = ProtectionHeartbeatLogic.A11Y_DISABLE_GRACE_MS
            )
        )
    }

    @Test
    fun xiaomiA11yBounce_underGrace_doesNotRecordOrLock() {
        assertFalse(
            ProtectionHeartbeatLogic.shouldRecordAccessibilityViolation(
                session = activeSession,
                accessibilityEnabled = false,
                disabledContinuouslyMillis = 3_000L
            )
        )
        assertFalse(
            ProtectionHeartbeatLogic.shouldLockForAccessibilityOutage(3_000L)
        )
    }

    @Test
    fun sustainedA11yOff_pastGrace_recordsAndLocks() {
        assertTrue(
            ProtectionHeartbeatLogic.shouldRecordAccessibilityViolation(
                session = activeSession,
                accessibilityEnabled = false,
                disabledContinuouslyMillis = 25_000L
            )
        )
        assertTrue(
            ProtectionHeartbeatLogic.shouldLockForAccessibilityOutage(25_000L)
        )
    }
}
