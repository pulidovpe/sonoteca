package io.github.pulidovpe.sonoteca.ui

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Test

/** El tema del móvil debe seguir siendo el del escritorio: compara colores e iconos con `Theme.qml` (si el archivo no está a mano, se omite). */
class NeonParityTest {
    private fun qml(): String {
        val file = listOf("../../src/sonoteca/ui/qml/Theme.qml", "../src/sonoteca/ui/qml/Theme.qml", "src/sonoteca/ui/qml/Theme.qml")
            .map { File(it) }.firstOrNull { it.isFile }
        assumeTrue("Theme.qml no está accesible desde las pruebas", file != null)
        return file!!.readText(Charsets.UTF_8)
    }

    @Test
    fun colorsMatchTheDesktopTheme() {
        val text = qml()
        val desktop = Regex("""readonly property color (\w+):\s*"#([0-9a-fA-F]{6,8})"""").findAll(text)
            .associate { it.groupValues[1] to it.groupValues[2] }
        assertTrue(NeonPalette.tokens.isNotEmpty())
        for ((name, argb) in NeonPalette.tokens) {
            val hex = desktop[name] ?: error("«$name» ya no está en Theme.qml")
            val expected = if (hex.length == 6) 0xFF000000L or hex.toLong(16) else hex.toLong(16)
            assertEquals("color $name", expected, argb)
        }
    }

    @Test
    fun iconsMatchTheDesktopTheme() {
        val text = qml()
        val desktop = Regex("""readonly property string (icon\w+):\s*"([^"]*)"""").findAll(text)
            .associate { it.groupValues[1] to it.groupValues[2] }
        assertTrue(NeonIcons.all.isNotEmpty())
        for ((name, path) in NeonIcons.all) {
            assertEquals("icono $name", desktop[name] ?: error("«$name» ya no está en Theme.qml"), path)
        }
    }

    @Test
    fun everyIconIsAValidSvgPathMadeOfKnownCommands() {
        val allowed = Regex("""[MmLlHhVvCcAaZz0-9.,\-\s]+""")
        for ((name, path) in NeonIcons.all) assertTrue("trazo de $name", allowed.matches(path))
    }
}
