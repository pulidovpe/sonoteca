package io.github.pulidovpe.sonoteca

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Test

class SelectionTest {
    @Test
    fun labelsAreReadableAndHandleEmptyNames() {
        assertEquals("Soda Stereo", Selection.Artist("Soda Stereo").label)
        assertEquals("(sin artista)", Selection.Artist("").label)
        assertEquals("Bocanada — Gustavo Cerati", Selection.Album("Gustavo Cerati", "Bocanada").label)
        assertEquals("(sin álbum) — (sin artista)", Selection.Album("", "").label)
        assertEquals("Rock en español", Selection.Playlist("u", "Rock en español").label)
    }

    @Test
    fun differentSelectionsAreDifferentValues() {
        assertEquals(Selection.Album("A", "X"), Selection.Album("A", "X"))
        assertNotEquals(Selection.Album("A", "X"), Selection.Album("B", "X"))
        assertNotEquals(Selection.Artist("A") as Selection, Selection.Playlist("A", "A") as Selection)
    }
}
