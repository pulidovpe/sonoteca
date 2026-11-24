package io.github.pulidovpe.sonoteca.db

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import androidx.room.Transaction
import androidx.room.Upsert
import kotlinx.coroutines.flow.Flow

// Pistas descargadas con la versión actual del catálogo (mismo hash), con la URI de MediaStore.
private const val PLAYABLE_SELECT =
    "SELECT t.uuid AS uuid, t.title AS title, t.artist AS artist, t.albumArtist AS albumArtist, t.album AS album, " +
        "t.trackNo AS trackNo, t.discNo AS discNo, t.duration AS duration, d.uri AS uri " +
        "FROM tracks t JOIN downloads d ON d.trackUuid = t.uuid AND d.hash = t.hash "

@Dao
abstract class LibraryDao {
    @Upsert
    abstract suspend fun upsertTracks(tracks: List<TrackEntity>)

    @Query("SELECT uuid FROM tracks")
    abstract suspend fun trackUuids(): List<String>

    @Query("SELECT uuid, hash, size FROM tracks")
    abstract suspend fun trackHashes(): List<TrackHashRow>

    @Query("DELETE FROM tracks WHERE uuid IN (:uuids)")
    abstract suspend fun deleteTracks(uuids: List<String>)

    @Query("DELETE FROM playlist_tracks")
    abstract suspend fun clearPlaylistLinks()

    @Query("DELETE FROM playlists")
    abstract suspend fun clearPlaylists()

    @Insert
    abstract suspend fun insertPlaylists(playlists: List<PlaylistEntity>)

    @Insert
    abstract suspend fun insertPlaylistLinks(links: List<PlaylistTrackEntity>)

    @Query(
        "SELECT t.albumArtist AS name, COUNT(*) AS tracks, COUNT(d.trackUuid) AS downloaded, MIN(t.uuid) AS sampleUuid FROM tracks t " +
            "LEFT JOIN downloads d ON d.trackUuid = t.uuid AND d.hash = t.hash " +
            "GROUP BY t.albumArtist ORDER BY t.albumArtist COLLATE NOCASE",
    )
    abstract fun artists(): Flow<List<ArtistRow>>

    @Query(
        "SELECT * FROM tracks WHERE albumArtist = :artist " +
            "ORDER BY album COLLATE NOCASE, discNo, trackNo, title COLLATE NOCASE",
    )
    abstract suspend fun tracksOfArtist(artist: String): List<TrackEntity>

    @Query(
        "SELECT t.albumArtist AS artist, t.album AS album, COUNT(*) AS tracks, COUNT(d.trackUuid) AS downloaded, MIN(t.uuid) AS sampleUuid FROM tracks t " +
            "LEFT JOIN downloads d ON d.trackUuid = t.uuid AND d.hash = t.hash " +
            "GROUP BY t.albumArtist, t.album ORDER BY t.album COLLATE NOCASE, t.albumArtist COLLATE NOCASE",
    )
    abstract fun albums(): Flow<List<AlbumRow>>

    @Query(
        "SELECT p.uuid AS uuid, p.name AS name, COUNT(t.uuid) AS tracks, COUNT(d.trackUuid) AS downloaded FROM playlists p " +
            "LEFT JOIN playlist_tracks pt ON pt.playlistUuid = p.uuid " +
            "LEFT JOIN tracks t ON t.uuid = pt.trackUuid " +
            "LEFT JOIN downloads d ON d.trackUuid = t.uuid AND d.hash = t.hash " +
            "GROUP BY p.uuid ORDER BY p.name COLLATE NOCASE",
    )
    abstract fun playlistRows(): Flow<List<PlaylistRow>>

    /** Hasta 4 álbumes de la lista, en el orden en que aparecen (para el collage de su portada, como en el escritorio). */
    @Query(
        "SELECT t.albumArtist AS artist, t.album AS album, MIN(t.uuid) AS sampleUuid FROM playlist_tracks pt " +
            "JOIN tracks t ON t.uuid = pt.trackUuid WHERE pt.playlistUuid = :uuid " +
            "GROUP BY t.albumArtist, t.album ORDER BY MIN(pt.position) LIMIT 4",
    )
    abstract suspend fun playlistCoverSamples(uuid: String): List<CoverSample>

    @Query(
        "SELECT * FROM tracks WHERE albumArtist = :artist AND album = :album " +
            "ORDER BY discNo, trackNo, title COLLATE NOCASE",
    )
    abstract suspend fun tracksOfAlbum(artist: String, album: String): List<TrackEntity>

    @Query(
        "SELECT * FROM tracks WHERE uuid IN (SELECT trackUuid FROM playlist_tracks WHERE playlistUuid = :uuid) " +
            "ORDER BY album COLLATE NOCASE, discNo, trackNo, title COLLATE NOCASE",
    )
    abstract suspend fun tracksOfPlaylist(uuid: String): List<TrackEntity>

    @Query("DELETE FROM downloads WHERE trackUuid = :uuid")
    abstract suspend fun deleteDownload(uuid: String)

    @Query("SELECT trackUuid, hash FROM downloads")
    abstract suspend fun downloadedHashes(): List<DownloadedHash>

    @Query("SELECT * FROM downloads WHERE trackUuid = :uuid")
    abstract suspend fun downloadFor(uuid: String): DownloadEntity?

    @Upsert
    abstract suspend fun upsertDownload(download: DownloadEntity)

    @Query(
        PLAYABLE_SELECT +
            "ORDER BY t.albumArtist COLLATE NOCASE, t.album COLLATE NOCASE, t.discNo, t.trackNo, t.title COLLATE NOCASE",
    )
    abstract fun playableAll(): Flow<List<PlayableTrack>>

    @Query(
        PLAYABLE_SELECT + "WHERE t.albumArtist = :artist " +
            "ORDER BY t.album COLLATE NOCASE, t.discNo, t.trackNo, t.title COLLATE NOCASE",
    )
    abstract suspend fun playableOfArtist(artist: String): List<PlayableTrack>

    @Query(
        PLAYABLE_SELECT + "WHERE t.albumArtist = :artist AND t.album = :album " +
            "ORDER BY t.discNo, t.trackNo, t.title COLLATE NOCASE",
    )
    abstract suspend fun playableOfAlbum(artist: String, album: String): List<PlayableTrack>

    /** En el orden de la lista (no por álbum), como se creó en el escritorio. */
    @Query(
        "SELECT t.uuid AS uuid, t.title AS title, t.artist AS artist, t.albumArtist AS albumArtist, t.album AS album, " +
            "t.trackNo AS trackNo, t.discNo AS discNo, t.duration AS duration, d.uri AS uri " +
            "FROM playlist_tracks pt JOIN tracks t ON t.uuid = pt.trackUuid " +
            "JOIN downloads d ON d.trackUuid = t.uuid AND d.hash = t.hash " +
            "WHERE pt.playlistUuid = :uuid ORDER BY pt.position",
    )
    abstract suspend fun playableOfPlaylist(uuid: String): List<PlayableTrack>

    @Insert
    abstract suspend fun insertPlay(event: PlayEventEntity)

    /** Las más antiguas primero; lotes pequeños (SQLite limita las variables de una consulta). */
    @Query("SELECT * FROM play_events ORDER BY playedAt, eventId LIMIT :limit")
    abstract suspend fun pendingPlays(limit: Int): List<PlayEventEntity>

    @Query("DELETE FROM play_events WHERE eventId IN (:ids)")
    abstract suspend fun deletePlays(ids: List<String>)

    @Query("SELECT COUNT(*) FROM play_events")
    abstract fun pendingPlayCount(): Flow<Int>

    @Query("SELECT COUNT(*) FROM tracks")
    abstract fun trackCount(): Flow<Int>

    @Query("SELECT COUNT(*) FROM playlists")
    abstract fun playlistCount(): Flow<Int>

    /**
     * Aplica el manifiesto en una sola transacción. `allowDeletes` debe ser false mientras el escritorio aún calcula
     * huellas (`pending_hash` > 0): esas pistas todavía no aparecen en el manifiesto y NO deben tomarse por borradas.
     */
    @Transaction
    open suspend fun applyManifest(
        tracks: List<TrackEntity>,
        playlists: List<PlaylistEntity>,
        links: List<PlaylistTrackEntity>,
        allowDeletes: Boolean,
    ) {
        upsertTracks(tracks)
        if (allowDeletes) {
            val keep = tracks.map { it.uuid }.toHashSet()
            // en trozos: SQLite limita los parámetros de una consulta (999 en Android antiguos)
            trackUuids().filter { it !in keep }.chunked(500).forEach { deleteTracks(it) }
        }
        clearPlaylistLinks()
        clearPlaylists()
        insertPlaylists(playlists)
        insertPlaylistLinks(links)
    }
}
