package com.phonecodex.app.ui.home

import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.height
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.phonecodex.app.domain.model.RecoveryPolicy

/**
 * Escape hatches for a locked session. Deliberately quiet: this is the path the user should
 * have to think about before taking.
 */
@Composable
internal fun LockedSessionRecoverySection(
    policy: RecoveryPolicy,
    onEmergencyExit: () -> Unit,
    onCooldownUnlock: () -> Unit
) {
    MicroLabel(text = "Recovery")
    Spacer(modifier = Modifier.height(10.dp))

    SummaryRow(label = "Mistakes", value = "${policy.mistakeWindowMinutes} minute window")
    Spacer(modifier = Modifier.height(8.dp))
    SummaryRow(label = "Cooldown", value = "${policy.cooldownHours} hours")
    Spacer(modifier = Modifier.height(8.dp))
    SummaryRow(
        label = "Override",
        value = if (policy.emergencyOverrideAllowed) "Allowed" else "Not allowed"
    )
    Spacer(modifier = Modifier.height(8.dp))
    SummaryRow(
        label = "Trusted admin",
        value = if (policy.trustedAdminRequired) "Required" else "Not required"
    )
    Spacer(modifier = Modifier.height(8.dp))
    SummaryRow(
        label = "Break fee",
        value = if (policy.breakFeeEnabled) "Planned" else "Disabled"
    )

    Spacer(modifier = Modifier.height(16.dp))
    QuietAction(
        text = "Emergency exit",
        onClick = onEmergencyExit,
        enabled = policy.emergencyOverrideAllowed,
        destructive = true
    )
    if (!policy.emergencyOverrideAllowed) {
        Spacer(modifier = Modifier.height(6.dp))
        Text(
            text = "You turned emergency exit off when you made this promise.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
    Spacer(modifier = Modifier.height(10.dp))
    QuietAction(text = "Request cooldown unlock", onClick = onCooldownUnlock)
}
