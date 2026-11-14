package io.github.pulidovpe.sonoteca.net

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Test

class PairingInfoTest {
    private val fp = "d8f62818f297773b6d032c868531588cd7f3d969df8d8b420eb79964405d4bba"
    private val valid = "sonoteca-sync://pair?host=192.168.1.20&port=8765&fp=$fp&code=123456"

    @Test
    fun parsesAValidUrl() {
        val info = PairingInfo.parse(valid)
        assertNotNull(info)
        assertEquals("192.168.1.20", info!!.host)
        assertEquals(8765, info.port)
        assertEquals(fp, info.fingerprint)
        assertEquals("123456", info.code)
    }

    @Test
    fun acceptsLocalhostForUsbAndSurroundingWhitespace() {
        val info = PairingInfo.parse("  sonoteca-sync://pair?host=localhost&port=8765&fp=$fp&code=000001\n")
        assertEquals("localhost", info?.host)
        assertEquals("000001", info?.code)
    }

    @Test
    fun normalizesFingerprintCaseAndColons() {
        val spaced = fp.uppercase().chunked(2).joinToString(":")
        val info = PairingInfo.parse("sonoteca-sync://pair?host=h&port=1&fp=$spaced&code=123456")
        assertEquals(fp, info?.fingerprint)
    }

    @Test
    fun rejectsInvalidInput() {
        assertNull(PairingInfo.parse(""))
        assertNull(PairingInfo.parse("https://pair?host=h&port=1&fp=$fp&code=123456"))
        assertNull(PairingInfo.parse("sonoteca-sync://otra?host=h&port=1&fp=$fp&code=123456"))
        assertNull(PairingInfo.parse("sonoteca-sync://pair?host=h&port=0&fp=$fp&code=123456"))
        assertNull(PairingInfo.parse("sonoteca-sync://pair?host=h&port=70000&fp=$fp&code=123456"))
        assertNull(PairingInfo.parse("sonoteca-sync://pair?host=h&port=1&fp=abcd&code=123456"))
        assertNull(PairingInfo.parse("sonoteca-sync://pair?host=h&port=1&fp=$fp&code=12345"))
        assertNull(PairingInfo.parse("sonoteca-sync://pair?host=h&port=1&fp=$fp"))
        assertNull(PairingInfo.parse("sonoteca-sync://pair?port=1&fp=$fp&code=123456"))
        assertNull(PairingInfo.parse("no es una url % con espacios"))
    }
}
