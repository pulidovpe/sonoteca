package io.github.pulidovpe.sonoteca.net

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** Manifiesto generado por el servidor real (sync/manifest.py): si el formato cambia, esta prueba lo detecta. */
class ManifestParserTest {
    private val json = """
{
 "api": 1,
 "schema": 10,
 "generated_at": "2026-11-12T10:00:00.000Z",
 "pending_hash": 0,
 "tracks": [
  {
   "uuid": "61993f2e-6ba5-48ee-be6d-f1033091439d",
   "hash": "2816597888e4a0d3a36b82b83316ab32680eb8f00f8cd3b904d681246d285a0e",
   "size": 100,
   "format": "mp3",
   "title": "De música ligera",
   "artist": "Soda Stereo",
   "album_artist": "Soda Stereo",
   "album": "Canción Animal",
   "track_no": 1,
   "disc_no": null,
   "year": 1990,
   "duration": 60.0,
   "genre": "Rock",
   "has_cover": false,
   "has_lyrics": false
  },
  {
   "uuid": "5e5fb46e-23f0-49e9-8ad3-95c4c6a6b2e5",
   "hash": "aaebc35c4c4e2cc7ac7c65812a7fa476d807b9f3fc60d478dfe098ceeb122321",
   "size": 200,
   "format": "mp3",
   "title": "Entre caníbales",
   "artist": "Soda Stereo",
   "album_artist": "Soda Stereo",
   "album": "Canción Animal",
   "track_no": 2,
   "disc_no": null,
   "year": null,
   "duration": 60.0,
   "genre": null,
   "has_cover": false,
   "has_lyrics": false
  },
  {
   "uuid": "336b350e-6134-426f-bf48-92e6bfd0124d",
   "hash": "5de6bf7f73e34ca05016906d50a4f3ced729bffd9fd1beefb0e0c6a0b5c136e4",
   "size": 50,
   "format": "mp3",
   "title": "Puente",
   "artist": "Gustavo Cerati",
   "album_artist": "Gustavo Cerati",
   "album": "Bocanada",
   "track_no": null,
   "disc_no": null,
   "year": null,
   "duration": 60.0,
   "genre": null,
   "has_cover": false,
   "has_lyrics": false
  }
 ],
 "playlists": [
  {
   "uuid": "6c6654c1-e86c-4dee-a88d-86326dbc0c82",
   "name": "Rock en español",
   "updated_at": "2026-11-12T09:00:00.000Z",
   "tracks": [
    "5e5fb46e-23f0-49e9-8ad3-95c4c6a6b2e5",
    "61993f2e-6ba5-48ee-be6d-f1033091439d"
   ]
  }
 ],
 "deleted_playlists": []
}
""".trimIndent()

    @Test
    fun parsesTracksPlaylistsAndMetadata() {
        val manifest = parseManifest(json)
        assertEquals(1, manifest.api)
        assertEquals(10, manifest.schema)
        assertEquals(0, manifest.pendingHash)
        assertEquals(3, manifest.tracks.size)
        val first = manifest.tracks[0]
        assertEquals("De música ligera", first.title)
        assertEquals("Soda Stereo", first.albumArtist)
        assertEquals(1990, first.year)
        assertEquals("Rock", first.genre)
        assertEquals(60.0, first.duration, 0.0)
        assertFalse(first.hasCover)
        assertEquals(64, first.hash.length)
    }

    @Test
    fun jsonNullsBecomeEmptyDefaultsNotTheTextNull() {
        val last = parseManifest(json).tracks.last()
        assertEquals("Puente", last.title)
        assertEquals(0, last.trackNo)
        assertEquals(0, last.discNo)
        assertEquals(0, last.year)
        assertEquals("", last.genre)
    }

    @Test
    fun playlistKeepsTheOrderOfItsTracks() {
        val manifest = parseManifest(json)
        val playlist = manifest.playlists.single()
        assertEquals("Rock en español", playlist.name)
        assertEquals(listOf("5e5fb46e-23f0-49e9-8ad3-95c4c6a6b2e5", "61993f2e-6ba5-48ee-be6d-f1033091439d"), playlist.tracks)
        assertTrue(manifest.deletedPlaylists.isEmpty())
    }

    @Test
    fun aTrackWithoutAHashYetHasAnEmptyHashAndTheManifestIsComplete() {
        val pending = json
            .replace("\"pending_hash\": 0,", "\"pending_hash\": 1,\n \"complete\": true,")
            .replaceFirst("\"hash\": \"2816597888e4a0d3a36b82b83316ab32680eb8f00f8cd3b904d681246d285a0e\",", "\"hash\": null,")
            .replaceFirst("\"size\": 100,", "\"size\": null,")
        val manifest = parseManifest(pending)
        assertTrue(manifest.complete)
        assertEquals("", manifest.tracks[0].hash)
        assertEquals(0L, manifest.tracks[0].size)
        assertEquals(1, manifest.tracks.count { it.hash.isEmpty() })   // las demás siguen con su huella
    }

    @Test
    fun anOldServerManifestIsNotCompleteByDefault() {
        assertFalse(parseManifest(json).complete)
    }

    @Test
    fun anUnavailableTrackAndTheMissingAndVideoCountsAreParsed() {
        val gone = json
            .replace("\"pending_hash\": 0,", "\"pending_hash\": 0,\n \"missing_files\": 1,\n \"video_tracks\": 2,")
            .replaceFirst("\"size\": 100,", "\"size\": null,\n   \"available\": false,")
        val manifest = parseManifest(gone)
        assertEquals(1, manifest.missingFiles)
        assertEquals(2, manifest.videoTracks)
        assertFalse(manifest.tracks[0].available)
        assertEquals(2, manifest.tracks.count { it.available })
    }

    @Test
    fun anOldServerManifestHasEveryTrackAvailableAndNoCounts() {
        val manifest = parseManifest(json)
        assertTrue(manifest.tracks.all { it.available })
        assertEquals(0, manifest.missingFiles)
        assertEquals(0, manifest.videoTracks)
    }
}
