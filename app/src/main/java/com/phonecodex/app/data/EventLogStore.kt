package com.phonecodex.app.data

import android.content.Context

class EventLogStore(context: Context) {

    private val prefs = context.applicationContext.getSharedPreferences(
        PREFS_NAME,
        Context.MODE_PRIVATE
    )

    fun addEvent(message: String) {
        val entry = "${System.currentTimeMillis()}|$message"
        val updated = (listOf(entry) + getRawEvents()).take(MAX_EVENTS)
        prefs.edit()
            .putString(KEY_EVENTS, updated.joinToString("\n"))
            .apply()
    }

    fun getRecentEvents(): List<String> {
        return getRawEvents().map { raw ->
            val separator = raw.indexOf('|')
            if (separator <= 0) {
                raw
            } else {
                val timestamp = raw.substring(0, separator)
                val message = raw.substring(separator + 1)
                "$timestamp: $message"
            }
        }
    }

    private fun getRawEvents(): List<String> {
        val stored = prefs.getString(KEY_EVENTS, null) ?: return emptyList()
        return stored
            .lineSequence()
            .map { it.trim() }
            .filter { it.isNotEmpty() }
            .toList()
    }

    companion object {
        private const val PREFS_NAME = "phonecodex_event_log"
        private const val KEY_EVENTS = "events"
        private const val MAX_EVENTS = 20
    }
}
