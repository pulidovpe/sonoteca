package io.github.pulidovpe.sonoteca

/** Lo que se puede elegir para descargar o borrar del teléfono: un artista, un álbum o una lista. Lógica pura (se prueba en la JVM). */
sealed interface Selection {
    val label: String

    data class Artist(val name: String) : Selection {
        override val label: String get() = name.ifEmpty { "(sin artista)" }
    }

    data class Album(val artist: String, val album: String) : Selection {
        override val label: String get() = album.ifEmpty { "(sin álbum)" } + " — " + artist.ifEmpty { "(sin artista)" }
    }

    data class Playlist(val uuid: String, val name: String) : Selection {
        override val label: String get() = name
    }
}

/** Petición pendiente de confirmar: borrar del teléfono las `count` pistas descargadas de `selection`. */
data class DeleteAsk(val selection: Selection, val count: Int)
