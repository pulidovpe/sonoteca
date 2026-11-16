package io.github.pulidovpe.sonoteca.download

import java.util.Locale

/** Nombres de carpetas y archivos en `Music/Sonoteca/<Artista>/<Álbum>/`. Lógica pura (sin Android): se prueba en la JVM. */
object Naming {
    private val ILLEGAL = Regex("[\\\\/:*?\"<>|\\p{Cntrl}]")

    /** Un nombre seguro para carpeta o archivo: sin caracteres prohibidos, sin puntos/espacios al final y de longitud acotada. */
    fun clean(name: String, max: Int = 80): String {
        var s = name.replace(ILLEGAL, "_").trim().trimEnd('.', ' ')
        if (s.length > max) s = s.substring(0, max).trimEnd('.', ' ')
        return s.ifEmpty { "_" }
    }

    fun relativeDir(artist: String, album: String): String =
        "Music/Sonoteca/${clean(artist.ifBlank { "Desconocido" })}/${clean(album.ifBlank { "Sin álbum" })}"

    fun displayName(trackNo: Int, discNo: Int, title: String, format: String): String {
        val number = when {
            trackNo <= 0 -> ""
            discNo > 1 -> String.format(Locale.ROOT, "%d-%02d - ", discNo, trackNo)
            else -> String.format(Locale.ROOT, "%02d - ", trackNo)
        }
        return number + clean(title.ifBlank { "Sin título" }) + "." + extensionFor(format)
    }

    fun extensionFor(format: String): String = format.lowercase(Locale.ROOT).trimStart('.').ifEmpty { "mp3" }

    fun mimeFor(format: String): String = when (extensionFor(format)) {
        "mp3" -> "audio/mpeg"
        "m4a", "mp4", "aac" -> "audio/mp4"
        "flac" -> "audio/flac"
        "ogg", "oga", "opus" -> "audio/ogg"
        "wav" -> "audio/x-wav"
        else -> "audio/mpeg"
    }
}
