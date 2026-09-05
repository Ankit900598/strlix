package com.phonecodex.app.ui.home

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.unit.dp

/**
 * The confirmation step: the app repeats the promise back before anything is enforced.
 *
 * Every value here comes from [PromiseUnderstanding]. Swapping the local heuristics for the
 * real Promise Compiler changes nothing in this file.
 */
@Composable
internal fun PromiseUnderstandingCard(
    understanding: PromiseUnderstanding,
    startBlockedMessage: String?,
    onStartCommitment: () -> Unit,
    onEditPromise: () -> Unit
) {
    val colors = MaterialTheme.colorScheme

    CalmCard(highlighted = true) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(
                text = "I understood",
                style = MaterialTheme.typography.headlineSmall,
                color = colors.onSurface
            )
            if (understanding.source == UnderstandingSource.LOCAL_PREVIEW) {
                StatusPill(text = "Draft", tone = PillTone.CALM)
            }
        }

        Spacer(modifier = Modifier.height(10.dp))
        Text(
            text = "\u201C${understanding.promiseText}\u201D",
            style = MaterialTheme.typography.bodyMedium,
            fontStyle = FontStyle.Italic,
            color = colors.onSurfaceVariant
        )

        Spacer(modifier = Modifier.height(18.dp))
        HorizontalDivider(color = colors.outlineVariant)
        Spacer(modifier = Modifier.height(18.dp))

        SummaryRow(label = "Duration", value = understanding.durationLabel)
        Spacer(modifier = Modifier.height(12.dp))
        SummaryRow(label = "Allowed", value = understanding.allowedLabel)
        Spacer(modifier = Modifier.height(12.dp))
        SummaryRow(label = "Blocked", value = understanding.blockedLabel)
        Spacer(modifier = Modifier.height(12.dp))
        SummaryRow(label = "Strictness", value = understanding.strictnessLabel)
        Spacer(modifier = Modifier.height(12.dp))
        SummaryRow(label = "If I drift", value = understanding.driftLabel)

        understanding.caution?.let { caution ->
            Spacer(modifier = Modifier.height(16.dp))
            Text(
                text = caution,
                style = MaterialTheme.typography.bodySmall,
                color = colors.primary
            )
        }

        if (understanding.managedApps.isNotEmpty()) {
            Spacer(modifier = Modifier.height(16.dp))
            Text(
                text = "Apps I will take over: ${understanding.managedApps.joinToString(" · ")}",
                style = MaterialTheme.typography.bodySmall,
                color = colors.onSurfaceVariant
            )
        }

        Spacer(modifier = Modifier.height(22.dp))
        PrimaryAction(text = "Start Commitment", onClick = onStartCommitment)

        startBlockedMessage?.let { message ->
            Spacer(modifier = Modifier.height(10.dp))
            Text(
                text = message,
                style = MaterialTheme.typography.bodySmall,
                color = colors.error
            )
        }

        Spacer(modifier = Modifier.height(10.dp))
        QuietAction(text = "Change my promise", onClick = onEditPromise)
    }
}
