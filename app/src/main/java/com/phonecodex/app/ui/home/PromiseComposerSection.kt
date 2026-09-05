package com.phonecodex.app.ui.home

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

/**
 * The one thing the home screen asks for: a promise, in the user's own words.
 */
@Composable
internal fun PromiseComposerSection(
    promiseText: String,
    onPromiseTextChange: (String) -> Unit,
    onExampleSelected: (ExamplePromise) -> Unit,
    onUnderstandPromise: () -> Unit
) {
    val colors = MaterialTheme.colorScheme

    CalmCard {
        Text(
            text = "What promise should I protect?",
            style = MaterialTheme.typography.headlineSmall,
            color = colors.onSurface
        )
        Spacer(modifier = Modifier.height(6.dp))
        Text(
            text = "Say it the way you would say it out loud. I will turn it into rules " +
                "and show you what I understood before anything starts.",
            style = MaterialTheme.typography.bodySmall,
            color = colors.onSurfaceVariant
        )

        Spacer(modifier = Modifier.height(18.dp))
        OutlinedTextField(
            value = promiseText,
            onValueChange = onPromiseTextChange,
            modifier = Modifier.fillMaxWidth(),
            placeholder = {
                Text(
                    text = "Tomorrow I have my OS exam. Keep me on one lecture playlist for " +
                        "3 hours…",
                    style = MaterialTheme.typography.bodyMedium,
                    color = colors.onSurfaceVariant
                )
            },
            textStyle = MaterialTheme.typography.bodyLarge,
            minLines = 4,
            shape = RoundedCornerShape(ActionCorner),
            colors = OutlinedTextFieldDefaults.colors(
                focusedBorderColor = colors.primary,
                unfocusedBorderColor = colors.outline,
                focusedContainerColor = Color.Transparent,
                unfocusedContainerColor = Color.Transparent,
                cursorColor = colors.primary,
                focusedTextColor = colors.onSurface,
                unfocusedTextColor = colors.onSurface
            )
        )

        Spacer(modifier = Modifier.height(16.dp))
        MicroLabel(text = "Or start from one of these")
        Spacer(modifier = Modifier.height(10.dp))
        FlowRow(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            EXAMPLE_PROMISES.forEach { example ->
                PromiseChip(
                    text = example.chipLabel,
                    onClick = { onExampleSelected(example) }
                )
            }
        }

        Spacer(modifier = Modifier.height(22.dp))
        PrimaryAction(
            text = "Understand Promise",
            onClick = onUnderstandPromise,
            enabled = promiseText.isNotBlank()
        )
    }
}
