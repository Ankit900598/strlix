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
                accessibilityEnabled = false
            )
        )
        assertFalse(
            ProtectionHeartbeatLogic.shouldRecordAccessibilityViolation(
                session = activeSession,
                accessibilityEnabled = true
            )
        )
        assertFalse(
            ProtectionHeartbeatLogic.shouldRecordAccessibilityViolation(
                session = null,
                accessibilityEnabled = false
            )
        )
    }
}
