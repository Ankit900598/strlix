package com.phonecodex.app.data

import android.content.Context
import com.phonecodex.app.domain.model.StudyWorldSettings

class StudyWorldSettingsStore(context: Context) {

    private val prefs = context.applicationContext.getSharedPreferences(
        PREFS_NAME,
        Context.MODE_PRIVATE
    )

    fun getSettings(): StudyWorldSettings {
        return StudyWorldSettings(
            durationMinutes = prefs.getInt(
                KEY_DURATION_MINUTES,
                DEFAULT_DURATION_MINUTES
            ),
            lockAttemptThreshold = prefs.getInt(
                KEY_LOCK_ATTEMPT_THRESHOLD,
                DEFAULT_LOCK_ATTEMPT_THRESHOLD
            ),
            blockAttemptCooldownMinutes = prefs.getInt(
                KEY_BLOCK_ATTEMPT_COOLDOWN_MINUTES,
                DEFAULT_BLOCK_ATTEMPT_COOLDOWN_MINUTES
            )
        )
    }

    fun setDurationMinutes(minutes: Int) {
        prefs.edit()
            .putInt(KEY_DURATION_MINUTES, minutes)
            .apply()
    }

    fun setLockAttemptThreshold(threshold: Int) {
        prefs.edit()
            .putInt(KEY_LOCK_ATTEMPT_THRESHOLD, threshold)
            .apply()
    }

    fun setBlockAttemptCooldownMinutes(minutes: Int) {
        prefs.edit()
            .putInt(KEY_BLOCK_ATTEMPT_COOLDOWN_MINUTES, minutes)
            .apply()
    }

    companion object {
        private const val PREFS_NAME = "phonecodex_study_world_settings"
        private const val KEY_DURATION_MINUTES = "duration_minutes"
        private const val KEY_LOCK_ATTEMPT_THRESHOLD = "lock_attempt_threshold"
        private const val KEY_BLOCK_ATTEMPT_COOLDOWN_MINUTES = "block_attempt_cooldown_minutes"

        const val DEFAULT_DURATION_MINUTES = 30
        const val DEFAULT_LOCK_ATTEMPT_THRESHOLD = 10
        const val DEFAULT_BLOCK_ATTEMPT_COOLDOWN_MINUTES = 2
    }
}
