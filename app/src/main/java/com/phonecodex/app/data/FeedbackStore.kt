package com.phonecodex.app.data

import android.content.Context
import com.phonecodex.app.domain.model.FeedbackEntry

class FeedbackStore(context: Context) {

    private val prefs = context.applicationContext.getSharedPreferences(
        PREFS_NAME,
        Context.MODE_PRIVATE
    )

    fun addFeedback(entry: FeedbackEntry) {
        val encoded = encode(entry)
        val updated = (listOf(encoded) + getRawEntries()).take(MAX_ENTRIES)
        prefs.edit()
            .putString(KEY_ENTRIES, updated.joinToString("\n"))
            .apply()
    }

    fun getRecentFeedback(): List<FeedbackEntry> {
        return getRawEntries()
            .mapNotNull { decode(it) }
    }

    fun getFeedbackCount(): Int {
        return getRawEntries().size
    }

    private fun getRawEntries(): List<String> {
        val stored = prefs.getString(KEY_ENTRIES, null) ?: return emptyList()
        return stored
            .lineSequence()
            .map { it.trim() }
            .filter { it.isNotEmpty() }
            .toList()
    }

    private fun encode(entry: FeedbackEntry): String {
        return listOf(
            entry.timestampMillis.toString(),
            entry.packageName,
            entry.screenTextPreview,
            entry.originalDecision,
            entry.correctedDecision,
            entry.reason
        ).joinToString(FIELD_SEPARATOR) { sanitizeField(it) }
    }

    private fun decode(raw: String): FeedbackEntry? {
        val parts = raw.split(FIELD_SEPARATOR)
        if (parts.size < 6) return null

        val timestampMillis = parts[0].toLongOrNull() ?: return null
        return FeedbackEntry(
            timestampMillis = timestampMillis,
            packageName = parts[1],
            screenTextPreview = parts[2],
            originalDecision = parts[3],
            correctedDecision = parts[4],
            reason = parts.drop(5).joinToString(FIELD_SEPARATOR)
        )
    }

    private fun sanitizeField(value: String): String {
        return value
            .replace(FIELD_SEPARATOR, " ")
            .replace('\n', ' ')
            .trim()
    }

    companion object {
        private const val PREFS_NAME = "phonecodex_feedback"
        private const val KEY_ENTRIES = "entries"
        private const val MAX_ENTRIES = 50
        private const val FIELD_SEPARATOR = "\u001E"
    }
}
