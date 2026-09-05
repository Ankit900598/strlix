package com.phonecodex.app.ui.home

import androidx.compose.runtime.Immutable
import com.phonecodex.app.data.DebugState
import com.phonecodex.app.domain.diagnostics.BackendHealthProbe
import com.phonecodex.app.domain.diagnostics.BackendProbeResult
import com.phonecodex.app.domain.model.FocusSession

/**
 * Snapshot for the Advanced Controls developer diagnostics card.
 * Built in [HomeScreenState] — never from prefs reads inside composables.
 */
@Immutable
internal data class DeveloperDiagnosticsUiModel(
    val statusLine: String,
    val backendReachableLabel: String,
    val provider: String,
    val deployment: String,
    val promptVersion: String,
    val lastClassificationTimestamp: String,
    val lastPackage: String,
    val lastDecision: String,
    val lastReason: String,
    val lastReasonCategory: String,
    val lastBackendLatency: String,
    val accessibilityLabel: String,
    val sessionStatus: String,
    val overlayActiveLabel: String,
    val probeDetail: String?,
    val testInProgress: Boolean
)

internal fun buildDeveloperDiagnosticsUiModel(
    isAccessibilityEnabled: Boolean,
    isAccessibilityAlive: Boolean,
    session: FocusSession?,
    overlayActive: Boolean,
    debugState: DebugState,
    probeResult: BackendProbeResult,
    testInProgress: Boolean
): DeveloperDiagnosticsUiModel {
    val statusLine = when {
        !isAccessibilityEnabled -> BackendHealthProbe.STATUS_A11Y_OFF
        probeResult.statusLine != "Not tested yet" -> probeResult.statusLine
        debugState.lastBackendProvider != null -> BackendHealthProbe.STATUS_CONNECTED
        else -> BackendHealthProbe.STATUS_OFFLINE
    }

    val backendReachable = when {
        probeResult.statusLine != "Not tested yet" -> probeResult.reachable
        debugState.lastBackendProvider != null -> true
        else -> false
    }

    val provider = probeResult.provider
        ?: debugState.lastBackendProvider
        ?: "—"
    val deployment = probeResult.deployment
        ?: debugState.lastBackendDeployment
        ?: "—"
    val promptVersion = probeResult.promptVersion
        ?: debugState.lastBackendPromptVersion
        ?: "—"

    val accessibilityLabel = when {
        !isAccessibilityEnabled -> "off"
        isAccessibilityAlive -> "enabled · alive"
        else -> "enabled · not alive (stale or killed)"
    }

    val sessionStatus = session?.status?.name ?: "none"

    val probeDetail = when {
        testInProgress -> "Running /health + /classify smoke…"
        probeResult.classifyOk == true ->
            "Smoke classify: ${probeResult.classifyDecision}" +
                (probeResult.classifyReasonCategory?.let { " ($it)" } ?: "")
        probeResult.classifyOk == false ->
            "Smoke classify failed${probeResult.detail?.let { ": $it" } ?: ""}"
        probeResult.detail != null && !probeResult.reachable ->
            probeResult.detail
        else -> null
    }

    return DeveloperDiagnosticsUiModel(
        statusLine = statusLine,
        backendReachableLabel = if (backendReachable) "yes" else "no",
        provider = provider,
        deployment = deployment,
        promptVersion = promptVersion,
        lastClassificationTimestamp = formatDebugTimestamp(debugState.lastUpdatedMillis),
        lastPackage = debugState.lastPackageName?.ifBlank { null } ?: "—",
        lastDecision = debugState.lastDecision?.ifBlank { null } ?: "—",
        lastReason = debugState.lastReason?.ifBlank { null } ?: "—",
        lastReasonCategory = debugState.lastReasonCategory?.ifBlank { null } ?: "—",
        lastBackendLatency = debugState.lastBackendLatencyMs?.let { "${it} ms" } ?: "—",
        accessibilityLabel = accessibilityLabel,
        sessionStatus = sessionStatus,
        overlayActiveLabel = if (overlayActive) "yes" else "no",
        probeDetail = probeDetail,
        testInProgress = testInProgress
    )
}
