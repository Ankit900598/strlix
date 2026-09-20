package com.phonecodex.app.data

import android.content.Context
import com.phonecodex.app.domain.protection.AccessibilityHeartbeatLaw

data class AccessibilityHeartbeat(
    val lastEventMillis: Long = 0L,
    val packageName: String = "",
    val reason: String = "",
    val serviceAlive: Boolean = false
)

/**
 * Best-effort cross-process flags for developer diagnostics.
 * Written by [com.phonecodex.app.accessibility.PhoneCodexAccessibilityService];
 * read by the UI process. Not a hard guarantee (process death / crash can leave stale true).
 */
class RuntimeDiagStore(context: Context) {

    private val prefs = context.applicationContext.getSharedPreferences(
        PREFS_NAME,
        Context.MODE_PRIVATE
    )

    fun setAccessibilityServiceAlive(alive: Boolean) {
        prefs.edit().putBoolean(KEY_A11Y_ALIVE, alive).apply()
    }

    fun isAccessibilityServiceAlive(): Boolean =
        prefs.getBoolean(KEY_A11Y_ALIVE, false)

    fun recordHeartbeat(
        nowMillis: Long,
        packageName: String?,
        reason: String
    ) {
        val pkg = packageName?.trim().orEmpty()
        val last = getHeartbeat()
        if (
            !AccessibilityHeartbeatLaw.shouldWrite(
                nowMillis = nowMillis,
                lastWriteMillis = last.lastEventMillis,
                packageName = pkg,
                lastPackageName = last.packageName,
                reason = reason,
                lastReason = last.reason
            )
        ) {
            return
        }
        prefs.edit()
            .putBoolean(KEY_A11Y_ALIVE, true)
            .putLong(KEY_HEARTBEAT_MS, nowMillis)
            .putString(KEY_HEARTBEAT_PKG, pkg)
            .putString(KEY_HEARTBEAT_REASON, reason)
            .apply()
    }

    fun getHeartbeat(): AccessibilityHeartbeat = AccessibilityHeartbeat(
        lastEventMillis = prefs.getLong(KEY_HEARTBEAT_MS, 0L),
        packageName = prefs.getString(KEY_HEARTBEAT_PKG, "") ?: "",
        reason = prefs.getString(KEY_HEARTBEAT_REASON, "") ?: "",
        serviceAlive = prefs.getBoolean(KEY_A11Y_ALIVE, false)
    )

    fun setOverlayActive(active: Boolean) {
        prefs.edit().putBoolean(KEY_OVERLAY_ACTIVE, active).apply()
    }

    fun isOverlayActive(): Boolean =
        prefs.getBoolean(KEY_OVERLAY_ACTIVE, false)

    companion object {
        private const val PREFS_NAME = "phonecodex_runtime_diag"
        private const val KEY_A11Y_ALIVE = "accessibilityServiceAlive"
        private const val KEY_OVERLAY_ACTIVE = "overlayActive"
        private const val KEY_HEARTBEAT_MS = "accessibilityLastEventMillis"
        private const val KEY_HEARTBEAT_PKG = "accessibilityLastEventPackage"
        private const val KEY_HEARTBEAT_REASON = "accessibilityLastEventReason"
    }
}
