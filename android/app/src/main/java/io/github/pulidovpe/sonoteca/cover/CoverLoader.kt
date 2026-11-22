package io.github.pulidovpe.sonoteca.cover

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.util.LruCache
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import io.github.pulidovpe.sonoteca.PairingStore
import io.github.pulidovpe.sonoteca.net.SyncApi
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Semaphore
import kotlinx.coroutines.sync.withPermit
import kotlinx.coroutines.withContext
import java.io.File
import java.io.IOException

/**
 * Miniaturas de portadas de álbumes y de imágenes de artistas. Se piden al escritorio SOLO cuando se ven, se reducen a 320 px
 * (recorte cuadrado) y se guardan en `files/covers`, así que después se ven sin conexión. Si el escritorio no tiene imagen, se
 * recuerda 24 h (`.none`) y la interfaz enseña la «cajita» de color plano, como el escritorio. Sin emparejamiento solo se usa lo guardado.
 */
class CoverLoader(context: Context, private val store: PairingStore) {
    private val dir = File(context.filesDir, "covers").apply { mkdirs() }
    private val memory = object : LruCache<String, ImageBitmap>(MEMORY_BYTES) {
        override fun sizeOf(key: String, value: ImageBitmap): Int = value.width * value.height * 4
    }
    private val gate = Semaphore(PARALLEL_DOWNLOADS)

    /** Lo que ya está en memoria (para que una fila que reaparece al desplazar no parpadee). */
    fun cached(key: String): ImageBitmap? = memory.get(key)

    /** `null` = no hay imagen (o no se pudo conseguir ahora: sin escritorio al alcance). `sampleUuid` es una pista del álbum/artista. */
    suspend fun load(key: String, sampleUuid: String, artist: Boolean): ImageBitmap? = withContext(Dispatchers.IO) {
        memory.get(key) ?: fromDisk(key) ?: fromServer(key, sampleUuid, artist)
    }

    private fun fromDisk(key: String): ImageBitmap? {
        val file = File(dir, "$key.jpg")
        if (!file.isFile) return null
        val image = BitmapFactory.decodeFile(file.path)?.asImageBitmap()
        if (image == null) file.delete() else memory.put(key, image)   // archivo dañado: se vuelve a pedir
        return image
    }

    private suspend fun fromServer(key: String, sampleUuid: String, artist: Boolean): ImageBitmap? {
        val marker = File(dir, "$key.none")
        if (marker.isFile && !CoverKeys.markerExpired(System.currentTimeMillis() - marker.lastModified())) return null
        val pairing = store.load() ?: return null
        return gate.withPermit {
            fromDisk(key) ?: try {   // otra petición pudo bajarla mientras esperaba su turno
                val bytes = SyncApi(pairing.host, pairing.port, pairing.fingerprint, pairing.token).image(sampleUuid, artist)
                if (bytes == null) {
                    marker.writeText("")   // el escritorio no tiene imagen: no se vuelve a preguntar hasta que caduque
                    null
                } else {
                    saveThumbnail(bytes, File(dir, "$key.jpg"))
                    marker.delete()
                    fromDisk(key)
                }
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                null   // sin escritorio al alcance o imagen ilegible: no se guarda nada y se reintenta la próxima vez
            }
        }
    }

    /** Decodifica reducida, recorta al cuadrado centrado, escala a [THUMB_PX] y guarda como JPEG (escritura atómica). */
    private fun saveThumbnail(bytes: ByteArray, target: File) {
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        BitmapFactory.decodeByteArray(bytes, 0, bytes.size, bounds)
        if (bounds.outWidth <= 0 || bounds.outHeight <= 0) throw IOException("imagen no válida")
        val options = BitmapFactory.Options().apply { inSampleSize = CoverKeys.sampleSize(bounds.outWidth, bounds.outHeight, THUMB_PX) }
        val decoded = BitmapFactory.decodeByteArray(bytes, 0, bytes.size, options) ?: throw IOException("imagen ilegible")
        val side = minOf(decoded.width, decoded.height)
        val square = Bitmap.createBitmap(decoded, (decoded.width - side) / 2, (decoded.height - side) / 2, side, side)
        val thumb = if (side > THUMB_PX) Bitmap.createScaledBitmap(square, THUMB_PX, THUMB_PX, true) else square
        val temp = File(target.parentFile, target.name + ".tmp")
        temp.outputStream().use { thumb.compress(Bitmap.CompressFormat.JPEG, JPEG_QUALITY, it) }
        if (!temp.renameTo(target)) {
            temp.delete()
            throw IOException("no se pudo guardar la miniatura")
        }
    }

    private companion object {
        const val THUMB_PX = 320
        const val JPEG_QUALITY = 85
        const val MEMORY_BYTES = 24 * 1024 * 1024
        const val PARALLEL_DOWNLOADS = 4
    }
}
