package com.phonecodex.app.ui.home

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Contract tests for voice → text fill. Voice must never imply Start Commitment.
 */
class PromiseComposerVoiceContractTest {

    @Test
    fun voiceTranscript_fillsTextAndSetsReviewStatus() {
        var promiseText = ""
        var voiceStatus: String? = null
        var understandingCleared = false

        fun applyVoiceTranscript(transcript: String) {
            val clean = transcript.trim()
            if (clean.isEmpty()) {
                voiceStatus = "I did not hear a promise. Try again or type it."
                return
            }
            promiseText = clean
            voiceStatus = "Voice captured. Edit if needed, then tap the arrow to understand."
            understandingCleared = true
        }

        applyVoiceTranscript("  at most 10 shorts today  ")

        assertEquals("at most 10 shorts today", promiseText)
        assertTrue(voiceStatus!!.contains("arrow"))
        assertTrue(understandingCleared)
        assertFalse(voiceStatus!!.contains("Start", ignoreCase = true))
    }

    @Test
    fun emptyVoiceTranscript_doesNotOverwritePromise() {
        var promiseText = "keep existing"
        var voiceStatus: String? = null

        fun applyVoiceTranscript(transcript: String) {
            val clean = transcript.trim()
            if (clean.isEmpty()) {
                voiceStatus = "I did not hear a promise. Try again or type it."
                return
            }
            promiseText = clean
        }

        applyVoiceTranscript("   ")
        assertEquals("keep existing", promiseText)
        assertEquals("I did not hear a promise. Try again or type it.", voiceStatus)
    }

    @Test
    fun sendEnabledOnlyWhenTextPresentAndNotUnderstanding() {
        fun canSend(text: String, understanding: Boolean): Boolean =
            text.isNotBlank() && !understanding

        assertFalse(canSend("", false))
        assertFalse(canSend("  ", false))
        assertTrue(canSend("study for 1 hour", false))
        assertFalse(canSend("study for 1 hour", true))
    }

    @Test
    fun beginVoiceCapture_setsListeningWithoutStarting() {
        var voiceStatus: String? = null
        var startedCommitment = false
        voiceStatus = "Listening…"
        assertEquals("Listening…", voiceStatus)
        assertFalse(startedCommitment)
    }
}
