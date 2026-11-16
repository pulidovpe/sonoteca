package io.github.pulidovpe.sonoteca.download

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class NamingTest {
    @Test
    fun cleanReplacesForbiddenCharactersAndTrailingDots() {
        assertEquals("AC_DC", Naming.clean("AC/DC"))
        assertEquals("Que_ Donde_", Naming.clean("Que? Donde:"))
        assertEquals("Fin", Naming.clean("Fin..."))
        assertEquals("a_b", Naming.clean("a\u0000b"))
        assertEquals("_", Naming.clean("   "))
        assertEquals("_", Naming.clean(".."))
    }

    @Test
    fun cleanLimitsLengthWithoutLeavingTrailingSpaces() {
        val long = "x".repeat(79) + " " + "y".repeat(50)
        val cleaned = Naming.clean(long)
        assertTrue(cleaned.length <= 80)
        assertTrue(!cleaned.endsWith(" "))
    }

    @Test
    fun relativeDirUsesMusicSonotecaArtistAlbumWithFallbacks() {
        assertEquals("Music/Sonoteca/Soda Stereo/Canción Animal", Naming.relativeDir("Soda Stereo", "Canción Animal"))
        assertEquals("Music/Sonoteca/Desconocido/Sin álbum", Naming.relativeDir("", " "))
        assertEquals("Music/Sonoteca/AC_DC/Back_In Black", Naming.relativeDir("AC/DC", "Back/In Black"))
    }

    @Test
    fun displayNameNumbersTracksAndDiscs() {
        assertEquals("01 - De música ligera.mp3", Naming.displayName(1, 0, "De música ligera", "mp3"))
        assertEquals("12 - Tema.m4a", Naming.displayName(12, 1, "Tema", "M4A"))
        assertEquals("2-05 - Tema.mp3", Naming.displayName(5, 2, "Tema", "mp3"))
        assertEquals("Sin número.mp3", Naming.displayName(0, 0, "Sin número", "mp3"))
        assertEquals("Sin título.mp3", Naming.displayName(0, 0, "", ""))
    }

    @Test
    fun mimeTypesMatchTheExtension() {
        assertEquals("audio/mpeg", Naming.mimeFor("mp3"))
        assertEquals("audio/mp4", Naming.mimeFor("m4a"))
        assertEquals("audio/flac", Naming.mimeFor("FLAC"))
        assertEquals("audio/ogg", Naming.mimeFor("opus"))
        assertEquals("audio/mpeg", Naming.mimeFor("desconocido"))
    }
}
