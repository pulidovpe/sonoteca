package io.github.pulidovpe.sonoteca.ui

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assume.assumeTrue
import org.junit.Test

class CollageLayoutTest {
    @Test
    fun noAlbumsMeansNoTilesAndMoreThanFourAreCutToFour() {
        assertEquals(0, CollageLayout.tiles(0).size)
        assertEquals(1, CollageLayout.tiles(1).size)
        assertEquals(2, CollageLayout.tiles(2).size)
        assertEquals(3, CollageLayout.tiles(3).size)
        assertEquals(4, CollageLayout.tiles(4).size)
        assertEquals(4, CollageLayout.tiles(9).size)
        assertEquals(0, CollageLayout.tiles(-1).size)
    }

    @Test
    fun theTilesCoverTheWholeSquareWithoutOverlapping() {
        for (count in 1..4) {
            val area = CollageLayout.tiles(count).sumOf { (it.w * it.h).toDouble() }
            assertEquals("área con $count álbumes", 1.0, area, 1e-6)
        }
    }

    /** El reparto del móvil debe ser el de `PlaylistCover.qml` del escritorio (si el archivo no está a mano, se omite). */
    @Test
    fun theLayoutMatchesTheDesktopPlaylistCover() {
        val file = listOf("../../src/sonoteca/ui/qml/PlaylistCover.qml", "../src/sonoteca/ui/qml/PlaylistCover.qml", "src/sonoteca/ui/qml/PlaylistCover.qml")
            .map { File(it) }.firstOrNull { it.isFile }
        assumeTrue("PlaylistCover.qml no está accesible desde las pruebas", file != null)
        val text = file!!.readText(Charsets.UTF_8)
        val tile = Regex("""\{ x: ([\d.]+), y: ([\d.]+), w: ([\d.]+), h: ([\d.]+) \}""")
        var checked = 0
        for (count in 1..4) {
            val block = Regex("""if \(n === $count\) return \[([^\]]*)\]""").find(text)?.groupValues?.get(1) ?: error("falta n === $count en PlaylistCover.qml")
            val desktop = tile.findAll(block).map { m -> m.groupValues.drop(1).map { it.toFloat() } }.toList()
            val mobile = CollageLayout.tiles(count).map { listOf(it.x, it.y, it.w, it.h) }
            assertEquals("reparto con $count álbumes", desktop, mobile)
            checked++
        }
        assertEquals(4, checked)
    }
}
