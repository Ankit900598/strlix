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

@Composable
internal fun PromiseUnderstandingCard(
    understanding: PromiseUnderstanding,
    startBlockedMessage: String?,
    onStartCommitment: () -> Unit,
    onEditPromise: () -> Unit
) {
    val colors = MaterialTheme.colorScheme
    val needsClarification = !understanding.clarificationQuestion.isNullOrBlank()

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
            StatusPill(
                text = when {
                    needsClarification -> "Needs clarification"
                    understanding.source == UnderstandingSource.LOCAL_PREVIEW -> "Draft"
                    else -> "Compiled"
                },
                tone = if (needsClarification) PillTone.ALERT else PillTone.CALM
            )
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

        SummaryRow(label = "Time", value = understanding.sessionTimeLabel)
        Spacer(modifier = Modifier.height(12.dp))
        SummaryRow(label = "Allowed", value = understanding.allowedLabel)
        Spacer(modifier = Modifier.height(12.dp))
        SummaryRow(label = "Blocked", value = understanding.blockedLabel)

        understanding.conditionalLabel?.let { conditional ->
            Spacer(modifier = Modifier.height(12.dp))
            SummaryRow(label = "Conditional", value = conditional)
        }

        understanding.clarificationQuestion?.let { question ->
            Spacer(modifier = Modifier.height(18.dp))
            HorizontalDivider(color = colors.outlineVariant)
            Spacer(modifier = Modifier.height(14.dp))
            SummaryRow(label = "Need clarification", value = question)
        }

        if (understanding.cautions.isNotEmpty()) {
            Spacer(modifier = Modifier.height(14.dp))
            SummaryRow(
                label = "Cautions",
                value = understanding.cautions.joinToString(" · ")
            )
        }

        if (!needsClarification) {
            Spacer(modifier = Modifier.height(12.dp))
            SummaryRow(label = "Strictness", value = understanding.strictnessLabel)
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = understanding.driftLabel,
                style = MaterialTheme.typography.bodySmall,
                color = colors.onSurfaceVariant
            )
        }

        if (understanding.managedApps.isNotEmpty() && !needsClarification) {
            Spacer(modifier = Modifier.height(12.dp))
            Text(
                text = "Apps involved: ${understanding.managedApps.joinToString(", ")}",
                style = MaterialTheme.typography.bodySmall,
                color = colors.onSurfaceVariant
            )
        }

        Spacer(modifier = Modifier.height(22.dp))
        if (understanding.canStart) {
            PrimaryAction(text = "Start Commitment", onClick = onStartCommitment)
        } else {
            Text(
                text = "Edit your promise to answer the question, then tap Understand Promise again.",
                style = MaterialTheme.typography.bodySmall,
                color = colors.onSurfaceVariant
            )
        }

        startBlockedMessage?.let { message ->
            Spacer(modifier = Modifier.height(10.dp))
            Text(
                text = message,
                style = MaterialTheme.typography.bodySmall,
                color = colors.error
            )
        }

        Spacer(modifier = Modifier.height(10.dp))
        QuietAction(
            text = if (needsClarification) "Edit promise" else "Change my promise",
            onClick = onEditPromise
        )
    }
}
