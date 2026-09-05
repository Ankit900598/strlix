package com.phonecodex.app.data

import android.content.Context

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

    fun setOverlayActive(active: Boolean) {
        prefs.edit().putBoolean(KEY_OVERLAY_ACTIVE, active).apply()
    }

    fun isOverlayActive(): Boolean =
        prefs.getBoolean(KEY_OVERLAY_ACTIVE, false)

    companion object {
        private const val PREFS_NAME = "phonecodex_runtime_diag"
        private const val KEY_A11Y_ALIVE = "accessibilityServiceAlive"
        private const val KEY_OVERLAY_ACTIVE = "overlayActive"
    }
}
