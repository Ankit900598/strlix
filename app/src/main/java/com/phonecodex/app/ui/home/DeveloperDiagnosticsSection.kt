package com.phonecodex.app.ui.home

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.width
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.phonecodex.app.domain.diagnostics.BackendProbeKind
import com.phonecodex.app.domain.enforcement.VisionExperiment

/**
 * Developer-only layer diagnostics under Advanced Controls.
 * Identifies which layer is broken without dumping noise on the main home screen.
 */
@Composable
internal fun DeveloperDiagnosticsSection(
    model: DeveloperDiagnosticsUiModel,
    onTestBackend: () -> Unit,
    onRefresh: () -> Unit,
    onVisionExperimentChange: (Boolean) -> Unit = {}
) {
    MicroLabel(text = "Developer diagnostics")
    Spacer(modifier = Modifier.height(6.dp))
    Text(
        text = "Layer health for phone tests. Not shown on the main home screen.",
        style = MaterialTheme.typography.bodySmall,
        color = MaterialTheme.colorScheme.onSurfaceVariant
    )
    Spacer(modifier = Modifier.height(12.dp))
    Text(
        text = model.statusLine,
        style = MaterialTheme.typography.bodyMedium,
        color = if (
            model.statusLine.contains("cannot work", ignoreCase = true) ||
            model.probeKind == BackendProbeKind.UNREACHABLE ||
            model.probeKind == BackendProbeKind.BRIDGE_MISSING
        ) {
            MaterialTheme.colorScheme.error
        } else {
            MaterialTheme.colorScheme.onSurface
        }
    )
    Spacer(modifier = Modifier.height(14.dp))

    SummaryRow(label = "Backend reachable", value = model.backendReachableLabel)
    Spacer(modifier = Modifier.height(8.dp))
    SummaryRow(label = "Provider", value = model.provider)
    Spacer(modifier = Modifier.height(8.dp))
    SummaryRow(label = "Deployment", value = model.deployment)
    Spacer(modifier = Modifier.height(8.dp))
    SummaryRow(label = "Prompt version", value = model.promptVersion)
    Spacer(modifier = Modifier.height(8.dp))
    SummaryRow(label = "Last classification", value = model.lastClassificationTimestamp)
    Spacer(modifier = Modifier.height(8.dp))
    SummaryRow(label = "Last package", value = model.lastPackage)
    Spacer(modifier = Modifier.height(8.dp))
    SummaryRow(label = "Last decision", value = model.lastDecision)
    Spacer(modifier = Modifier.height(8.dp))
    SummaryRow(label = "Last reason", value = model.lastReason)
    Spacer(modifier = Modifier.height(8.dp))
    SummaryRow(label = "Reason category", value = model.lastReasonCategory)
    Spacer(modifier = Modifier.height(8.dp))
    SummaryRow(label = "Last backend latency", value = model.lastBackendLatency)
    Spacer(modifier = Modifier.height(8.dp))
    SummaryRow(label = "Accessibility", value = model.accessibilityLabel)
    Spacer(modifier = Modifier.height(8.dp))
    SummaryRow(label = "Session", value = model.sessionStatus)
    model.noActiveCommitmentWarning?.let { warning ->
        Spacer(modifier = Modifier.height(8.dp))
        Text(
            text = warning,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.error
        )
    }
    Spacer(modifier = Modifier.height(8.dp))
    SummaryRow(label = "Overlay active", value = model.overlayActiveLabel)
    Spacer(modifier = Modifier.height(14.dp))
    VisionExperimentToggleRow(
        enabled = model.visionExperimentEnabled,
        windowOpen = model.visionExperimentWindowOpen,
        copy = model.visionExperimentCopy,
        onCheckedChange = onVisionExperimentChange
    )

    model.probeDetail?.let { detail ->
        Spacer(modifier = Modifier.height(12.dp))
        Text(
            text = detail,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }

    Spacer(modifier = Modifier.height(14.dp))
    QuietAction(
        text = if (model.testInProgress) "Testing…" else "Test Backend",
        onClick = onTestBackend,
        enabled = !model.testInProgress
    )
    Spacer(modifier = Modifier.height(8.dp))
    QuietAction(text = "Refresh diagnostics", onClick = onRefresh)
}

@Composable
private fun VisionExperimentToggleRow(
    enabled: Boolean,
    windowOpen: Boolean,
    copy: String,
    onCheckedChange: (Boolean) -> Unit
) {
    val colors = MaterialTheme.colorScheme
    val windowLabel = if (windowOpen) {
        "Window open until ${VisionExperiment.KILL_DATE_LABEL}"
    } else {
        "Window closed — capture impossible"
    }
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = "10-day vision experiment",
                style = MaterialTheme.typography.titleMedium,
                color = colors.onSurface
            )
            Spacer(modifier = Modifier.height(2.dp))
            Text(
                text = copy,
                style = MaterialTheme.typography.bodySmall,
                color = colors.onSurfaceVariant
            )
            Spacer(modifier = Modifier.height(2.dp))
            Text(
                text = windowLabel,
                style = MaterialTheme.typography.bodySmall,
                color = if (windowOpen) colors.secondary else colors.error
            )
        }
        Spacer(modifier = Modifier.width(12.dp))
        Switch(
            checked = enabled,
            onCheckedChange = onCheckedChange,
            enabled = windowOpen,
            colors = SwitchDefaults.colors(
                checkedThumbColor = colors.onPrimary,
                checkedTrackColor = colors.primary,
                uncheckedThumbColor = colors.onSurfaceVariant,
                uncheckedTrackColor = colors.surface,
                uncheckedBorderColor = colors.outline
            )
        )
    }
}

@Composable
internal fun AdvancedDeveloperDiagnosticsCard(state: HomeScreenState) {
    CalmCard {
        DeveloperDiagnosticsSection(
            model = state.developerDiagnostics,
            onTestBackend = state::testBackend,
            onRefresh = state::refreshDeveloperDiagnostics,
            onVisionExperimentChange = state::setVisionExperimentEnabled
        )
    }
}
