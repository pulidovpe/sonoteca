package io.github.pulidovpe.sonoteca

import android.content.Context
import java.util.UUID

/** Escritorio con el que se emparejó este móvil. El token es secreto: queda en el almacenamiento privado de la app. */
data class Pairing(val host: String, val port: Int, val fingerprint: String, val token: String)

class PairingStore(context: Context) {
    private val prefs = context.applicationContext.getSharedPreferences("pairing", Context.MODE_PRIVATE)

    /** Identificador estable de este móvil ante el escritorio (se crea la primera vez). */
    fun deviceId(): String =
        prefs.getString("device_id", null) ?: UUID.randomUUID().toString().also {
            prefs.edit().putString("device_id", it).apply()
        }

    fun load(): Pairing? {
        val host = prefs.getString("host", null) ?: return null
        val fp = prefs.getString("fp", null) ?: return null
        val token = prefs.getString("token", null) ?: return null
        return Pairing(host, prefs.getInt("port", 0), fp, token)
    }

    fun save(pairing: Pairing) {
        prefs.edit()
            .putString("host", pairing.host).putInt("port", pairing.port)
            .putString("fp", pairing.fingerprint).putString("token", pairing.token)
            .apply()
    }

    fun clear() {
        prefs.edit().remove("host").remove("port").remove("fp").remove("token").apply()
    }
}
