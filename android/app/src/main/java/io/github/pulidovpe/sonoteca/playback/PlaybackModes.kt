package io.github.pulidovpe.sonoteca.playback

/** Modos de reproducción (aleatorio y repetir). Lógica pura, sin Android: se prueba en la JVM. */
object PlaybackModes {
    // mismos valores que Player.REPEAT_MODE_OFF / ONE / ALL de Media3 (lo comprueba PlaybackModesTest)
    const val REPEAT_OFF = 0
    const val REPEAT_ONE = 1
    const val REPEAT_ALL = 2

    /** Como en el escritorio: sin repetir → repetir todas → repetir una → sin repetir. */
    fun nextRepeat(mode: Int): Int = when (mode) {
        REPEAT_OFF -> REPEAT_ALL
        REPEAT_ALL -> REPEAT_ONE
        else -> REPEAT_OFF
    }

    fun repeatLabel(mode: Int): String = when (mode) {
        REPEAT_ALL -> "Repetir todas"
        REPEAT_ONE -> "Repetir una"
        else -> "Repetir"
    }
}
