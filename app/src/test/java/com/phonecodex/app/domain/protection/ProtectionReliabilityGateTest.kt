package com.phonecodex.app.domain.protection

import com.phonecodex.app.domain.diagnostics.BackendProbeKind
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ProtectionReliabilityGateTest {

    private val now = 1_000_000L

    @Test
    fun accessibilityOff_needsSetup_andDeepLinks() {
        val model = ProtectionReliabilityGate.evaluate(
            input(
                accessibilityEnabled = false,
                accessibilityAlive = false,
                lastEventMillis = 0L
            )
        )
        assertEquals(ProtectionReliabilityLevel.NEEDS_SETUP, model.level)
        assertEquals(ProtectionReliabilityGate.HEADLINE_NEEDS_SETUP, model.headline)
        assertEquals("Off", model.accessibilityLine)
        assertEquals(ProtectionPrimaryAction.OPEN_ACCESSIBILITY, model.primaryAction)
        assertEquals(ProtectionReliabilityGate.ACTION_TURN_ON, model.primaryActionLabel)
        assertFalse(model.nothingEnforced)
    }

    @Test
    fun enabledButDeadAndStale_notProtecting() {
        val model = ProtectionReliabilityGate.evaluate(
            input(
                accessibilityEnabled = true,
                accessibilityAlive = false,
                lastEventMillis = now - 60_000L,
                hasActiveCommitment = true
            )
        )
        assertEquals(ProtectionReliabilityLevel.NOT_PROTECTING, model.level)
        assertEquals("Enabled but not alive", model.accessibilityLine)
        assertEquals(ProtectionPrimaryAction.OPEN_ACCESSIBILITY, model.primaryAction)
    }

    @Test
    fun enabledDeadButFreshHeartbeat_countsAsAlive() {
        val model = ProtectionReliabilityGate.evaluate(
            input(
                accessibilityEnabled = true,
                accessibilityAlive = false,
                lastEventMillis = now - 5_000L,
                hasActiveCommitment = true
            )
        )
        assertEquals(ProtectionReliabilityLevel.PROTECTED, model.level)
        assertEquals("Alive", model.accessibilityLine)
        assertEquals(ProtectionPrimaryAction.NONE, model.primaryAction)
        assertNull(model.primaryActionLabel)
        assertEquals("last phone event 5s ago", model.lastEventLine)
    }

    @Test
    fun loopAliveWithNoLaw_nothingIsEnforced() {
        val model = ProtectionReliabilityGate.evaluate(
            input(
                accessibilityEnabled = true,
                accessibilityAlive = true,
                lastEventMillis = now - 2_000L
            )
        )
        assertEquals(ProtectionReliabilityLevel.NOT_PROTECTING, model.level)
        assertTrue(model.nothingEnforced)
        assertTrue(model.summary.contains(ProtectionReliabilityGate.NOTHING_ENFORCED))
        assertEquals("None", model.commitmentLine)
        assertEquals("Off", model.guardrailLine)
        assertEquals(ProtectionPrimaryAction.NONE, model.primaryAction)
    }

    @Test
    fun activeCommitment_protectedEvenIfBackendMissing() {
        val model = ProtectionReliabilityGate.evaluate(
            input(
                accessibilityEnabled = true,
                accessibilityAlive = true,
                lastEventMillis = now - 1_000L,
                hasActiveCommitment = true,
                backendKind = BackendProbeKind.BRIDGE_MISSING,
                backendLoopback = true
            )
        )
        assertEquals(ProtectionReliabilityLevel.PROTECTED, model.level)
        assertTrue(model.isProtected)
        assertEquals("Bridge missing", model.backendLine)
        assertTrue(model.showAdbReverseHint)
        assertEquals(ProtectionReliabilityGate.ADB_REVERSE, model.adbReverseHint)
        assertEquals("adb reverse tcp:8787 tcp:8787", model.adbReverseHint)
    }

    @Test
    fun guardrailOnly_protected() {
        val model = ProtectionReliabilityGate.evaluate(
            input(
                accessibilityEnabled = true,
                accessibilityAlive = true,
                lastEventMillis = now - 1_000L,
                permanentGuardrailOn = true
            )
        )
        assertEquals(ProtectionReliabilityLevel.PROTECTED, model.level)
        assertEquals("On", model.guardrailLine)
        assertFalse(model.nothingEnforced)
    }

    @Test
    fun hostedBackendMissing_doesNotShowAdbReverse() {
        val model = ProtectionReliabilityGate.evaluate(
            input(
                accessibilityEnabled = true,
                accessibilityAlive = true,
                lastEventMillis = now - 1_000L,
                hasActiveCommitment = true,
                backendKind = BackendProbeKind.BRIDGE_MISSING,
                backendLoopback = false
            )
        )
        assertFalse(model.showAdbReverseHint)
        assertEquals("", model.adbReverseHint)
    }

    @Test
    fun checkLogLine_isReadableAndDoesNotStartAPromise() {
        val model = ProtectionReliabilityGate.evaluate(
            input(
                accessibilityEnabled = true,
                accessibilityAlive = true,
                lastEventMillis = now - 8_000L,
                hasActiveCommitment = true,
                backendKind = BackendProbeKind.REACHABLE
            )
        )
        assertTrue(model.checkLogLine.startsWith("Protected"))
        assertTrue(model.checkLogLine.contains("a11y=Alive"))
        assertTrue(model.checkLogLine.contains("commitment=Active"))
        assertTrue(model.checkLogLine.contains("guardrail=Off"))
        assertTrue(model.checkLogLine.contains("backend=Reachable"))
        assertTrue(model.checkLogLine.contains("last phone event 8s ago"))
        assertFalse(model.checkLogLine.contains("Start"))
    }

    private fun input(
        accessibilityEnabled: Boolean,
        accessibilityAlive: Boolean,
        lastEventMillis: Long,
        hasActiveCommitment: Boolean = false,
        permanentGuardrailOn: Boolean = false,
        backendKind: BackendProbeKind = BackendProbeKind.IDLE,
        backendLoopback: Boolean = true
    ): ProtectionReliabilityInput = ProtectionReliabilityInput(
        accessibilityEnabled = accessibilityEnabled,
        accessibilityAlive = accessibilityAlive,
        lastEventMillis = lastEventMillis,
        lastEventPackage = "com.android.chrome",
        lastEventReason = AccessibilityHeartbeatLaw.REASON_WINDOW_CHANGED,
        hasActiveCommitment = hasActiveCommitment,
        permanentGuardrailOn = permanentGuardrailOn,
        backendKind = backendKind,
        backendLoopback = backendLoopback,
        nowMillis = now
    )
}
