package io.github.pulidovpe.sonoteca

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import io.github.pulidovpe.sonoteca.db.AppDatabase
import io.github.pulidovpe.sonoteca.download.DownloadPlan
import io.github.pulidovpe.sonoteca.download.DownloadProgress
import io.github.pulidovpe.sonoteca.net.SyncHttpException
import io.github.pulidovpe.sonoteca.playback.PlayerController
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import java.io.IOException
import java.net.ConnectException
import java.net.SocketTimeoutException
import java.net.UnknownHostException
import javax.net.ssl.SSLException

class MainViewModel(app: Application) : AndroidViewModel(app) {
    private val store = PairingStore(app)
    private val repository = SyncRepository(app, AppDatabase.get(app), store)

    val pairing = MutableStateFlow(store.load())
    val busy = MutableStateFlow(false)
    val message = MutableStateFlow<String?>(null)

    /** Selección pendiente de confirmar (resumen antes de descargar) y progreso de la descarga en curso. */
    val plan = MutableStateFlow<DownloadPlan?>(null)
    val progress = MutableStateFlow<DownloadProgress?>(null)
    val deleteAsk = MutableStateFlow<DeleteAsk?>(null)
    private var planSelection: Selection? = null
    private var downloadJob: Job? = null

    val artists = repository.artists.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())
    val trackCount = repository.trackCount.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), 0)
    val playlistCount = repository.playlistCount.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), 0)
    val albums = repository.albums.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())
    val playlistRows = repository.playlistRows.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    /** Reproductor local (fase 4a): toca lo descargado en el teléfono, sin servidor ni cable. */
    val player = PlayerController(app)
    val playerState = player.state
    val playable = repository.playable.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    /** Reproducciones anotadas en el teléfono que aún no se han subido al escritorio. */
    val pendingPlays = repository.pendingPlays.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), 0)

    init {
        player.connect()
        uploadPlaysQuietly()
    }

    /** Al abrir la app, si el escritorio está al alcance, sube las reproducciones pendientes sin molestar; si no, se reintenta luego. */
    private fun uploadPlaysQuietly() {
        val current = pairing.value ?: return
        viewModelScope.launch {
            try {
                repository.uploadPlays(current)
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                // sin escritorio al alcance (sin cable ni Wi-Fi): es lo normal; las reproducciones siguen guardadas
            }
        }
    }

    /** Toca la lista «Descargado» entera empezando por la pista `index`. */
    fun playFromList(index: Int) {
        val list = playable.value
        if (index in list.indices) player.play(list, index)
    }

    /** Toca lo ya descargado de la selección del diálogo (artista, álbum o lista). */
    fun playSelection() {
        val selection = planSelection ?: return
        plan.value = null
        viewModelScope.launch {
            try {
                val tracks = repository.playableOf(selection)
                if (tracks.isEmpty()) message.value = "No hay pistas descargadas de «${selection.label}»." else player.play(tracks, 0)
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                message.value = friendly(e)
            }
        }
    }

    /** Desde la pestaña «Descargado»: una pista a continuación de la que suena, o al final de la cola. */
    fun queueTrack(index: Int, next: Boolean) {
        val track = playable.value.getOrNull(index) ?: return
        if (next) player.playNext(listOf(track)) else player.addToEnd(listOf(track))
        message.value = if (next) "«${track.title}» sonará a continuación." else "«${track.title}» se agregó al final de la cola."
    }

    /** Lo ya descargado de la selección del diálogo, a continuación o al final de la cola. */
    fun queueSelection(next: Boolean) {
        val selection = planSelection ?: return
        plan.value = null
        viewModelScope.launch {
            try {
                val tracks = repository.playableOf(selection)
                if (tracks.isEmpty()) {
                    message.value = "No hay pistas descargadas de «${selection.label}»."
                } else {
                    if (next) player.playNext(tracks) else player.addToEnd(tracks)
                    message.value = "${tracks.size} pistas de «${selection.label}» " + if (next) "sonarán a continuación." else "se agregaron al final de la cola."
                }
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                message.value = friendly(e)
            }
        }
    }

    override fun onCleared() {
        player.release()
    }

    fun pair(url: String, deviceName: String) = launchBusy {
        val paired = repository.pair(url, deviceName)
        pairing.value = paired
        val head = "Emparejado con ${paired.host}:${paired.port}."
        // El catálogo guardado puede ser de otro escritorio (otros UUID): se renueva al emparejar para que las descargas no den «pista desconocida».
        try {
            "$head ${repository.sync(paired)}"
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            "$head No se pudo sincronizar el catálogo: ${friendly(e)} Pulsa «Sincronizar catálogo» para reintentar."
        }
    }

    fun sync() {
        val current = pairing.value ?: return
        launchBusy { repository.sync(current) }
    }

    fun choose(selection: Selection) {
        if (busy.value) return
        viewModelScope.launch {
            try {
                planSelection = selection
                plan.value = repository.plan(selection)
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                message.value = friendly(e)
            }
        }
    }

    fun dismissPlan() {
        plan.value = null
    }

    /** Pasa del resumen a la confirmación de borrado (solo si hay algo descargado de esa selección). */
    fun askDelete() {
        val current = plan.value ?: return
        val selection = planSelection ?: return
        if (current.onPhone <= 0) return
        plan.value = null
        deleteAsk.value = DeleteAsk(selection, current.onPhone)
    }

    fun dismissDelete() {
        deleteAsk.value = null
    }

    fun confirmDelete() {
        val ask = deleteAsk.value ?: return
        deleteAsk.value = null
        if (busy.value) return
        viewModelScope.launch {
            busy.value = true
            try {
                val (deleted, failed) = repository.deleteDownloads(ask.selection)
                message.value = "Borradas $deleted pistas del teléfono." + if (failed > 0) " No se pudieron borrar $failed." else ""
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                message.value = friendly(e)
            } finally {
                busy.value = false
            }
        }
    }

    fun startDownload() {
        val chosen = plan.value ?: return
        val paired = pairing.value ?: return
        if (busy.value) return
        plan.value = null
        downloadJob = viewModelScope.launch {
            busy.value = true
            try {
                message.value = repository.download(paired, chosen) { progress.value = it }.text()
            } catch (e: CancellationException) {
                message.value = "Descarga cancelada. Lo ya descargado se conserva y puedes reanudar."
                throw e
            } catch (e: Exception) {
                message.value = friendly(e)
            } finally {
                progress.value = null
                busy.value = false
            }
        }
    }

    fun cancelDownload() {
        downloadJob?.cancel()
    }

    fun unpair() {
        repository.unpair()
        pairing.value = null
        message.value = "Emparejamiento olvidado. Se conservan el catálogo y lo descargado; el catálogo se renueva al emparejar de nuevo."
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
        is SSLException -> "El certificado del escritorio no es el que se fijó al emparejar. Pasa si el servidor usa otra " +
            "carpeta de datos, se borró su carpeta «sync» o es otro equipo. Si es tu escritorio: pulsa «Olvidar» y " +
            "empareja de nuevo con la URL que muestra ahora el servidor. Detalle: ${e.message}"
        is ConnectException -> "No se pudo conectar. ¿Está corriendo `sonoteca sync-serve`? " +
            "Por USB, ¿ejecutaste `adb reverse`? Por Wi-Fi, ¿están en la misma red?"
        is SocketTimeoutException -> "El escritorio tardó demasiado en responder."
        is UnknownHostException -> "No se encuentra el equipo ${(e.message ?: "")}. Revisa la dirección."
        is IOException -> "Se cortó la conexión con el escritorio. Mira la consola de `sonoteca sync-serve`: " +
            "si hubo un error interno, ahí está la traza. Detalle: ${e.message}"
        is IllegalArgumentException -> e.message ?: "Datos inválidos."
        else -> "Error inesperado: ${e.javaClass.simpleName}: ${e.message}"
    }
}
