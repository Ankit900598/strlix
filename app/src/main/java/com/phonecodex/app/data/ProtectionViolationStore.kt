package com.phonecodex.app.data

import android.content.Context
import com.phonecodex.app.domain.protection.ProtectionViolationPolicy

data class ProtectionViolationState(
    val violationCount: Int,
    val lastViolationMillis: Long,
    val lastReason: String?
)

class ProtectionViolationStore(context: Context) {

    private val prefs = context.applicationContext.getSharedPreferences(
        PREFS_NAME,
        Context.MODE_PRIVATE
    )

    fun getState(): ProtectionViolationState {
        return ProtectionViolationState(
            violationCount = prefs.getInt(KEY_VIOLATION_COUNT, 0),
            lastViolationMillis = prefs.getLong(KEY_LAST_VIOLATION_MILLIS, 0L),
            lastReason = prefs.getString(KEY_LAST_REASON, null)
        )
    }

    fun recordViolation(reason: String, nowMillis: Long = System.currentTimeMillis()): Boolean {
        val lastViolationMillis = prefs.getLong(KEY_LAST_VIOLATION_MILLIS, 0L)
        if (!ProtectionViolationPolicy.shouldRecordViolation(lastViolationMillis, nowMillis)) {
            return false
        }

        val violationCount = prefs.getInt(KEY_VIOLATION_COUNT, 0) + 1
        prefs.edit()
            .putLong(KEY_LAST_VIOLATION_MILLIS, nowMillis)
            .putInt(KEY_VIOLATION_COUNT, violationCount)
            .putString(KEY_LAST_REASON, reason)
            .putBoolean(KEY_PENDING_CONSEQUENCES, true)
            .apply()
        return true
    }

    fun clearViolations() {
        prefs.edit().clear().apply()
    }

    fun consumePendingConsequences(): Boolean {
        val pending = prefs.getBoolean(KEY_PENDING_CONSEQUENCES, false)
        if (!pending) return false

        prefs.edit()
            .putBoolean(KEY_PENDING_CONSEQUENCES, false)
            .apply()
        return true
    }

    companion object {
        private const val PREFS_NAME = "phonecodex_protection_violations"
        private const val KEY_LAST_VIOLATION_MILLIS = "lastViolationMillis"
        private const val KEY_VIOLATION_COUNT = "violationCount"
        private const val KEY_LAST_REASON = "lastReason"
        private const val KEY_PENDING_CONSEQUENCES = "pendingConsequences"

        const val REASON_ACCESSIBILITY_DISABLED_DURING_COMMITMENT =
            "Accessibility protection disabled during active commitment"
    }
}
