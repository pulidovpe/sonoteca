package io.github.pulidovpe.sonoteca

import io.github.pulidovpe.sonoteca.db.TrackEntity
import io.github.pulidovpe.sonoteca.db.TrackHashRow
import org.junit.Assert.assertEquals
import org.junit.Assert.assertSame
import org.junit.Test

class KeepKnownHashTest {
    private fun track(hash: String, size: Long) = TrackEntity(
        uuid = "u1", hash = hash, size = size, format = "mp3", title = "T", artist = "A", albumArtist = "A", album = "X",
        trackNo = 1, discNo = 0, year = 0, duration = 1.0, genre = "", hasCover = false, hasLyrics = false,
    )

    @Test
    fun aKnownTrackWithoutAnewHashKeepsTheOldHashAndSize() {
        val merged = keepKnownHash(track("", 0), TrackHashRow("u1", "viejo", 123))
        assertEquals("viejo", merged.hash)
        assertEquals(123L, merged.size)
    }

    @Test
    fun aNewHashAlwaysWins() {
        val fresh = track("nuevo", 456)
        assertSame(fresh, keepKnownHash(fresh, TrackHashRow("u1", "viejo", 123)))
    }

    @Test
    fun aNewTrackWithoutAHashStaysEmptyUntilTheDesktopHasIt() {
        val merged = keepKnownHash(track("", 0), null)
        assertEquals("", merged.hash)
        assertEquals(0L, merged.size)
    }
}
