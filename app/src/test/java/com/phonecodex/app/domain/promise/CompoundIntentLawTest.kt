package com.phonecodex.app.domain.promise

import com.phonecodex.app.domain.model.FocusPromise
import com.phonecodex.app.domain.model.StrictnessLevel
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class CompoundIntentLawTest {

    @Test
    fun twoAllowOnlyAsks() {
        assertTrue(
            CompoundIntentLaw.needsClarification("allow only calculus, allow only 10 shorts")
        )
        val hit = CompoundIntentLaw.clarificationFor(
            "allow only this and second is allow only that"
        )
        assertEquals(3, hit!!.options.size)
        assertTrue(hit.options.first { it.id == "B" }.recommended)
    }

    @Test
    fun calculusThenMonkAsks() {
        assertTrue(
            CompoundIntentLaw.needsClarification("allow only calculus lecture, monk 4 hours")
        )
    }

    @Test
    fun quotaPlusAdultComposes() {
        assertFalse(
            CompoundIntentLaw.needsClarification(
                "I want to watch at most 10 shorts today, but never adult shorts"
            )
        )
    }

    @Test
    fun shotsQuotaDoesNotLookLikeTwoWorlds() {
        assertFalse(
            CompoundIntentLaw.needsClarification("allow me upto 20 shots then block")
        )
    }

    @Test
    fun pickFirstUsesFirstClause() {
        assertEquals(
            "allow only calculus lecture",
            CompoundIntentLaw.effectivePromiseText(
                "allow only calculus lecture, monk 4 hours",
                "B"
            )
        )
    }

    @Test
    fun injectLocksUntilPick() {
        val draft = FocusPromise(
            rawText = "allow only calculus, allow only monk",
            sessionDurationMinutes = 240,
            allowedKeywords = emptyList(),
            blockedKeywords = emptyList(),
            strictness = StrictnessLevel.STRICT,
            suggestedAppRules = emptyList()
        )
        val locked = PromiseClarificationLaw.apply(draft)
        assertTrue(locked.clarificationRequired)
        assertEquals(false, locked.canStartCommitment)
        assertEquals(3, locked.clarificationOptions.size)

        val picked = PromiseClarificationLaw.apply(draft, "A")
        assertFalse(picked.clarificationRequired)
        assertEquals(true, picked.canStartCommitment)
    }
}
