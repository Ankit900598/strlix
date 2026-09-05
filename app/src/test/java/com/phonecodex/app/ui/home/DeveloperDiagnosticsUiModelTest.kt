package com.phonecodex.app.ui.home

import com.phonecodex.app.data.DebugState
import com.phonecodex.app.domain.diagnostics.BackendHealthProbe
import com.phonecodex.app.domain.diagnostics.BackendProbeResult
import org.junit.Assert.assertEquals
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
        assertEquals("none", model.sessionStatus)
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
        assertTrue(model.probeDetail!!.contains("ALLOW"))
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
