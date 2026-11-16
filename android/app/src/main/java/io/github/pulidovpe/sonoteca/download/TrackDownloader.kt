package io.github.pulidovpe.sonoteca.download

import android.content.ContentValues
import android.content.Context
import android.net.Uri
import android.provider.MediaStore
import io.github.pulidovpe.sonoteca.Pairing
import io.github.pulidovpe.sonoteca.db.AppDatabase
import io.github.pulidovpe.sonoteca.db.DownloadEntity
import io.github.pulidovpe.sonoteca.net.SyncApi
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.withContext
import java.io.File
import java.io.IOException

data class DownloadProgress(
    val doneTracks: Int,
    val totalTracks: Int,
    val currentTitle: String,
    val bytesDone: Long,
    val bytesTotal: Long,
) {
    val fraction: Float get() = if (bytesTotal <= 0L) 0f else (bytesDone.toFloat() / bytesTotal.toFloat()).coerceIn(0f, 1f)
}

data class DownloadSummary(val ok: Int, val failed: Int, val bytes: Long, val firstError: String?) {
    fun text(): String {
        val base = "Descargadas $ok pistas (${formatBytes(bytes)})."
        return if (failed > 0) "$base Fallaron $failed: $firstError" else base
    }
}

/**
 * Descarga pistas al teléfono: cada una va a un `.part` reanudable en la caché de la app, se verifica por SHA-256 y SOLO entonces se
 * publica en `Music/Sonoteca/<Artista>/<Álbum>/` con MediaStore (así nunca queda un archivo a medias en la música del teléfono).
 * Una pista a la vez. Si el proceso se detiene, lo descargado se conserva y se reanuda al repetir.
 */
class TrackDownloader(private val context: Context, private val db: AppDatabase) {
    suspend fun run(pairing: Pairing, plan: DownloadPlan, onProgress: (DownloadProgress) -> Unit): DownloadSummary =
        withContext(Dispatchers.IO) {
            val api = SyncApi(pairing.host, pairing.port, pairing.fingerprint, pairing.token)
            val dao = db.library()
            val job = coroutineContext[Job]
            val partDir = File(context.cacheDir, "downloads")
            val total = plan.pending.size
            val bytesTotal = plan.pendingBytes
            var bytesDone = 0L
            var ok = 0
            var failed = 0
            var firstError: String? = null

            for ((index, track) in plan.pending.withIndex()) {
                ensureActive()
                onProgress(DownloadProgress(index, total, track.title, bytesDone, bytesTotal))
                try {
                    val part = File(partDir, "${track.uuid}.part")
                    FileDownloader.download(
                        part = part,
                        expectedHash = track.hash,
                        expectedSize = track.size,
                        open = { offset -> api.openFile(track.uuid, offset) },
                        onBytes = { written -> onProgress(DownloadProgress(index, total, track.title, bytesDone + written, bytesTotal)) },
                        isCancelled = { job?.isActive == false },
                    )
                    // si había una versión anterior, se borra ANTES de publicar la nueva (si no, MediaStore renombra la nueva «(1)»)
                    dao.downloadFor(track.uuid)?.let { previous -> deleteEntry(Uri.parse(previous.uri)) }
                    val uri = publish(
                        part,
                        Naming.relativeDir(track.albumArtist.ifEmpty { track.artist }, track.album),
                        Naming.displayName(track.trackNo, track.discNo, track.title, track.format),
                        Naming.mimeFor(track.format),
                    )
                    dao.upsertDownload(DownloadEntity(track.uuid, track.hash, uri.toString(), track.size, System.currentTimeMillis()))
                    part.delete()
                    ok++
                    bytesDone += track.size
                } catch (e: CancellationException) {
                    throw e
                } catch (e: Exception) {
                    ensureActive()   // una cancelación llega como InterruptedIOException: se trata como cancelación, no como fallo
                    failed++
                    if (firstError == null) firstError = "${track.title}: ${e.message ?: e.javaClass.simpleName}"
                }
            }
            onProgress(DownloadProgress(total, total, "", bytesDone, bytesTotal))
            DownloadSummary(ok, failed, bytesDone, firstError)
        }

    private fun publish(source: File, relativeDir: String, displayName: String, mime: String): Uri {
        val resolver = context.contentResolver
        val collection = MediaStore.Audio.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY)
        val values = ContentValues().apply {
            put(MediaStore.Audio.Media.DISPLAY_NAME, displayName)
            put(MediaStore.Audio.Media.MIME_TYPE, mime)
            put(MediaStore.Audio.Media.RELATIVE_PATH, relativeDir)
            put(MediaStore.Audio.Media.IS_PENDING, 1)
        }
        val uri = resolver.insert(collection, values) ?: throw IOException("MediaStore no creó la entrada de $displayName")
        try {
            val out = resolver.openOutputStream(uri, "w") ?: throw IOException("No se pudo abrir $displayName para escribir")
            out.use { target -> source.inputStream().use { input -> input.copyTo(target) } }
            val done = ContentValues().apply { put(MediaStore.Audio.Media.IS_PENDING, 0) }
            resolver.update(uri, done, null, null)
        } catch (e: Exception) {
            resolver.delete(uri, null, null)
            throw e
        }
        return uri
    }

    private fun deleteEntry(uri: Uri) {
        try {
            context.contentResolver.delete(uri, null, null)
        } catch (e: Exception) {
            // la entrada ya no existe o no es nuestra: no es un error
        }
    }
}
