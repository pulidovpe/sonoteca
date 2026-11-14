package io.github.pulidovpe.sonoteca

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import io.github.pulidovpe.sonoteca.db.AppDatabase
import io.github.pulidovpe.sonoteca.net.SyncHttpException
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import java.net.ConnectException
import java.net.SocketTimeoutException
import java.net.UnknownHostException
import javax.net.ssl.SSLException

class MainViewModel(app: Application) : AndroidViewModel(app) {
    private val store = PairingStore(app)
    private val repository = SyncRepository(AppDatabase.get(app), store)

    val pairing = MutableStateFlow(store.load())
    val busy = MutableStateFlow(false)
    val message = MutableStateFlow<String?>(null)

    val artists = repository.artists.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())
    val trackCount = repository.trackCount.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), 0)
    val playlistCount = repository.playlistCount.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), 0)

    fun pair(url: String, deviceName: String) = launchBusy {
        val paired = repository.pair(url, deviceName)
        pairing.value = paired
        "Emparejado con ${paired.host}:${paired.port}."
    }

    fun sync() {
        val current = pairing.value ?: return
        launchBusy { repository.sync(current) }
    }

    fun unpair() {
        repository.unpair()
        pairing.value = null
        message.value = "Emparejamiento olvidado. Los datos descargados se conservan."
    }

    fun dismissMessage() {
        message.value = null
    }

    private fun launchBusy(block: suspend () -> String) {
        if (busy.value) return
        viewModelScope.launch {
            busy.value = true
            message.value = try {
                block()
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                friendly(e)
            } finally {
                busy.value = false
            }
        }
    }

    private fun friendly(e: Exception): String = when (e) {
        is SyncHttpException -> when (e.status) {
            401 -> "El escritorio no reconoce este móvil. Vuelve a emparejar."
            403 -> "Código de emparejamiento incorrecto o caducado. Genera uno nuevo (Intro en el escritorio)."
            else -> "El escritorio respondió: ${e.message}"
        }
        is SSLException -> "No se pudo establecer una conexión segura: la huella del certificado no coincide " +
            "(¿emparejaste con otro equipo?). Detalle: ${e.message}"
        is ConnectException -> "No se pudo conectar. ¿Está corriendo `sonoteca sync-serve`? " +
            "Por USB, ¿ejecutaste `adb reverse`? Por Wi-Fi, ¿están en la misma red?"
        is SocketTimeoutException -> "El escritorio tardó demasiado en responder."
        is UnknownHostException -> "No se encuentra el equipo ${(e.message ?: "")}. Revisa la dirección."
        is IllegalArgumentException -> e.message ?: "Datos inválidos."
        else -> "Error inesperado: ${e.javaClass.simpleName}: ${e.message}"
    }
}
