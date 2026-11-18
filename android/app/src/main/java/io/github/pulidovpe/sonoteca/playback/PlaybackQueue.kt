package io.github.pulidovpe.sonoteca.playback

import io.github.pulidovpe.sonoteca.db.PlayableTrack

/** Lógica pura de la cola de reproducción (sin Android: se prueba en la JVM). */
object PlaybackQueue {
    /** Máximo de pistas que se envían de una vez al servicio de reproducción (evita mensajes enormes entre procesos). */
    const val MAX_ITEMS = 500

    class Window(val tracks: List<PlayableTrack>, val startIndex: Int)

    /**
     * Recorta la lista a `limit` pistas alrededor de la elegida (un quinto antes y el resto después) y devuelve dónde queda.
     * Si cabe entera, no se recorta. `startIndex` fuera de rango se ajusta; con la lista vacía devuelve una ventana vacía.
     */
    fun window(tracks: List<PlayableTrack>, startIndex: Int, limit: Int = MAX_ITEMS): Window {
        if (tracks.isEmpty()) return Window(emptyList(), 0)
        val start = startIndex.coerceIn(0, tracks.lastIndex)
        if (tracks.size <= limit) return Window(tracks, start)
        val from = (start - limit / 5).coerceIn(0, tracks.size - limit)
        return Window(tracks.subList(from, from + limit), start - from)
    }

    /** Solo se reproducen entradas de MediaStore (lo que descargó la app): ningún `file://`, `https://` ni otros proveedores. */
    fun isAllowedUri(uri: String): Boolean = uri.startsWith("content://media/")

    /** `m:ss` a partir de milisegundos; valores negativos o desconocidos se muestran como `0:00`. */
    fun formatTime(ms: Long): String {
        val total = (ms / 1000).coerceAtLeast(0)
        return "${total / 60}:${(total % 60).toString().padStart(2, '0')}"
    }
}
