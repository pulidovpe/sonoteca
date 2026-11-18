package io.github.pulidovpe.sonoteca.db

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

/** Réplica de una pista del escritorio. La identidad es `uuid` (estable); `hash` detecta cambios de contenido. */
@Entity(tableName = "tracks", indices = [Index("albumArtist"), Index("album")])
data class TrackEntity(
    @PrimaryKey val uuid: String,
    val hash: String,
    val size: Long,
    val format: String,
    val title: String,
    val artist: String,
    val albumArtist: String,
    val album: String,
    val trackNo: Int,
    val discNo: Int,
    val year: Int,
    val duration: Double,
    val genre: String,
    val hasCover: Boolean,
    val hasLyrics: Boolean,
)

@Entity(tableName = "playlists")
data class PlaylistEntity(
    @PrimaryKey val uuid: String,
    val name: String,
    val updatedAt: String,
)

/** Orden de las pistas de una lista (sin clave foránea: una pista aún sin huella puede faltar un rato en `tracks`). */
@Entity(tableName = "playlist_tracks", primaryKeys = ["playlistUuid", "position"], indices = [Index("trackUuid")])
data class PlaylistTrackEntity(
    val playlistUuid: String,
    val position: Int,
    val trackUuid: String,
)

/** Lo ya descargado al teléfono: `hash` es el del archivo guardado (si cambia en el catálogo, hay que bajarlo de nuevo). */
@Entity(tableName = "downloads")
data class DownloadEntity(
    @PrimaryKey val trackUuid: String,
    val hash: String,
    val uri: String,
    val sizeBytes: Long,
    val downloadedAt: Long,
)

data class DownloadedHash(val trackUuid: String, val hash: String)

/** Una pista descargada y lista para reproducir (resultado de consultas; no es una tabla). `uri` es la entrada de MediaStore. */
data class PlayableTrack(
    val uuid: String,
    val title: String,
    val artist: String,
    val albumArtist: String,
    val album: String,
    val trackNo: Int,
    val discNo: Int,
    val duration: Double,
    val uri: String,
)

data class ArtistRow(val name: String, val tracks: Int, val downloaded: Int)

data class AlbumRow(val artist: String, val album: String, val tracks: Int, val downloaded: Int)

data class PlaylistRow(val uuid: String, val name: String, val tracks: Int, val downloaded: Int)
