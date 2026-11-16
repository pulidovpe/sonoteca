package io.github.pulidovpe.sonoteca.download

import io.github.pulidovpe.sonoteca.db.TrackEntity
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PlanTest {
    private fun track(uuid: String, hash: String, size: Long) = TrackEntity(
        uuid = uuid, hash = hash, size = size, format = "mp3", title = uuid, artist = "A", albumArtist = "A", album = "X",
        trackNo = 1, discNo = 0, year = 0, duration = 1.0, genre = "", hasCover = false, hasLyrics = false,
    )

    private val tracks = listOf(track("u1", "h1", 100), track("u2", "h2", 200), track("u3", "h3", 300))

    @Test
    fun onlyMissingOrChangedTracksArePending() {
        val plan = buildPlan("A", tracks, mapOf("u1" to "h1", "u2" to "viejo"), freeBytes = 10_000_000_000L)
        assertEquals(listOf("u2", "u3"), plan.pending.map { it.uuid })
        assertEquals(1, plan.replacing)          // u2 estaba descargada pero cambió
        assertEquals(1, plan.alreadyDone)
        assertEquals(500L, plan.pendingBytes)
        assertEquals(3, plan.totalTracks)
    }

    @Test
    fun nothingPendingWhenEverythingMatches() {
        val plan = buildPlan("A", tracks, tracks.associate { it.uuid to it.hash }, freeBytes = 0)
        assertTrue(plan.pending.isEmpty())
        assertEquals(3, plan.alreadyDone)
        assertEquals(0L, plan.pendingBytes)
    }

    @Test
    fun spaceCheckKeepsTheSafetyMargin() {
        val enough = buildPlan("A", tracks, emptyMap(), freeBytes = 600 + FREE_SPACE_MARGIN_BYTES)
        assertTrue(enough.fits)
        val tight = buildPlan("A", tracks, emptyMap(), freeBytes = 599 + FREE_SPACE_MARGIN_BYTES)
        assertFalse(tight.fits)
    }

    @Test
    fun bytesAreFormattedForHumans() {
        assertEquals("0 KB", formatBytes(0))
        assertEquals("512 KB", formatBytes(512L * 1024))
        assertEquals("5 MB", formatBytes(5L * 1024 * 1024))
        assertEquals("1.5 GB", formatBytes((1.5 * 1024 * 1024 * 1024).toLong()))
        assertEquals("90.5 GB", formatBytes((90.46 * 1024 * 1024 * 1024).toLong()))
    }
}
