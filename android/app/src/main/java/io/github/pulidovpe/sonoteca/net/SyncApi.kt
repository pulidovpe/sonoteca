package io.github.pulidovpe.sonoteca.net

import org.json.JSONObject
import java.io.IOException
import java.net.URI
import javax.net.ssl.HostnameVerifier
import javax.net.ssl.HttpsURLConnection

/** Error devuelto por el servidor (código HTTP + mensaje del escritorio). */
class SyncHttpException(val status: Int, message: String) : IOException(message)

data class PairResult(val token: String, val fingerprint: String)

/**
 * Cliente del protocolo de docs/SYNC.md. Bloqueante: llamar siempre fuera del hilo principal.
 * La confianza se decide SOLO por la huella del certificado (no hay validación de nombre de host: por USB el host es
 * `localhost` y por Wi-Fi una IP).
 */
class SyncApi(
    private val host: String,
    private val port: Int,
    private val fingerprint: String,
    private val token: String? = null,
) {
    fun pair(deviceId: String, deviceName: String, code: String): PairResult {
        val body = JSONObject().put("code", code).put("device_id", deviceId).put("device_name", deviceName)
        val response = JSONObject(request("POST", "/v1/pair", body))
        return PairResult(response.getString("token"), response.getString("fingerprint"))
    }

    fun manifest(): Manifest = parseManifest(request("GET", "/v1/manifest", null))

    private fun open(method: String, path: String): HttpsURLConnection {
        val url = URI("https", null, host, port, path, null, null).toURL()
        val connection = url.openConnection() as HttpsURLConnection
        connection.sslSocketFactory = PinnedTls.socketFactory(fingerprint)
        connection.hostnameVerifier = HostnameVerifier { _, _ -> true }   // ver nota de la clase
        connection.requestMethod = method
        connection.connectTimeout = 10_000
        connection.readTimeout = 60_000
        token?.let { connection.setRequestProperty("Authorization", "Bearer $it") }
        return connection
    }

    private fun request(method: String, path: String, body: JSONObject?): String {
        val connection = open(method, path)
        try {
            if (body != null) {
                connection.doOutput = true
                connection.setRequestProperty("Content-Type", "application/json")
                connection.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
            }
            val status = connection.responseCode
            val stream = if (status in 200..299) connection.inputStream else connection.errorStream
            val text = stream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
            if (status !in 200..299) throw SyncHttpException(status, errorMessage(text, status))
            return text
        } finally {
            connection.disconnect()
        }
    }

    private fun errorMessage(text: String, status: Int): String =
        try {
            JSONObject(text).optString("error", "Error HTTP $status")
        } catch (e: Exception) {
            "Error HTTP $status"
        }
}
