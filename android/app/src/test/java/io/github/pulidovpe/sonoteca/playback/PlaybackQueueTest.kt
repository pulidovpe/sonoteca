package io.github.pulidovpe.sonoteca.playback

import io.github.pulidovpe.sonoteca.db.PlayableTrack
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PlaybackQueueTest {
    private fun tracks(count: Int) = (0 until count).map { i ->
        PlayableTrack(
            uuid = "u$i", title = "T$i", artist = "A", albumArtist = "A", album = "Al",
            trackNo = i + 1, discNo = 1, duration = 180.0, uri = "content://media/external/audio/media/$i",
        )
    }

    @Test
    fun smallListsAreKeptWhole() {
        val all = tracks(10)
        val window = PlaybackQueue.window(all, 4)
        assertEquals(all, window.tracks)
        assertEquals(4, window.startIndex)
    }

    @Test
    fun startIndexIsClampedAndEmptyListIsSafe() {
        val all = tracks(3)
        assertEquals(2, PlaybackQueue.window(all, 99).startIndex)
        assertEquals(0, PlaybackQueue.window(all, -5).startIndex)
        val empty = PlaybackQueue.window(emptyList(), 7)
        assertTrue(empty.tracks.isEmpty())
        assertEquals(0, empty.startIndex)
    }

    @Test
    fun longListsAreCutAroundTheChosenTrack() {
        val all = tracks(1600)
        val middle = PlaybackQueue.window(all, 1000)
        assertEquals(PlaybackQueue.MAX_ITEMS, middle.tracks.size)
        assertEquals("u900", middle.tracks.first().uuid)
        assertEquals(100, middle.startIndex)
        assertEquals("u1000", middle.tracks[middle.startIndex].uuid)
    }

    @Test
    fun cutsAtBothEndsKeepTheChosenTrackAndFullSize() {
        val all = tracks(1600)
        val first = PlaybackQueue.window(all, 0)
        assertEquals(PlaybackQueue.MAX_ITEMS, first.tracks.size)
        assertEquals("u0", first.tracks[first.startIndex].uuid)
        val last = PlaybackQueue.window(all, 1599)
        assertEquals(PlaybackQueue.MAX_ITEMS, last.tracks.size)
        assertEquals("u1599", last.tracks[last.startIndex].uuid)
        assertEquals("u1599", last.tracks.last().uuid)
    }

    @Test
    fun onlyMediaStoreUrisAreAllowed() {
        assertTrue(PlaybackQueue.isAllowedUri("content://media/external/audio/media/42"))
        assertTrue(PlaybackQueue.isAllowedUri("content://media/external_primary/audio/media/42"))
        assertFalse(PlaybackQueue.isAllowedUri("file:///sdcard/Music/a.mp3"))
        assertFalse(PlaybackQueue.isAllowedUri("https://ejemplo.org/a.mp3"))
        assertFalse(PlaybackQueue.isAllowedUri("content://otra.app.provider/archivo"))
        assertFalse(PlaybackQueue.isAllowedUri(""))
    }

    @Test
    fun timeIsFormattedAsMinutesAndSeconds() {
        assertEquals("0:00", PlaybackQueue.formatTime(0))
        assertEquals("0:09", PlaybackQueue.formatTime(9_999))
        assertEquals("3:05", PlaybackQueue.formatTime(185_000))
        assertEquals("75:03", PlaybackQueue.formatTime(4_503_000))
        assertEquals("0:00", PlaybackQueue.formatTime(-9_223_372_036_854_775_807L))
    }
}
