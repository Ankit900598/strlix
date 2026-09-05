package com.phonecodex.app.ui.home

import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.height
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

/**
 * Only rendered when protection is off. A promise the phone cannot enforce is worse than no
 * promise, so this is the one alert allowed on the home screen.
 */
@Composable
internal fun ProtectionSetupCard(onOpenAccessibilitySettings: () -> Unit) {
    CalmCard {
        Text(
            text = "I cannot see your screen yet",
            style = MaterialTheme.typography.titleLarge,
            color = MaterialTheme.colorScheme.error
        )
        Spacer(modifier = Modifier.height(6.dp))
        Text(
            text = "Turn on the PhoneCodex accessibility service so I can notice when you " +
                "drift. Until then I can hold a promise, but I cannot protect it.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Spacer(modifier = Modifier.height(16.dp))
        PrimaryAction(text = "Turn On Protection", onClick = onOpenAccessibilitySettings)
    }
}

/** Raw protection health. Lives under Advanced Controls. */
@Composable
internal fun ProtectionHealthDetails(
    isAccessibilityEnabled: Boolean,
    violationCount: Int,
    lastViolationReason: String?,
    onOpenAccessibilitySettings: () -> Unit,
    onClearViolations: () -> Unit
) {
    MicroLabel(text = "Protection status")
    Spacer(modifier = Modifier.height(10.dp))
    SummaryRow(
        label = "Service",
        value = if (isAccessibilityEnabled) "Connected" else "Disconnected"
    )
    Spacer(modifier = Modifier.height(8.dp))
    SummaryRow(label = "Violations", value = violationCount.toString())
    if (!lastViolationReason.isNullOrBlank()) {
        Spacer(modifier = Modifier.height(8.dp))
        SummaryRow(label = "Last", value = lastViolationReason)
    }
    Spacer(modifier = Modifier.height(14.dp))
    if (!isAccessibilityEnabled) {
        QuietAction(
            text = "Open accessibility settings",
            onClick = onOpenAccessibilitySettings
        )
        Spacer(modifier = Modifier.height(8.dp))
    }
    QuietAction(
        text = "Clear violations",
        onClick = onClearViolations,
        enabled = violationCount > 0
    )
}
