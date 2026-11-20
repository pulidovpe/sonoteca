package io.github.pulidovpe.sonoteca.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color

/** Colores del tema «Neón» como `Color` de Compose (mismos valores que el escritorio: ver [NeonPalette]). */
object Neon {
    val cyan = Color(NeonPalette.CYAN)
    val blue = Color(NeonPalette.BLUE)
    val violet = Color(NeonPalette.VIOLET)
    val magenta = Color(NeonPalette.MAGENTA)
    val textOnAccent = Color(NeonPalette.TEXT_ON_ACCENT)

    /** Degradado cian → magenta del botón de reproducir (como en el escritorio). */
    val playGradient: Brush = Brush.linearGradient(listOf(cyan, magenta))
}

/**
 * Esquema de Material 3 con los colores del escritorio: fondo azul casi negro, acento cian, violeta y magenta de la marca.
 * Siempre oscuro (el escritorio no tiene tema claro). Los niveles `surfaceContainer*` van de la barra lateral a las superficies elevadas.
 */
private val NeonColorScheme = darkColorScheme(
    primary = Neon.cyan,
    onPrimary = Neon.textOnAccent,
    primaryContainer = Color(NeonPalette.ACCENT_SOFT),
    onPrimaryContainer = Color(NeonPalette.TEXT),
    inversePrimary = Neon.blue,
    secondary = Neon.violet,
    onSecondary = Color(NeonPalette.TEXT),
    secondaryContainer = Color(NeonPalette.ACCENT_SOFT),   // fila/pestaña seleccionada, como en el escritorio
    onSecondaryContainer = Neon.cyan,
    tertiary = Neon.magenta,
    onTertiary = Color(NeonPalette.TEXT),
    tertiaryContainer = Color(NeonPalette.SURFACE_RAISED),
    onTertiaryContainer = Color(NeonPalette.TEXT),
    background = Color(NeonPalette.BG),
    onBackground = Color(NeonPalette.TEXT),
    surface = Color(NeonPalette.BG),
    onSurface = Color(NeonPalette.TEXT),
    surfaceVariant = Color(NeonPalette.SURFACE),
    onSurfaceVariant = Color(NeonPalette.TEXT_DIM),
    surfaceTint = Color.Transparent,   // sin velo de color al elevar: las superficies ya traen su tono
    inverseSurface = Color(NeonPalette.TEXT),
    inverseOnSurface = Color(NeonPalette.BG),
    error = Color(NeonPalette.DANGER),
    onError = Neon.textOnAccent,
    errorContainer = Color(NeonPalette.SURFACE_RAISED),
    onErrorContainer = Color(NeonPalette.DANGER),
    outline = Color(NeonPalette.TEXT_FAINT),
    outlineVariant = Color(NeonPalette.BORDER),   // divisores sutiles
    scrim = Color(NeonPalette.SCRIM),
    surfaceBright = Color(NeonPalette.SURFACE_HOVER),
    surfaceDim = Color(NeonPalette.SIDEBAR),
    surfaceContainerLowest = Color(NeonPalette.SIDEBAR),
    surfaceContainerLow = Color(NeonPalette.BAR),
    surfaceContainer = Color(NeonPalette.PLAYER_BAR),   // barra de navegación y reproductor, como la barra de reproducción del escritorio
    surfaceContainerHigh = Color(NeonPalette.SURFACE),
    surfaceContainerHighest = Color(NeonPalette.SURFACE_RAISED),
)

@Composable
fun SonotecaTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = NeonColorScheme, content = content)
}
