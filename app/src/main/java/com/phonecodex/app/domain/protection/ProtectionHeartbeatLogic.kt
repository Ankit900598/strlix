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
        accessibilityEnabled: Boolean,
        disabledContinuouslyMillis: Long = A11Y_DISABLE_GRACE_MS,
        graceMillis: Long = A11Y_DISABLE_GRACE_MS
    ): Boolean {
        return shouldKeepRunning(session) &&
            !accessibilityEnabled &&
            disabledContinuouslyMillis >= graceMillis
    }

    /**
     * Xiaomi/MIUI often kills and rebinds Accessibility for a few seconds.
     * Lock only after a sustained off window — not a bounce.
     */
    fun shouldLockForAccessibilityOutage(
        disabledContinuouslyMillis: Long,
        graceMillis: Long = A11Y_DISABLE_GRACE_MS
    ): Boolean = disabledContinuouslyMillis >= graceMillis

    const val A11Y_DISABLE_GRACE_MS = 20_000L
}
