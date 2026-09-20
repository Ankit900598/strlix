package com.phonecodex.app.data

import android.content.Context
import com.phonecodex.app.domain.enforcement.ShortFormQuotaGate

class ShortFormQuotaStore(context: Context) : ShortFormQuotaGate.Ledger {

    private val prefs = context.applicationContext.getSharedPreferences(
        PREFS_NAME,
        Context.MODE_PRIVATE
    )

    override fun load(dayKey: String): Pair<Int, Set<String>> {
        val count = prefs.getInt(countKey(dayKey), 0)
        val raw = prefs.getString(sigKey(dayKey), "").orEmpty()
        val signatures = if (raw.isBlank()) {
            emptySet()
        } else {
            raw.split('\u001E').map { it.trim() }.filter { it.isNotEmpty() }.toSet()
        }
        return count to signatures
    }

    override fun save(dayKey: String, count: Int, signatures: Set<String>) {
        prefs.edit()
            .putInt(countKey(dayKey), count)
            .putString(sigKey(dayKey), signatures.joinToString("\u001E"))
            .apply()
    }

    private fun countKey(dayKey: String) = "count.$dayKey"

    private fun sigKey(dayKey: String) = "sig.$dayKey"

    companion object {
        private const val PREFS_NAME = "phonecodex_short_form_quota"
    }
}
