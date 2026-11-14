package io.github.pulidovpe.sonoteca.net

import java.security.MessageDigest
import java.security.cert.CertificateException
import java.security.cert.X509Certificate
import javax.net.ssl.SSLContext
import javax.net.ssl.SSLSocketFactory
import javax.net.ssl.TrustManager
import javax.net.ssl.X509TrustManager

/**
 * TLS con certificado «fijado»: el servidor de Sonoteca usa un certificado autofirmado, así que no se valida contra
 * autoridades sino contra la huella SHA-256 del certificado, recibida al emparejar. Quien no presente exactamente ese
 * certificado es rechazado (también se rechaza un servidor «legítimo» con otro certificado).
 */
object PinnedTls {
    fun normalize(fingerprint: String): String = fingerprint.lowercase().replace(":", "")

    fun fingerprintOf(cert: X509Certificate): String =
        MessageDigest.getInstance("SHA-256").digest(cert.encoded).joinToString("") { "%02x".format(it) }

    class PinnedTrustManager(expected: String) : X509TrustManager {
        private val expectedBytes = normalize(expected).toByteArray(Charsets.US_ASCII)

        override fun checkClientTrusted(chain: Array<out X509Certificate>?, authType: String?) {
            throw CertificateException("No se aceptan certificados de cliente")
        }

        override fun checkServerTrusted(chain: Array<out X509Certificate>?, authType: String?) {
            if (chain.isNullOrEmpty()) throw CertificateException("El servidor no presentó certificado")
            val actual = fingerprintOf(chain[0])
            // comparación de tiempo constante
            if (!MessageDigest.isEqual(actual.toByteArray(Charsets.US_ASCII), expectedBytes)) {
                throw CertificateException("La huella del certificado no coincide (recibida $actual)")
            }
        }

        override fun getAcceptedIssuers(): Array<X509Certificate> = emptyArray()
    }

    fun socketFactory(expectedFingerprint: String): SSLSocketFactory {
        val context = SSLContext.getInstance("TLS")
        context.init(null, arrayOf<TrustManager>(PinnedTrustManager(expectedFingerprint)), null)
        return context.socketFactory
    }
}
