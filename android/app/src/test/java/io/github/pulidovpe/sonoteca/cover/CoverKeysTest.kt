package io.github.pulidovpe.sonoteca.cover

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class CoverKeysTest {
    @Test
    fun keysAreStableAndFileSafe() {
        val key = CoverKeys.album("Alanis Morissette", "Jagged Little Pill")
        assertEquals(key, CoverKeys.album("Alanis Morissette", "Jagged Little Pill"))
        assertTrue(Regex("^al-[0-9a-f]{40}$").matches(key))
        assertTrue(Regex("^ar-[0-9a-f]{40}$").matches(CoverKeys.artist("Ñandú / AC:DC \"x\"")))
    }

    @Test
    fun differentAlbumsAndArtistsGetDifferentKeys() {
        assertNotEquals(CoverKeys.album("A", "B"), CoverKeys.album("B", "A"))
        assertNotEquals(CoverKeys.album("AB", "C"), CoverKeys.album("A", "BC"))   // el separador evita colisiones
        assertNotEquals(CoverKeys.album("A", ""), CoverKeys.artist("A"))
    }

    @Test
    fun sha1MatchesAKnownValue() {
        // SHA-1 de «abc»: a9993e364706816aba3e25717850c26c9cd0d89d (RFC 3174)
        assertEquals("ar-a9993e364706816aba3e25717850c26c9cd0d89d", CoverKeys.artist("abc"))
    }

    @Test
    fun sampleSizeKeepsTheShortSideAtLeastTheTarget() {
        assertEquals(1, CoverKeys.sampleSize(200, 200, 320))
        assertEquals(1, CoverKeys.sampleSize(500, 500, 320))
        assertEquals(2, CoverKeys.sampleSize(1000, 1000, 256))
        assertEquals(8, CoverKeys.sampleSize(4000, 3000, 256))
        assertEquals(1, CoverKeys.sampleSize(4000, 100, 256))   // el lado corto manda
    }

    @Test
    fun aNoCoverMarkerExpiresAfterADay() {
        assertFalse(CoverKeys.markerExpired(0))
        assertFalse(CoverKeys.markerExpired(CoverKeys.MARKER_TTL_MS))
        assertTrue(CoverKeys.markerExpired(CoverKeys.MARKER_TTL_MS + 1))
    }
}
