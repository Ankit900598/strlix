package com.phonecodex.app.ui.home

import androidx.compose.runtime.Immutable
import com.phonecodex.app.data.DebugState
import com.phonecodex.app.domain.diagnostics.BackendHealthProbe
import com.phonecodex.app.domain.diagnostics.BackendProbeKind
import com.phonecodex.app.domain.diagnostics.BackendProbeResult
import com.phonecodex.app.domain.enforcement.SessionEnforcementCopy
import com.phonecodex.app.domain.enforcement.VisionExperiment
import com.phonecodex.app.domain.model.FocusSession
import com.phonecodex.app.domain.model.SessionStatus

/**
 * Snapshot for the Advanced Controls developer diagnostics card.
 * Built in [HomeScreenState] — never from prefs reads inside composables.
 *
 * [probeResult] must already be display-resolved (sticky / checking / bridge hint).
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
    val testInProgress: Boolean,
    val probeKind: BackendProbeKind,
    val noActiveCommitmentWarning: String? = null,
    val visionExperimentEnabled: Boolean = false,
    val visionExperimentCopy: String = VISION_EXPERIMENT_COPY,
    val visionExperimentWindowOpen: Boolean = false
)

internal fun buildDeveloperDiagnosticsUiModel(
    isAccessibilityEnabled: Boolean,
    isAccessibilityAlive: Boolean,
    session: FocusSession?,
    overlayActive: Boolean,
    debugState: DebugState,
    probeResult: BackendProbeResult,
    testInProgress: Boolean,
    visionExperimentEnabled: Boolean = false,
    nowEpochMs: Long = System.currentTimeMillis()
): DeveloperDiagnosticsUiModel {
    // Prefer explicit probe display; never invent scary "offline" when never tested.
    val statusLine = when {
        !isAccessibilityEnabled -> BackendHealthProbe.STATUS_A11Y_OFF
        testInProgress || probeResult.kind == BackendProbeKind.CHECKING ->
            probeResult.statusLine.ifBlank { BackendHealthProbe.STATUS_CHECKING }
        probeResult.kind != BackendProbeKind.IDLE -> probeResult.statusLine
        debugState.lastBackendProvider != null -> BackendHealthProbe.STATUS_CONNECTED
        else -> BackendHealthProbe.STATUS_IDLE
    }

    val backendReachable = when (probeResult.kind) {
        BackendProbeKind.REACHABLE,
        BackendProbeKind.STALE_OK -> true
        BackendProbeKind.CHECKING -> probeResult.reachable
        BackendProbeKind.IDLE -> debugState.lastBackendProvider != null
        BackendProbeKind.UNREACHABLE,
        BackendProbeKind.BRIDGE_MISSING -> false
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

    val hasActiveSession =
        session?.status == SessionStatus.ACTIVE || session?.status == SessionStatus.LOCKED
    val sessionStatus = SessionEnforcementCopy.diagnosticsSessionStatus(
        hasActiveSession = hasActiveSession,
        sessionStatusName = session?.status?.name
    )
    val noActiveCommitmentWarning =
        if (SessionEnforcementCopy.shouldShowNoActiveCommitmentWarning(hasActiveSession)) {
            SessionEnforcementCopy.NO_ACTIVE_COMMITMENT
        } else {
            null
        }

    val probeDetail = when {
        testInProgress -> "Running /health + /classify smoke…"
        probeResult.kind == BackendProbeKind.BRIDGE_MISSING ->
            probeResult.detail ?: BackendHealthProbe.HINT_ADB_REVERSE
        probeResult.kind == BackendProbeKind.STALE_OK ->
            probeResult.detail
        probeResult.classifyOk == true ->
            "Smoke classify: ${probeResult.classifyDecision}" +
                (probeResult.classifyReasonCategory?.let { " ($it)" } ?: "")
        probeResult.classifyOk == false ->
            "Smoke classify failed${probeResult.detail?.let { ": $it" } ?: ""}"
        probeResult.detail != null &&
            (probeResult.kind == BackendProbeKind.UNREACHABLE || !probeResult.reachable) ->
            probeResult.detail
        else -> null
    }

    val probeKind = when {
        !isAccessibilityEnabled -> probeResult.kind
        testInProgress -> BackendProbeKind.CHECKING
        probeResult.kind != BackendProbeKind.IDLE -> probeResult.kind
        debugState.lastBackendProvider != null -> BackendProbeKind.REACHABLE
        else -> BackendProbeKind.IDLE
    }

    return DeveloperDiagnosticsUiModel(
        statusLine = statusLine,
        backendReachableLabel = when (probeKind) {
            BackendProbeKind.STALE_OK -> "yes (stale)"
            BackendProbeKind.CHECKING -> "checking"
            BackendProbeKind.BRIDGE_MISSING -> "no (bridge?)"
            BackendProbeKind.REACHABLE -> "yes"
            BackendProbeKind.UNREACHABLE -> "no"
            BackendProbeKind.IDLE -> if (backendReachable) "yes" else "not tested"
        },
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
        testInProgress = testInProgress,
        probeKind = probeKind,
        noActiveCommitmentWarning = noActiveCommitmentWarning,
        visionExperimentEnabled = visionExperimentEnabled,
        visionExperimentCopy = VISION_EXPERIMENT_COPY,
        visionExperimentWindowOpen = VisionExperiment.isCalendarWindowOpen(nowEpochMs)
    )
}

internal const val VISION_EXPERIMENT_COPY =
    "10-day vision experiment (credits). Local law still wins. Off after ${VisionExperiment.KILL_DATE_LABEL}."
