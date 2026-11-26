package io.github.pulidovpe.sonoteca

import android.content.Context
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.os.StatFs
import io.github.pulidovpe.sonoteca.db.AppDatabase
import io.github.pulidovpe.sonoteca.db.CoverSample
import io.github.pulidovpe.sonoteca.db.PlayableTrack
import io.github.pulidovpe.sonoteca.db.PlaylistEntity
import io.github.pulidovpe.sonoteca.db.PlaylistTrackEntity
import io.github.pulidovpe.sonoteca.db.TrackEntity
import io.github.pulidovpe.sonoteca.db.TrackHashRow
import io.github.pulidovpe.sonoteca.download.DownloadPlan
import io.github.pulidovpe.sonoteca.download.DownloadProgress
import io.github.pulidovpe.sonoteca.download.DownloadSummary
import io.github.pulidovpe.sonoteca.download.TrackDownloader
import io.github.pulidovpe.sonoteca.download.buildPlan
import io.github.pulidovpe.sonoteca.net.Manifest
import io.github.pulidovpe.sonoteca.net.PairingInfo
import io.github.pulidovpe.sonoteca.net.PlayEvent
import io.github.pulidovpe.sonoteca.net.SyncApi
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class SyncRepository(private val context: Context, private val db: AppDatabase, private val store: PairingStore) {
    // Pistas cuyo archivo no está en el disco del escritorio (lo dice el manifiesto en cada sincronización). Se guardan aparte, en
    // preferencias, para no tocar el esquema de la base de datos.
    private val catalogPrefs = context.getSharedPreferences("catalog", Context.MODE_PRIVATE)

    private fun unavailableUuids(): Set<String> = catalogPrefs.getStringSet(KEY_UNAVAILABLE, emptySet()) ?: emptySet()

    val artists = db.library().artists()
    val trackCount = db.library().trackCount()
    val playlistCount = db.library().playlistCount()
    val albums = db.library().albums()
    val playlistRows = db.library().playlistRows()
    val playable = db.library().playableAll()
    val pendingPlays = db.library().pendingPlayCount()

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
        // primero se suben las reproducciones anotadas sin conexión; si falla, no impide sincronizar el catálogo (quedan guardadas)
        val uploaded = try {
            uploadPlays(pairing)
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            null
        }
        val manifest = SyncApi(pairing.host, pairing.port, pairing.fingerprint, pairing.token).manifest()
        // si el escritorio aún no tiene la huella de una pista que ya conocemos (la reescribió), se conserva la anterior:
        // así lo descargado sigue contando como descargado hasta que llegue la nueva
        val known = db.library().trackHashes().associateBy { it.uuid }
        db.library().applyManifest(
            tracks = manifest.tracks.map { track -> track.toEntity().let { keepKnownHash(it, known[it.uuid]) } },
            playlists = manifest.playlists.map { PlaylistEntity(it.uuid, it.name, it.updatedAt) },
            links = manifest.playlists.flatMap { playlist ->
                playlist.tracks.mapIndexed { index, trackUuid -> PlaylistTrackEntity(playlist.uuid, index, trackUuid) }
            },
            // con `complete` el manifiesto trae todas las pistas, así que lo que falta ya no existe; un servidor antiguo solo es fiable sin pendientes
            allowDeletes = manifest.complete || manifest.pendingHash == 0,
        )
        catalogPrefs.edit().putStringSet(KEY_UNAVAILABLE, manifest.tracks.filter { !it.available }.map { it.uuid }.toSet()).apply()
        summary(manifest) + when {
            uploaded == null -> " No se pudieron subir las reproducciones: se reintentará."
            uploaded > 0 -> " Subidas $uploaded reproducciones al escritorio."
            else -> ""
        }
    }

    /**
     * Sube al escritorio las reproducciones anotadas en el teléfono (en lotes) y las borra al recibir el 200. Devuelve cuántas envió.
     * Si falla, lanza y NO borra nada: se reintenta la próxima vez (el escritorio ignora las repetidas).
     */
    suspend fun uploadPlays(pairing: Pairing): Int = withContext(Dispatchers.IO) {
        val api = SyncApi(pairing.host, pairing.port, pairing.fingerprint, pairing.token)
        var sent = 0
        while (true) {
            val batch = db.library().pendingPlays(PLAY_BATCH)
            if (batch.isEmpty()) break
            api.plays(batch.map { PlayEvent(it.eventId, it.trackUuid, it.playedAt) })
            db.library().deletePlays(batch.map { it.eventId })
            sent += batch.size
        }
        sent
    }

    private suspend fun tracksFor(selection: Selection): List<TrackEntity> = when (selection) {
        is Selection.Artist -> db.library().tracksOfArtist(selection.name)
        is Selection.Album -> db.library().tracksOfAlbum(selection.artist, selection.album)
        is Selection.Playlist -> db.library().tracksOfPlaylist(selection.uuid)
    }

    suspend fun playlistCoverSamples(uuid: String): List<CoverSample> = db.library().playlistCoverSamples(uuid)

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
        buildPlan(selection.label, tracksFor(selection), have, freeBytes(), unavailableUuids())
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
        return buildString {
            append(base)
            if (m.pendingHash > 0) {
                append(" El escritorio aún calcula la huella de ${m.pendingHash} archivos: esas pistas ya se ven, pero no se pueden descargar todavía; sincroniza otra vez en unos minutos.")
            }
            if (m.missingFiles > 0) {
                append(" ${m.missingFiles} pistas están en la biblioteca del escritorio pero su archivo no está en su disco (¿disco externo desconectado o archivos movidos?): no se pueden descargar.")
            }
            if (m.videoTracks > 0) append(" Los ${m.videoTracks} vídeos del escritorio no se sincronizan (solo audio).")
        }
    }

    private fun io.github.pulidovpe.sonoteca.net.ManifestTrack.toEntity() = TrackEntity(
        uuid = uuid, hash = hash, size = size, format = format, title = title, artist = artist,
        albumArtist = albumArtist.ifEmpty { artist }, album = album, trackNo = trackNo, discNo = discNo,
        year = year, duration = duration, genre = genre, hasCover = hasCover, hasLyrics = hasLyrics,
    )
}

private const val PLAY_BATCH = 500   // reproducciones por petición (y por consulta de borrado)

/**
 * Si el escritorio aún no tiene la huella de una pista (la reescribió y la recalcula), se conservan la huella y el tamaño que el catálogo
 * ya conocía: así lo descargado sigue contando como descargado hasta que llegue la nueva. Una pista nueva sin huella queda con `hash` vacío.
 */
internal fun keepKnownHash(entity: TrackEntity, before: TrackHashRow?): TrackEntity =
    if (entity.hash.isEmpty() && before != null) entity.copy(hash = before.hash, size = before.size) else entity

private const val KEY_UNAVAILABLE = "unavailable"
