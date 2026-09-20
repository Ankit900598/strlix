package com.phonecodex.app.ui.home

import com.phonecodex.app.data.DebugState
import com.phonecodex.app.domain.diagnostics.BackendHealthProbe
import com.phonecodex.app.domain.enforcement.VisionExperiment
import com.phonecodex.app.domain.diagnostics.BackendProbeKind
import com.phonecodex.app.domain.diagnostics.BackendProbeResult
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class DeveloperDiagnosticsUiModelTest {

    @Test
    fun build_whenAccessibilityOff_usesProtectionCannotWorkStatus() {
        val model = buildDeveloperDiagnosticsUiModel(
            isAccessibilityEnabled = false,
            isAccessibilityAlive = false,
            session = null,
            overlayActive = false,
            debugState = emptyDebug(),
            probeResult = BackendProbeResult.idle(),
            testInProgress = false
        )

        assertEquals(BackendHealthProbe.STATUS_A11Y_OFF, model.statusLine)
        assertEquals("off", model.accessibilityLabel)
        assertEquals("no", model.overlayActiveLabel)
        assertTrue(model.sessionStatus.contains("none"))
        assertTrue(
            model.sessionStatus.contains(
                com.phonecodex.app.domain.enforcement.SessionEnforcementCopy.NO_ACTIVE_COMMITMENT
            )
        )
        assertEquals(
            com.phonecodex.app.domain.enforcement.SessionEnforcementCopy.NO_ACTIVE_COMMITMENT,
            model.noActiveCommitmentWarning
        )
    }

    @Test
    fun build_whenNeverProbed_doesNotSayOffline() {
        val model = buildDeveloperDiagnosticsUiModel(
            isAccessibilityEnabled = true,
            isAccessibilityAlive = true,
            session = null,
            overlayActive = false,
            debugState = emptyDebug(),
            probeResult = BackendProbeResult.idle(),
            testInProgress = false
        )

        assertEquals(BackendHealthProbe.STATUS_IDLE, model.statusLine)
        assertFalse(model.statusLine.contains("offline", ignoreCase = true))
        assertEquals("not tested", model.backendReachableLabel)
        assertEquals(BackendProbeKind.IDLE, model.probeKind)
        assertTrue(model.visionExperimentCopy.contains("10-day vision experiment"))
        assertFalse(model.visionExperimentEnabled)
    }

    @Test
    fun build_whenProbeConnected_showsBackendConnected() {
        val model = buildDeveloperDiagnosticsUiModel(
            isAccessibilityEnabled = true,
            isAccessibilityAlive = true,
            session = null,
            overlayActive = true,
            debugState = emptyDebug(),
            probeResult = BackendProbeResult(
                kind = BackendProbeKind.REACHABLE,
                reachable = true,
                statusLine = BackendHealthProbe.STATUS_CONNECTED,
                provider = "azure",
                deployment = "pc-lab-cheap",
                promptVersion = "v04",
                classifyOk = true,
                classifyDecision = "ALLOW",
                classifyReasonCategory = "safe",
                latencyMs = 120L,
                detail = null
            ),
            testInProgress = false
        )

        assertEquals(BackendHealthProbe.STATUS_CONNECTED, model.statusLine)
        assertEquals("yes", model.backendReachableLabel)
        assertEquals("azure", model.provider)
        assertEquals("pc-lab-cheap", model.deployment)
        assertEquals("v04", model.promptVersion)
        assertEquals("yes", model.overlayActiveLabel)
        assertEquals(BackendProbeKind.REACHABLE, model.probeKind)
        assertTrue(model.probeDetail!!.contains("ALLOW"))
    }

    @Test
    fun build_whenBridgeMissing_showsAdbHint() {
        val model = buildDeveloperDiagnosticsUiModel(
            isAccessibilityEnabled = true,
            isAccessibilityAlive = true,
            session = null,
            overlayActive = false,
            debugState = emptyDebug(),
            probeResult = BackendProbeResult.failure(
                kind = BackendProbeKind.BRIDGE_MISSING,
                latencyMs = 8L,
                detail = "Connection refused"
            ),
            testInProgress = false
        )

        assertEquals(BackendHealthProbe.STATUS_BRIDGE_MISSING, model.statusLine)
        assertEquals("no (bridge?)", model.backendReachableLabel)
        assertEquals(BackendProbeKind.BRIDGE_MISSING, model.probeKind)
        assertTrue(model.probeDetail!!.contains(BackendHealthProbe.reachabilityHint()))
    }

    @Test
    fun build_whenStaleOk_doesNotLookOffline() {
        val model = buildDeveloperDiagnosticsUiModel(
            isAccessibilityEnabled = true,
            isAccessibilityAlive = true,
            session = null,
            overlayActive = false,
            debugState = emptyDebug(),
            probeResult = BackendProbeResult(
                kind = BackendProbeKind.STALE_OK,
                reachable = true,
                statusLine = BackendHealthProbe.STATUS_STALE,
                provider = "azure",
                deployment = "pc-lab-cheap",
                promptVersion = "v04",
                classifyOk = true,
                classifyDecision = "ALLOW",
                classifyReasonCategory = "safe",
                latencyMs = 40L,
                detail = BackendHealthProbe.HINT_ADB_REVERSE
            ),
            testInProgress = false
        )

        assertEquals(BackendHealthProbe.STATUS_STALE, model.statusLine)
        assertEquals("yes (stale)", model.backendReachableLabel)
        assertFalse(model.statusLine.contains("offline", ignoreCase = true))
        assertEquals(BackendProbeKind.STALE_OK, model.probeKind)
    }

    @Test
    fun build_visionWindowClosedAfterKillDate() {
        val model = buildDeveloperDiagnosticsUiModel(
            isAccessibilityEnabled = true,
            isAccessibilityAlive = true,
            session = null,
            overlayActive = false,
            debugState = emptyDebug(),
            probeResult = BackendProbeResult.idle(),
            testInProgress = false,
            visionExperimentEnabled = true,
            nowEpochMs = VisionExperiment.END_EPOCH_MS
        )
        assertFalse(model.visionExperimentWindowOpen)
        assertTrue(model.visionExperimentEnabled)
        assertTrue(model.visionExperimentCopy.contains(VisionExperiment.KILL_DATE_LABEL))
    }

    private fun emptyDebug(): DebugState = DebugState(
        lastPackageName = null,
        lastScreenTextPreview = null,
        lastDecision = null,
        lastReason = null,
        lastSource = null,
        lastConfidence = null,
        lastMatchedSignals = emptyList(),
        lastUpdatedMillis = 0L,
        lastReasonCategory = null,
        lastWouldEscalate = null,
        lastBackendProvider = null,
        lastBackendDeployment = null,
        lastBackendPromptVersion = null,
        lastBackendLatencyMs = null
    )
}
