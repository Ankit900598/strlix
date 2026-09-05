package com.phonecodex.app.domain.protection

object ProtectionViolationPolicy {

    fun shouldRecordViolation(
        lastViolationMillis: Long,
        nowMillis: Long,
        cooldownMillis: Long = DEFAULT_COOLDOWN_MILLIS
    ): Boolean {
        if (lastViolationMillis <= 0L) return true
        return nowMillis - lastViolationMillis >= cooldownMillis
    }

    const val DEFAULT_COOLDOWN_MILLIS = 60_000L
}
