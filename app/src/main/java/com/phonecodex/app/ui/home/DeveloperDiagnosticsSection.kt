package com.phonecodex.app.ui.home

import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.height
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

/**
 * Developer-only layer diagnostics under Advanced Controls.
 * Identifies which layer is broken without dumping noise on the main home screen.
 */
@Composable
internal fun DeveloperDiagnosticsSection(
    model: DeveloperDiagnosticsUiModel,
    onTestBackend: () -> Unit,
    onRefresh: () -> Unit
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
            model.statusLine.contains("offline", ignoreCase = true) ||
            model.statusLine.contains("cannot work", ignoreCase = true)
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
    Spacer(modifier = Modifier.height(8.dp))
    SummaryRow(label = "Overlay active", value = model.overlayActiveLabel)

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
internal fun AdvancedDeveloperDiagnosticsCard(state: HomeScreenState) {
    CalmCard {
        DeveloperDiagnosticsSection(
            model = state.developerDiagnostics,
            onTestBackend = state::testBackend,
            onRefresh = state::refreshDeveloperDiagnostics
        )
    }
}
