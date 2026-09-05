package com.phonecodex.app.ui.theme

import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.platform.LocalContext

private val DarkColorScheme = darkColorScheme(
    primary = Clay,
    onPrimary = ClayOnDark,
    primaryContainer = ClaySoftDark,
    onPrimaryContainer = Clay,
    secondary = Sage,
    onSecondary = ClayOnDark,
    secondaryContainer = SageSoftDark,
    onSecondaryContainer = Sage,
    tertiary = Clay,
    background = InkBackground,
    onBackground = InkTextPrimary,
    surface = InkSurface,
    onSurface = InkTextPrimary,
    surfaceVariant = InkSurfaceRaised,
    onSurfaceVariant = InkTextMuted,
    outline = InkOutline,
    outlineVariant = InkOutlineSoft,
    error = Ember,
    onError = InkTextPrimary,
    errorContainer = EmberSoftDark,
    onErrorContainer = Ember
)

private val LightColorScheme = lightColorScheme(
    primary = ClayDeep,
    onPrimary = PaperSurface,
    primaryContainer = ClaySoftLight,
    onPrimaryContainer = ClayDeep,
    secondary = Sage,
    onSecondary = PaperSurface,
    secondaryContainer = SageSoftLight,
    onSecondaryContainer = PaperTextPrimary,
    tertiary = ClayDeep,
    background = PaperBackground,
    onBackground = PaperTextPrimary,
    surface = PaperSurface,
    onSurface = PaperTextPrimary,
    surfaceVariant = PaperSurfaceRaised,
    onSurfaceVariant = PaperTextMuted,
    outline = PaperOutline,
    outlineVariant = PaperOutlineSoft,
    error = Ember,
    onError = PaperSurface,
    errorContainer = EmberSoftLight,
    onErrorContainer = ClayOnDark
)

/**
 * Dynamic colour is off by default: PhoneCodex should feel like the same calm companion
 * on every phone, not like whatever wallpaper the user picked.
 */
@Composable
fun PhoneCodexTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    dynamicColor: Boolean = false,
    content: @Composable () -> Unit
) {
    val colorScheme = when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            val context = LocalContext.current
            if (darkTheme) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
        }

        darkTheme -> DarkColorScheme
        else -> LightColorScheme
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = Typography,
        content = content
    )
}
