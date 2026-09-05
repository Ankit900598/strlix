package com.phonecodex.app.domain.protection

import com.phonecodex.app.domain.model.FocusSession
import com.phonecodex.app.domain.model.SessionStatus

object ProtectionHeartbeatLogic {

    fun shouldKeepRunning(session: FocusSession?): Boolean {
        return when (session?.status) {
            SessionStatus.ACTIVE, SessionStatus.LOCKED -> true
            else -> false
        }
    }

    fun shouldRecordAccessibilityViolation(
        session: FocusSession?,
        accessibilityEnabled: Boolean
    ): Boolean {
        return shouldKeepRunning(session) && !accessibilityEnabled
    }
}
