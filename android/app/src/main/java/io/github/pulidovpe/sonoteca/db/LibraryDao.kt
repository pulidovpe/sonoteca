package io.github.pulidovpe.sonoteca.db

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import androidx.room.Transaction
import androidx.room.Upsert
import kotlinx.coroutines.flow.Flow

@Dao
abstract class LibraryDao {
    @Upsert
    abstract suspend fun upsertTracks(tracks: List<TrackEntity>)

    @Query("SELECT uuid FROM tracks")
    abstract suspend fun trackUuids(): List<String>

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
        "SELECT t.albumArtist AS name, COUNT(*) AS tracks, COUNT(d.trackUuid) AS downloaded FROM tracks t " +
            "LEFT JOIN downloads d ON d.trackUuid = t.uuid AND d.hash = t.hash " +
            "GROUP BY t.albumArtist ORDER BY t.albumArtist COLLATE NOCASE",
    )
    abstract fun artists(): Flow<List<ArtistRow>>

    @Query(
        "SELECT * FROM tracks WHERE albumArtist = :artist " +
            "ORDER BY album COLLATE NOCASE, discNo, trackNo, title COLLATE NOCASE",
    )
    abstract suspend fun tracksOfArtist(artist: String): List<TrackEntity>

    @Query("SELECT trackUuid, hash FROM downloads")
    abstract suspend fun downloadedHashes(): List<DownloadedHash>

    @Query("SELECT * FROM downloads WHERE trackUuid = :uuid")
    abstract suspend fun downloadFor(uuid: String): DownloadEntity?

    @Upsert
    abstract suspend fun upsertDownload(download: DownloadEntity)

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
