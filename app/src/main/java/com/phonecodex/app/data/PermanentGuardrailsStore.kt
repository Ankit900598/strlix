package com.phonecodex.app.data

import android.content.Context
import com.phonecodex.app.domain.model.PermanentGuardrail

class PermanentGuardrailsStore(context: Context) {

    private val prefs = context.applicationContext.getSharedPreferences(
        PREFS_NAME,
        Context.MODE_PRIVATE
    )

    fun getGuardrails(): List<PermanentGuardrail> {
        return listOf(loadPornGuardrail())
    }

    fun getEnabledGuardrails(): List<PermanentGuardrail> {
        val now = System.currentTimeMillis()
        return getGuardrails()
            .filter { guardrail -> guardrail.enabled && !isExpired(guardrail, now) }
    }

    fun setGuardrailEnabled(id: String, enabled: Boolean) {
        when (id) {
            PORN_GUARDRAIL_ID -> {
                prefs.edit()
                    .putBoolean(KEY_PORN_GUARDRAIL_ENABLED, enabled)
                    .apply()
            }
        }
    }

    private fun loadPornGuardrail(): PermanentGuardrail {
        return DEFAULT_PORN_GUARDRAIL.copy(
            enabled = prefs.getBoolean(KEY_PORN_GUARDRAIL_ENABLED, true)
        )
    }

    private fun isExpired(guardrail: PermanentGuardrail, nowMillis: Long): Boolean {
        val expiresAt = guardrail.expiresAtMillis ?: return false
        return nowMillis >= expiresAt
    }

    companion object {
        private const val PREFS_NAME = "phonecodex_permanent_guardrails"
        private const val KEY_PORN_GUARDRAIL_ENABLED = "porn_guardrail_enabled"
        const val PORN_GUARDRAIL_ID = "porn_guardrail"

        private val DEFAULT_PORN_GUARDRAIL = PermanentGuardrail(
            id = PORN_GUARDRAIL_ID,
            name = "Block Porn",
            enabled = true,
            blockedKeywords = setOf(
                "porn",
                "xxx",
                "pornhub",
                "xvideos",
                "xhamster",
                "onlyfans",
                "redtube",
                "xnxx",
                "sex",
                "nude",
                "adult",
                "hot",
                "bikini"
            ),
            blockedPackages = emptySet(),
            createdAtMillis = 0L,
            expiresAtMillis = null
        )
    }
}
