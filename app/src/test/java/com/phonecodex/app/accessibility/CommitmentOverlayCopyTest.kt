package com.phonecodex.app.accessibility

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class CommitmentOverlayCopyTest {

    @Test
    fun overlayKind_mapsDecisions() {
        assertEquals(OverlayKind.WARN, CommitmentOverlayCopy.overlayKind("WARN"))
        assertEquals(OverlayKind.WARN, CommitmentOverlayCopy.overlayKind("ASK"))
        assertEquals(OverlayKind.BLOCK, CommitmentOverlayCopy.overlayKind("BLOCK"))
        assertEquals(OverlayKind.LOCK, CommitmentOverlayCopy.overlayKind("LOCK"))
        assertEquals(OverlayKind.BLOCK, CommitmentOverlayCopy.overlayKind("ALLOW"))
    }

    @Test
    fun shortReason_prefersClassifierReason() {
        assertEquals(
            "Shorts will pull you off lecture mode.",
            CommitmentOverlayCopy.shortReason("BLOCK", "Shorts will pull you off lecture mode.")
        )
    }

    @Test
    fun shortReason_fallsBackByKind() {
        assertEquals(
            "This doesn’t match your current commitment.",
            CommitmentOverlayCopy.shortReason("BLOCK", "  ")
        )
        assertEquals(
            "This might pull you off your commitment.",
            CommitmentOverlayCopy.shortReason("WARN", "")
        )
    }

    @Test
    fun attemptLabel_hidesZero() {
        assertNull(CommitmentOverlayCopy.attemptLabel(null))
        assertNull(CommitmentOverlayCopy.attemptLabel(0))
        assertEquals("1 drift so far", CommitmentOverlayCopy.attemptLabel(1))
        assertEquals("3 drifts so far", CommitmentOverlayCopy.attemptLabel(3))
    }

    @Test
    fun remainingLabel_lockPrefix() {
        assertEquals(
            "12m left",
            CommitmentOverlayCopy.remainingLabel(OverlayKind.BLOCK, 12 * 60_000L)
        )
        assertEquals(
            "Lock holds · 12m left",
            CommitmentOverlayCopy.remainingLabel(OverlayKind.LOCK, 12 * 60_000L)
        )
        assertNull(CommitmentOverlayCopy.remainingLabel(OverlayKind.WARN, 0L))
    }

    @Test
    fun headline_warnSaysStayOnPromise() {
        assertEquals("Stay on promise", CommitmentOverlayCopy.headline(OverlayKind.WARN))
    }
}
