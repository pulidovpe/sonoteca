package io.github.pulidovpe.sonoteca.cover

import java.security.MessageDigest

/** Lógica pura de las miniaturas de portadas (sin Android: se prueba en la JVM). */
object CoverKeys {
    /** Un «no hay portada» del escritorio se recuerda este tiempo antes de volver a preguntar (puede que ya la haya descargado). */
    const val MARKER_TTL_MS = 24L * 60 * 60 * 1000

    /** Clave de archivo de la portada de un álbum (artista de álbum + título). */
    fun album(artist: String, album: String): String = "al-" + sha1(artist + "\u0000" + album)

    /** Clave de archivo de la imagen de un artista de álbum. */
    fun artist(name: String): String = "ar-" + sha1(name)

    /** Mayor potencia de 2 con la que el lado corto sigue siendo al menos `target` (para decodificar sin gastar memoria de más). */
    fun sampleSize(width: Int, height: Int, target: Int): Int {
        var size = 1
        val shortSide = minOf(width, height)
        while (shortSide / (size * 2) >= target) size *= 2
        return size
    }

    fun markerExpired(ageMs: Long): Boolean = ageMs > MARKER_TTL_MS

    private fun sha1(text: String): String =
        MessageDigest.getInstance("SHA-1").digest(text.toByteArray(Charsets.UTF_8)).joinToString("") { "%02x".format(it) }
}
