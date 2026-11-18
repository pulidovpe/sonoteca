package io.github.pulidovpe.sonoteca

import android.content.Context
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.os.StatFs
import io.github.pulidovpe.sonoteca.db.AppDatabase
import io.github.pulidovpe.sonoteca.db.PlayableTrack
import io.github.pulidovpe.sonoteca.db.PlaylistEntity
import io.github.pulidovpe.sonoteca.db.PlaylistTrackEntity
import io.github.pulidovpe.sonoteca.db.TrackEntity
import io.github.pulidovpe.sonoteca.download.DownloadPlan
import io.github.pulidovpe.sonoteca.download.DownloadProgress
import io.github.pulidovpe.sonoteca.download.DownloadSummary
import io.github.pulidovpe.sonoteca.download.TrackDownloader
import io.github.pulidovpe.sonoteca.download.buildPlan
import io.github.pulidovpe.sonoteca.net.Manifest
import io.github.pulidovpe.sonoteca.net.PairingInfo
import io.github.pulidovpe.sonoteca.net.SyncApi
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class SyncRepository(private val context: Context, private val db: AppDatabase, private val store: PairingStore) {
    val artists = db.library().artists()
    val trackCount = db.library().trackCount()
    val playlistCount = db.library().playlistCount()
    val albums = db.library().albums()
    val playlistRows = db.library().playlistRows()
    val playable = db.library().playableAll()

    /** Empareja con el escritorio usando la URL de `sonoteca sync-serve`. Devuelve el emparejamiento guardado. */
    suspend fun pair(rawUrl: String, deviceName: String): Pairing = withContext(Dispatchers.IO) {
        val info = PairingInfo.parse(rawUrl)
            ?: throw IllegalArgumentException("La URL de emparejamiento no es válida. Debe empezar por sonoteca-sync://pair?")
        val name = deviceName.trim().ifEmpty { Build.MODEL }
        val result = SyncApi(info.host, info.port, info.fingerprint).pair(store.deviceId(), name, info.code)
        Pairing(info.host, info.port, info.fingerprint, result.token).also { store.save(it) }
    }

    /** Descarga el manifiesto y lo aplica a la base local. Devuelve un resumen para mostrar. */
    suspend fun sync(pairing: Pairing): String = withContext(Dispatchers.IO) {
        val manifest = SyncApi(pairing.host, pairing.port, pairing.fingerprint, pairing.token).manifest()
        db.library().applyManifest(
            tracks = manifest.tracks.map { it.toEntity() },
            playlists = manifest.playlists.map { PlaylistEntity(it.uuid, it.name, it.updatedAt) },
            links = manifest.playlists.flatMap { playlist ->
                playlist.tracks.mapIndexed { index, trackUuid -> PlaylistTrackEntity(playlist.uuid, index, trackUuid) }
            },
            allowDeletes = manifest.pendingHash == 0,
        )
        summary(manifest)
    }

    private suspend fun tracksFor(selection: Selection): List<TrackEntity> = when (selection) {
        is Selection.Artist -> db.library().tracksOfArtist(selection.name)
        is Selection.Album -> db.library().tracksOfAlbum(selection.artist, selection.album)
        is Selection.Playlist -> db.library().tracksOfPlaylist(selection.uuid)
    }

    /** Las pistas YA descargadas de una selección, listas para reproducir (en orden de álbum; las listas, en su orden). */
    suspend fun playableOf(selection: Selection): List<PlayableTrack> = withContext(Dispatchers.IO) {
        val dao = db.library()
        when (selection) {
            is Selection.Artist -> dao.playableOfArtist(selection.name)
            is Selection.Album -> dao.playableOfAlbum(selection.artist, selection.album)
            is Selection.Playlist -> dao.playableOfPlaylist(selection.uuid)
        }
    }

    /** Qué falta por descargar de una selección (artista, álbum o lista) y cuánto espacio libre hay. */
    suspend fun plan(selection: Selection): DownloadPlan = withContext(Dispatchers.IO) {
        val have = db.library().downloadedHashes().associate { it.trackUuid to it.hash }
        buildPlan(selection.label, tracksFor(selection), have, freeBytes())
    }

    /**
     * Borra del teléfono lo descargado de una selección: la entrada de MediaStore y el registro. No toca el escritorio ni el catálogo.
     * Devuelve (borradas, fallidas). Si la entrada ya no existe, cuenta como borrada.
     */
    suspend fun deleteDownloads(selection: Selection): Pair<Int, Int> = withContext(Dispatchers.IO) {
        val dao = db.library()
        var deleted = 0
        var failed = 0
        for (track in tracksFor(selection)) {
            val download = dao.downloadFor(track.uuid) ?: continue
            try {
                context.contentResolver.delete(Uri.parse(download.uri), null, null)
                dao.deleteDownload(track.uuid)
                deleted++
            } catch (e: Exception) {
                failed++
            }
        }
        deleted to failed
    }

    suspend fun download(pairing: Pairing, plan: DownloadPlan, onProgress: (DownloadProgress) -> Unit): DownloadSummary =
        TrackDownloader(context, db).run(pairing, plan, onProgress)

    @Suppress("DEPRECATION")   // el almacenamiento principal; no hay una API más simple para el espacio libre
    private fun freeBytes(): Long = StatFs(Environment.getExternalStorageDirectory().path).availableBytes

    fun unpair() = store.clear()

    private fun summary(m: Manifest): String {
        val base = "${m.tracks.size} pistas y ${m.playlists.size} listas sincronizadas."
        return if (m.pendingHash > 0) {
            "$base El escritorio aún calcula huellas de ${m.pendingHash} archivos: vuelve a sincronizar en unos minutos."
        } else {
            base
        }
    }

    private fun io.github.pulidovpe.sonoteca.net.ManifestTrack.toEntity() = TrackEntity(
        uuid = uuid, hash = hash, size = size, format = format, title = title, artist = artist,
        albumArtist = albumArtist.ifEmpty { artist }, album = album, trackNo = trackNo, discNo = discNo,
        year = year, duration = duration, genre = genre, hasCover = hasCover, hasLyrics = hasLyrics,
    )
}
