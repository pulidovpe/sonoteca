package io.github.pulidovpe.sonoteca.download

import java.io.Closeable
import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import java.io.InputStream
import java.io.InterruptedIOException
import java.security.MessageDigest

/** Respuesta del escritorio a la petición de un archivo (la crea `SyncApi.openFile`; en las pruebas, una falsa). */
class RemoteFile(
    val status: Int,
    val contentRange: String?,
    val hash: String?,
    val body: InputStream?,
    private val onClose: () -> Unit = {},
) : Closeable {
    override fun close() {
        try {
            body?.close()
        } catch (_: IOException) {
            // ya cerrada
        }
        onClose()
    }
}

/** El archivo cambió en el escritorio desde el último catálogo: hay que volver a sincronizar el catálogo. */
class ChangedOnDesktopException(message: String) : IOException(message)

/** El archivo llegó completo pero su SHA-256 no es el del catálogo: se descarta. */
class HashMismatchException(message: String) : IOException(message)

object Sha256 {
    fun of(bytes: ByteArray): String = hex(MessageDigest.getInstance("SHA-256").digest(bytes))

    fun of(file: File): String {
        val digest = MessageDigest.getInstance("SHA-256")
        file.inputStream().use { input ->
            val buffer = ByteArray(1 shl 16)
            while (true) {
                val n = input.read(buffer)
                if (n < 0) break
                digest.update(buffer, 0, n)
            }
        }
        return hex(digest.digest())
    }

    private fun hex(bytes: ByteArray): String = bytes.joinToString("") { "%02x".format(it) }
}

/**
 * Descarga a un archivo parcial (`.part`) que se REANUDA con `Range` si se cortó, y solo da por buena la descarga si el tamaño y el
 * SHA-256 coinciden con el catálogo. Lógica pura: `open(offset)` es quien habla con el escritorio.
 */
object FileDownloader {
    private val CONTENT_RANGE = Regex("""bytes (\d+)-(\d+)/""")

    fun rangeStart(contentRange: String?): Long? = contentRange?.let { CONTENT_RANGE.find(it)?.groupValues?.get(1)?.toLongOrNull() }

    /** Termina con `part` completo y verificado, o lanza una excepción (y conserva `part` si se puede reanudar). */
    fun download(
        part: File,
        expectedHash: String,
        expectedSize: Long,
        open: (offset: Long) -> RemoteFile,
        onBytes: (written: Long) -> Unit = {},
        isCancelled: () -> Boolean = { false },
    ) {
        part.parentFile?.mkdirs()
        if (part.exists() && part.length() > expectedSize) part.delete()
        if (!part.exists() || part.length() < expectedSize) {
            fetch(part, expectedHash, open, onBytes, isCancelled, allowRestart = true)
        }
        if (part.length() != expectedSize) {
            throw IOException("Descarga incompleta (${part.length()} de $expectedSize bytes); se puede reanudar")
        }
        val actual = Sha256.of(part)
        if (!actual.equals(expectedHash, ignoreCase = true)) {
            part.delete()
            throw HashMismatchException("El archivo llegó dañado (SHA-256 distinto del catálogo); se descartó")
        }
        onBytes(expectedSize)
    }

    private fun fetch(
        part: File,
        expectedHash: String,
        open: (Long) -> RemoteFile,
        onBytes: (Long) -> Unit,
        isCancelled: () -> Boolean,
        allowRestart: Boolean,
    ) {
        val start = if (part.exists()) part.length() else 0L
        open(start).use { remote ->
            val serverHash = remote.hash
            if (serverHash != null && !serverHash.equals(expectedHash, ignoreCase = true)) {
                throw ChangedOnDesktopException("El archivo cambió en el escritorio: sincroniza el catálogo y vuelve a intentarlo")
            }
            val append: Boolean
            when (remote.status) {
                200 -> append = false   // el servidor ignoró el rango: se empieza de cero
                206 -> {
                    if (rangeStart(remote.contentRange) != start) {
                        if (!allowRestart) throw IOException("El escritorio no respetó el rango pedido")
                        part.delete()
                        fetch(part, expectedHash, open, onBytes, isCancelled, allowRestart = false)
                        return
                    }
                    append = true
                }
                else -> throw IOException("El escritorio respondió HTTP ${remote.status}")
            }
            val body = remote.body ?: throw IOException("Respuesta sin contenido")
            var written = if (append) start else 0L
            FileOutputStream(part, append).use { out ->
                val buffer = ByteArray(1 shl 16)
                while (true) {
                    if (isCancelled()) throw InterruptedIOException("Descarga cancelada")
                    val n = body.read(buffer)
                    if (n < 0) break
                    out.write(buffer, 0, n)
                    written += n
                    onBytes(written)
                }
            }
        }
    }
}
