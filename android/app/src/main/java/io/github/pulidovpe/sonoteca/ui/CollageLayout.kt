package io.github.pulidovpe.sonoteca.ui

/**
 * Cómo se reparten las portadas del collage de una lista: un álbum = su portada; 2 = dos mitades; 3 = una mitad y dos cuartos;
 * 4 = 2×2. Es la misma tabla que `PlaylistCover.qml` del escritorio (`NeonParityTest` ya compara la paleta; `CollageLayoutTest`, esto).
 * Posiciones y tamaños como fracción del lado. Sin Android: se prueba en la JVM.
 */
object CollageLayout {
    class Tile(val x: Float, val y: Float, val w: Float, val h: Float)

    /** Baldosas para `albums` álbumes distintos (se usan como mucho 4). */
    fun tiles(albums: Int): List<Tile> = when (albums.coerceIn(0, 4)) {
        1 -> listOf(Tile(0f, 0f, 1f, 1f))
        2 -> listOf(Tile(0f, 0f, 0.5f, 1f), Tile(0.5f, 0f, 0.5f, 1f))
        3 -> listOf(Tile(0f, 0f, 0.5f, 1f), Tile(0.5f, 0f, 0.5f, 0.5f), Tile(0.5f, 0.5f, 0.5f, 0.5f))
        4 -> listOf(Tile(0f, 0f, 0.5f, 0.5f), Tile(0.5f, 0f, 0.5f, 0.5f), Tile(0f, 0.5f, 0.5f, 0.5f), Tile(0.5f, 0.5f, 0.5f, 0.5f))
        else -> emptyList()
    }
}
