package io.github.pulidovpe.sonoteca.net

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test
import java.io.ByteArrayInputStream
import java.security.cert.CertificateException
import java.security.cert.CertificateFactory
import java.security.cert.X509Certificate

/** El certificado y su huella los generó el servidor real (sync/tls.py): el cálculo debe coincidir byte a byte. */
class PinnedTlsTest {
    private val pem = """
-----BEGIN CERTIFICATE-----
MIIBJjCBzKADAgECAhQWs/tk1qg32763d7uaBdpWF7sTMDAKBggqhkjOPQQDAjAT
MREwDwYDVQQDDAhTb25vdGVjYTAeFw0yNjExMTIwMDU5NDdaFw0zNjExMTAwMDU5
NDdaMBMxETAPBgNVBAMMCFNvbm90ZWNhMFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcD
QgAEMAjXIgsTQhBmQF+WWmqvG1jOij99zcBRfE4L9J2NIH1f699FsXvYP04+rOzz
SYGl0V/Wn13nusxtmBtLmzaiLjAKBggqhkjOPQQDAgNJADBGAiEAwqTBjcQIuPNk
W0d7VRevMa/qemVd44JxgMcv0xi060MCIQDj8GjFT/CXAYwaM8pkCrVd+hY65PqW
kv+e0y2lVlTNiQ==
-----END CERTIFICATE-----
""".trimIndent()
    private val expected = "d8f62818f297773b6d032c868531588cd7f3d969df8d8b420eb79964405d4bba"

    private fun cert(): X509Certificate =
        CertificateFactory.getInstance("X.509").generateCertificate(ByteArrayInputStream(pem.toByteArray())) as X509Certificate

    @Test
    fun fingerprintMatchesTheOneComputedByTheDesktop() {
        assertEquals(expected, PinnedTls.fingerprintOf(cert()))
    }

    @Test
    fun trustManagerAcceptsExactlyThePinnedCertificate() {
        PinnedTls.PinnedTrustManager(expected).checkServerTrusted(arrayOf(cert()), "ECDHE_ECDSA")
        PinnedTls.PinnedTrustManager(expected.uppercase()).checkServerTrusted(arrayOf(cert()), "ECDHE_ECDSA")
    }

    @Test
    fun trustManagerRejectsAnyOtherFingerprint() {
        val other = "0".repeat(64)
        assertThrows(CertificateException::class.java) {
            PinnedTls.PinnedTrustManager(other).checkServerTrusted(arrayOf(cert()), "ECDHE_ECDSA")
        }
    }

    @Test
    fun trustManagerRejectsEmptyChainAndClientCertificates() {
        val manager = PinnedTls.PinnedTrustManager(expected)
        assertThrows(CertificateException::class.java) { manager.checkServerTrusted(emptyArray<X509Certificate>(), "x") }
        assertThrows(CertificateException::class.java) { manager.checkServerTrusted(null, "x") }
        assertThrows(CertificateException::class.java) { manager.checkClientTrusted(arrayOf(cert()), "x") }
    }
}
