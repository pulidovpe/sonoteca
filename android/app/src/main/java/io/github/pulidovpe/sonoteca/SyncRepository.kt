package io.github.pulidovpe.sonoteca

import android.content.Context
import android.os.Build
import android.os.Environment
import android.os.StatFs
import io.github.pulidovpe.sonoteca.db.AppDatabase
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

    /** Qué falta por descargar de un artista (agrupado por artista del álbum) y cuánto espacio libre hay. */
    suspend fun planArtist(artist: String): DownloadPlan = withContext(Dispatchers.IO) {
        val tracks = db.library().tracksOfArtist(artist)
        val have = db.library().downloadedHashes().associate { it.trackUuid to it.hash }
        buildPlan(artist.ifEmpty { "(sin artista)" }, tracks, have, freeBytes())
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
