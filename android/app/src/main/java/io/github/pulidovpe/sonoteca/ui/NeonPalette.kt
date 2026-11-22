package io.github.pulidovpe.sonoteca.ui

/**
 * Colores del tema «Neón»: los MISMOS valores que `src/sonoteca/ui/qml/Theme.qml` del escritorio (ARGB). Generado a partir de ese archivo;
 * `NeonParityTest` lo compara con él para que la CI avise si el escritorio cambia un color y el móvil no. Sin dependencias de Android ni Compose.
 */
object NeonPalette {
    const val CYAN = 0xFF00D0FCL
    const val BLUE = 0xFF0396FDL
    const val VIOLET = 0xFF9849FDL
    const val MAGENTA = 0xFFBA38FCL
    const val BG = 0xFF060E16L
    const val SIDEBAR = 0xFF040A10L
    const val BAR = 0xFF050B11L
    const val PLAYER_BAR = 0xFF0A141DL
    const val SURFACE = 0xFF0C1822L
    const val SURFACE_HOVER = 0xFF152536L
    const val SURFACE_RAISED = 0xFF14212EL
    const val PANEL = 0xFF0F1B27L
    const val FIELD = 0xFF08121AL
    const val BORDER = 0xFF1E3043L
    const val DIVIDER = 0xFF172636L
    const val TRACK = 0xFF2B3D50L
    const val TEXT = 0xFFF4F9FFL
    const val TEXT_SOFT = 0xFFC9D6E2L
    const val TEXT_DIM = 0xFF8DA2B6L
    const val TEXT_FAINT = 0xFF5D7184L
    const val ACCENT_SOFT = 0xFF0E2D3DL
    const val TEXT_ON_ACCENT = 0xFF031018L
    const val WARN = 0xFFF5C26BL
    const val DANGER = 0xFFFF6B81L
    const val SCRIM = 0xB0020A12L
    const val PLACEHOLDER = 0xFF101D29L

    /** Nombre en `Theme.qml` → color ARGB. */
    val tokens: Map<String, Long> = mapOf(
        "cyan" to CYAN,
        "blue" to BLUE,
        "violet" to VIOLET,
        "magenta" to MAGENTA,
        "bg" to BG,
        "sidebar" to SIDEBAR,
        "bar" to BAR,
        "playerBar" to PLAYER_BAR,
        "surface" to SURFACE,
        "surfaceHover" to SURFACE_HOVER,
        "surfaceRaised" to SURFACE_RAISED,
        "panel" to PANEL,
        "field" to FIELD,
        "border" to BORDER,
        "divider" to DIVIDER,
        "track" to TRACK,
        "text" to TEXT,
        "textSoft" to TEXT_SOFT,
        "textDim" to TEXT_DIM,
        "textFaint" to TEXT_FAINT,
        "accentSoft" to ACCENT_SOFT,
        "textOnAccent" to TEXT_ON_ACCENT,
        "warn" to WARN,
        "danger" to DANGER,
        "scrim" to SCRIM,
        "placeholder" to PLACEHOLDER,
    )
}
