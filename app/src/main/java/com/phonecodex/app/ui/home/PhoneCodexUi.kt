package com.phonecodex.app.ui.home

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp

/**
 * Design primitives for the PhoneCodex companion UI.
 *
 * Everything here is presentation only: no stores, no engines, no I/O.
 */

internal val CardCorner: Dp = 22.dp
internal val ActionCorner: Dp = 16.dp

/** Rounded, low-contrast container. The single building block of the home screen. */
@Composable
internal fun CalmCard(
    modifier: Modifier = Modifier,
    highlighted: Boolean = false,
    content: @Composable ColumnScope.() -> Unit
) {
    val colors = MaterialTheme.colorScheme
    Surface(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(CardCorner),
        color = if (highlighted) colors.surfaceVariant else colors.surface,
        border = BorderStroke(
            width = 1.dp,
            color = if (highlighted) colors.outline else colors.outlineVariant
        )
    ) {
        Column(modifier = Modifier.padding(20.dp), content = content)
    }
}

/** The one obvious action on a screen. */
@Composable
internal fun PrimaryAction(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true
) {
    Button(
        onClick = onClick,
        modifier = modifier
            .fillMaxWidth()
            .heightIn(min = 56.dp),
        enabled = enabled,
        shape = RoundedCornerShape(ActionCorner),
        colors = ButtonDefaults.buttonColors(
            containerColor = MaterialTheme.colorScheme.primary,
            contentColor = MaterialTheme.colorScheme.onPrimary,
            disabledContainerColor = MaterialTheme.colorScheme.surfaceVariant,
            disabledContentColor = MaterialTheme.colorScheme.onSurfaceVariant
        )
    ) {
        Text(text = text, style = MaterialTheme.typography.labelLarge)
    }
}

/** Secondary action: present, but never competing with the primary. */
@Composable
internal fun QuietAction(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    destructive: Boolean = false
) {
    val contentColor = if (destructive) {
        MaterialTheme.colorScheme.error
    } else {
        MaterialTheme.colorScheme.onSurfaceVariant
    }
    Surface(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(ActionCorner),
        color = Color.Transparent,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline)
    ) {
        TextButton(
            onClick = onClick,
            enabled = enabled,
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 50.dp),
            shape = RoundedCornerShape(ActionCorner)
        ) {
            Text(
                text = text,
                style = MaterialTheme.typography.titleMedium,
                color = if (enabled) contentColor else MaterialTheme.colorScheme.outline
            )
        }
    }
}

/** Tappable example promise. */
@Composable
internal fun PromiseChip(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    subtle: Boolean = false
) {
    val colors = MaterialTheme.colorScheme
    Surface(
        onClick = onClick,
        enabled = enabled,
        modifier = modifier,
        shape = RoundedCornerShape(100.dp),
        color = if (subtle) {
            colors.surface.copy(alpha = 0.35f)
        } else {
            colors.surfaceVariant
        },
        border = BorderStroke(
            1.dp,
            if (subtle) colors.outlineVariant.copy(alpha = 0.7f) else colors.outlineVariant
        )
    ) {
        Text(
            text = text,
            style = MaterialTheme.typography.bodySmall,
            color = if (enabled) {
                colors.onSurfaceVariant
            } else {
                colors.outline
            },
            modifier = Modifier.padding(
                horizontal = if (subtle) 12.dp else 14.dp,
                vertical = if (subtle) 7.dp else 9.dp
            )
        )
    }
}

internal enum class PillTone { CALM, POSITIVE, ALERT }

/** Small read-only status marker. */
@Composable
internal fun StatusPill(text: String, tone: PillTone, modifier: Modifier = Modifier) {
    val colors = MaterialTheme.colorScheme
    val content = when (tone) {
        PillTone.CALM -> colors.onSurfaceVariant
        PillTone.POSITIVE -> colors.secondary
        PillTone.ALERT -> colors.error
    }
    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(100.dp),
        color = when (tone) {
            PillTone.CALM -> colors.surface
            PillTone.POSITIVE -> colors.secondaryContainer
            PillTone.ALERT -> colors.errorContainer
        },
        border = BorderStroke(1.dp, colors.outlineVariant)
    ) {
        Text(
            text = text,
            style = MaterialTheme.typography.labelMedium,
            color = content,
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp)
        )
    }
}

/** `Label      value` row used by the "I understood" card. */
@Composable
internal fun SummaryRow(label: String, value: String) {
    Row(modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.Top) {
        Text(
            text = label,
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.width(94.dp)
        )
        Text(
            text = value,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurface,
            modifier = Modifier.weight(1f)
        )
    }
}

/** Uppercase micro-label used to separate blocks inside Advanced Controls. */
@Composable
internal fun MicroLabel(text: String, modifier: Modifier = Modifier) {
    Text(
        text = text.uppercase(),
        style = MaterialTheme.typography.labelSmall,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
        modifier = modifier
    )
}

/** Row of mutually exclusive small options (durations, thresholds, cooldowns). */
@Composable
internal fun <T> OptionRow(
    options: List<T>,
    selected: T,
    label: (T) -> String,
    onSelected: (T) -> Unit,
    enabled: Boolean = true
) {
    val colors = MaterialTheme.colorScheme
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        options.forEach { option ->
            val isSelected = option == selected
            Surface(
                onClick = { onSelected(option) },
                enabled = enabled && !isSelected,
                modifier = Modifier.weight(1f),
                shape = RoundedCornerShape(12.dp),
                color = if (isSelected) colors.primaryContainer else colors.surface,
                border = BorderStroke(
                    width = 1.dp,
                    color = if (isSelected) colors.primary else colors.outlineVariant
                )
            ) {
                Text(
                    text = label(option),
                    style = MaterialTheme.typography.labelMedium,
                    color = if (isSelected) colors.primary else colors.onSurfaceVariant,
                    textAlign = TextAlign.Center,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 11.dp)
                )
            }
        }
    }
}
