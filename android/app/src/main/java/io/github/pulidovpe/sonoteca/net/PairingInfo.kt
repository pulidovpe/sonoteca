package io.github.pulidovpe.sonoteca.net

import java.net.URI
import java.net.URLDecoder

/**
 * Datos de emparejamiento: la URL que muestra `sonoteca sync-serve`,
 * `sonoteca-sync://pair?host=<h>&port=<p>&fp=<sha256-hex>&code=<6 dígitos>`.
 * Lógica pura (sin clases de Android) para poder probarla en la JVM.
 */
data class PairingInfo(val host: String, val port: Int, val fingerprint: String, val code: String) {
    companion object {
        private val HEX64 = Regex("^[0-9a-f]{64}$")
        private val CODE = Regex("^[0-9]{6}$")

        /** Devuelve null si el texto no es una URL de emparejamiento válida. */
        fun parse(text: String): PairingInfo? {
            val uri = try {
                URI(text.trim())
            } catch (e: Exception) {
                return null
            }
            if (uri.scheme != "sonoteca-sync" || uri.host != "pair") return null
            val query = uri.rawQuery ?: return null
            val params = HashMap<String, String>()
            for (part in query.split('&')) {
                val eq = part.indexOf('=')
                if (eq <= 0) continue
                params[part.substring(0, eq)] = URLDecoder.decode(part.substring(eq + 1), "UTF-8")
            }
            val host = params["host"]?.trim().orEmpty()
            val port = params["port"]?.toIntOrNull() ?: return null
            val fingerprint = params["fp"]?.lowercase()?.replace(":", "").orEmpty()
            val code = params["code"].orEmpty()
            if (host.isEmpty() || port !in 1..65535) return null
            if (!HEX64.matches(fingerprint) || !CODE.matches(code)) return null
            return PairingInfo(host, port, fingerprint, code)
        }
    }
}
