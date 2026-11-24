package io.github.pulidovpe.sonoteca.download

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class DownloadStateTest {
    @Test
    fun onlyAFullyDownloadedItemIsComplete() {
        assertTrue(DownloadState.isComplete(12, 12))
        assertFalse(DownloadState.isComplete(12, 3))    // a medias: en gris
        assertFalse(DownloadState.isComplete(12, 0))
        assertFalse(DownloadState.isComplete(0, 0))     // vacío: nunca «completo»
    }

    @Test
    fun anItemWithAnyDownloadedTrackAppearsInDownloaded() {
        assertTrue(DownloadState.hasAny(1))
        assertTrue(DownloadState.hasAny(12))
        assertFalse(DownloadState.hasAny(0))
    }
}
