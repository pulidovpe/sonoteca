package io.github.pulidovpe.sonoteca.playback

import java.time.Instant
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter

/**
 * Decide cuándo una pista cuenta como «reproducida»: tras 5 s de AVANCE normal (igual que el escritorio: `stats.COUNT_AFTER_MS`;
 * saltar con la barra no suma, retroceder tampoco; pausar no suma), o la duración entera si la pista dura menos de 5 s, y como mucho una
 * vez por reproducción. Al empezar otra pista —o la misma de nuevo— se reinicia. Lógica pura, sin Android: se prueba en la JVM.
 */
class PlayCounter(private val onCount: (trackUuid: String) -> Unit) {
    private var uuid: String? = null
    private var listened = 0L
    private var last = -1L
    private var counted = false

    /** Empieza una pista (o `null` si ya no hay ninguna). */
    fun startItem(trackUuid: String?) {
        uuid = trackUuid
        listened = 0
        last = -1
        counted = false
    }

    /** Se llama cada medio segundo MIENTRAS suena, con la posición actual y la duración (0 si aún no se conoce). */
    fun onPosition(positionMs: Long, durationMs: Long) {
        val current = uuid ?: return
        if (counted) return
        if (last in 0L..positionMs && positionMs - last <= MAX_STEP_MS) listened += positionMs - last
        last = positionMs
        if (listened >= threshold(durationMs)) {
            counted = true
            onCount(current)
        }
    }

    companion object {
        const val COUNT_AFTER_MS = 5_000L
        const val MAX_STEP_MS = 2_500L   // un avance mayor entre dos lecturas es un salto, no escucha

        fun threshold(durationMs: Long): Long = if (durationMs <= 0) COUNT_AFTER_MS else maxOf(1L, minOf(COUNT_AFTER_MS, durationMs))
    }
}

/** Formato de fecha del protocolo (docs/SYNC.md): UTC ISO 8601 con milisegundos, `2026-11-18T10:00:00.123Z`. */
object PlayEvents {
    private val format = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'").withZone(ZoneOffset.UTC)

    fun timestamp(epochMs: Long): String = format.format(Instant.ofEpochMilli(epochMs))
}
