package io.github.pulidovpe.sonoteca.download

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import java.io.ByteArrayInputStream
import java.io.File
import java.io.IOException
import java.io.InterruptedIOException

/** Servidor falso: sirve `content` respetando (o no) el rango pedido, como el escritorio real (`sync/server.py`). */
private class FakeServer(
    private val content: ByteArray,
    private val hashHeader: String? = Sha256.of(content),
    private val honorRange: Boolean = true,
    private val rangeStartLie: Long? = null,
    private val truncateAt: Int? = null,
) {
    val offsets = mutableListOf<Long>()

    fun open(offset: Long): RemoteFile {
        offsets += offset
        val partial = honorRange && offset > 0
        val from = if (partial) offset.toInt() else 0
        var body = content.copyOfRange(from, content.size)
        if (truncateAt != null) body = body.copyOfRange(0, minOf(truncateAt, body.size))
        val range = if (partial) "bytes ${rangeStartLie ?: offset}-${content.size - 1}/${content.size}" else null
        return RemoteFile(if (partial) 206 else 200, range, hashHeader, ByteArrayInputStream(body))
    }
}

class FileDownloaderTest {
    @get:Rule
    val tmp = TemporaryFolder()

    private val content = ByteArray(300_000) { (it * 31 % 251).toByte() }
    private val hash = Sha256.of(content)

    private fun part(): File = File(tmp.root, "x.part")

    @Test
    fun fullDownloadIsVerifiedAndProgressReachesTheEnd() {
        val server = FakeServer(content)
        var last = 0L
        FileDownloader.download(part(), hash, content.size.toLong(), server::open, onBytes = { last = it })
        assertArrayEquals(content, part().readBytes())
        assertEquals(content.size.toLong(), last)
        assertEquals(listOf(0L), server.offsets)
    }

    @Test
    fun resumesFromTheExistingPartialFile() {
        part().writeBytes(content.copyOfRange(0, 120_000))
        val server = FakeServer(content)
        FileDownloader.download(part(), hash, content.size.toLong(), server::open)
        assertArrayEquals(content, part().readBytes())
        assertEquals(listOf(120_000L), server.offsets)   // pidió solo lo que faltaba
    }

    @Test
    fun serverIgnoringRangeRestartsFromZeroWithoutCorruptingTheFile() {
        part().writeBytes(content.copyOfRange(0, 50_000))
        val server = FakeServer(content, honorRange = false)
        FileDownloader.download(part(), hash, content.size.toLong(), server::open)
        assertArrayEquals(content, part().readBytes())
    }

    @Test
    fun wrongContentRangeRestartsOnceFromZero() {
        part().writeBytes(content.copyOfRange(0, 50_000))
        // la primera respuesta miente en el inicio del rango; el reintento desde cero (sin rango) llega bien
        val server = FakeServer(content, rangeStartLie = 7)
        FileDownloader.download(part(), hash, content.size.toLong(), server::open)
        assertArrayEquals(content, part().readBytes())
        assertEquals(listOf(50_000L, 0L), server.offsets)
    }

    @Test
    fun hashHeaderDifferentFromTheCatalogMeansChangedOnDesktop() {
        val server = FakeServer(content, hashHeader = "0".repeat(64))
        assertThrows(ChangedOnDesktopException::class.java) {
            FileDownloader.download(part(), hash, content.size.toLong(), server::open)
        }
    }

    @Test
    fun corruptedContentIsDiscarded() {
        val damaged = content.copyOf().also { it[1000] = (it[1000] + 1).toByte() }
        val server = FakeServer(damaged, hashHeader = hash)   // el servidor "promete" la huella buena pero manda bytes malos
        assertThrows(HashMismatchException::class.java) {
            FileDownloader.download(part(), hash, content.size.toLong(), server::open)
        }
        assertFalse(part().exists())   // no queda un archivo corrupto para reanudar
    }

    @Test
    fun incompleteBodyKeepsThePartialFileForResuming() {
        val server = FakeServer(content, truncateAt = 80_000)
        assertThrows(IOException::class.java) {
            FileDownloader.download(part(), hash, content.size.toLong(), server::open)
        }
        assertEquals(80_000L, part().length())
        // al reintentar con un servidor sano, continúa desde 80 000
        val healthy = FakeServer(content)
        FileDownloader.download(part(), hash, content.size.toLong(), healthy::open)
        assertEquals(listOf(80_000L), healthy.offsets)
        assertArrayEquals(content, part().readBytes())
    }

    @Test
    fun cancellationKeepsWhatWasWritten() {
        val server = FakeServer(content)
        var chunks = 0
        assertThrows(InterruptedIOException::class.java) {
            FileDownloader.download(part(), hash, content.size.toLong(), server::open, isCancelled = { ++chunks > 2 })
        }
        assertTrue(part().length() in 1 until content.size.toLong())
    }

    @Test
    fun httpErrorIsReported() {
        val failing: (Long) -> RemoteFile = { RemoteFile(500, null, null, null) }
        assertThrows(IOException::class.java) { FileDownloader.download(part(), hash, 10, failing) }
    }

    @Test
    fun rangeStartIsParsedFromContentRange() {
        assertEquals(100L, FileDownloader.rangeStart("bytes 100-199/1000"))
        assertEquals(null, FileDownloader.rangeStart(null))
        assertEquals(null, FileDownloader.rangeStart("garbage"))
    }
}
