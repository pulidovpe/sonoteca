package io.github.pulidovpe.sonoteca.playback

import android.content.ComponentName
import android.content.Context
import android.net.Uri
import androidx.core.content.ContextCompat
import androidx.media3.common.MediaItem
import androidx.media3.common.MediaMetadata
import androidx.media3.common.PlaybackException
import androidx.media3.common.Player
import androidx.media3.session.MediaController
import androidx.media3.session.SessionToken
import com.google.common.util.concurrent.ListenableFuture
import io.github.pulidovpe.sonoteca.db.PlayableTrack
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

/** Lo que la interfaz necesita saber del reproductor. */
data class PlayerUi(
    val hasItem: Boolean = false,
    val title: String = "",
    val artist: String = "",
    val isPlaying: Boolean = false,
    val positionMs: Long = 0,
    val durationMs: Long = 0,
    val hasNext: Boolean = false,
    val shuffle: Boolean = false,
    val repeatMode: Int = PlaybackModes.REPEAT_OFF,
    val queue: List<QueueItem> = emptyList(),
    val currentIndex: Int = -1,
    val error: String? = null,
)

/** Una pista de la cola de reproducción (id = UUID de la pista). */
data class QueueItem(val uuid: String, val title: String, val artist: String)

/**
 * Habla con [PlaybackService] mediante un MediaController. Todo se llama desde el hilo principal.
 * Si se pide reproducir antes de que la conexión esté lista, la petición queda pendiente y se ejecuta al conectar.
 */
class PlayerController(private val context: Context) {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
    private var future: ListenableFuture<MediaController>? = null
    private var controller: MediaController? = null
    private var pending: PlaybackQueue.Window? = null
    private var ticker: Job? = null
    private val prefs = context.getSharedPreferences("player", Context.MODE_PRIVATE)
    private val mutableState = MutableStateFlow(PlayerUi())

    val state: StateFlow<PlayerUi> = mutableState.asStateFlow()

    private val listener = object : Player.Listener {
        override fun onEvents(player: Player, events: Player.Events) = refresh(player)

        override fun onMediaItemTransition(mediaItem: MediaItem?, reason: Int) {
            mutableState.update { it.copy(error = null) }
        }

        override fun onPlayerError(error: PlaybackException) {
            mutableState.update { it.copy(error = "No se puede reproducir: ${error.message ?: error.errorCodeName}") }
        }
    }

    fun connect() {
        if (future != null) return
        val token = SessionToken(context, ComponentName(context, PlaybackService::class.java))
        val request = MediaController.Builder(context, token).buildAsync()
        future = request
        request.addListener({
            try {
                val connected = request.get()
                controller = connected
                connected.addListener(listener)
                if (connected.mediaItemCount == 0) {   // servicio recién creado: se recuperan aleatorio y repetir de la última vez
                    connected.shuffleModeEnabled = prefs.getBoolean(KEY_SHUFFLE, false)
                    connected.repeatMode = prefs.getInt(KEY_REPEAT, PlaybackModes.REPEAT_OFF)
                }
                refresh(connected)
                pending?.let { queued ->
                    pending = null
                    start(connected, queued)
                }
            } catch (e: Exception) {
                mutableState.update { it.copy(error = "No se pudo conectar con el reproductor.") }
            }
        }, ContextCompat.getMainExecutor(context))
        ticker = scope.launch {
            while (isActive) {
                delay(POSITION_POLL_MS)
                val current = controller
                if (current != null && current.isPlaying) {
                    mutableState.update { it.copy(positionMs = current.currentPosition.coerceAtLeast(0)) }
                }
            }
        }
    }

    /** Reproduce `tracks` empezando por `startIndex` (la cola se recorta a [PlaybackQueue.MAX_ITEMS] pistas alrededor de esa). */
    fun play(tracks: List<PlayableTrack>, startIndex: Int) {
        val window = PlaybackQueue.window(tracks, startIndex)
        if (window.tracks.isEmpty()) return
        val connected = controller
        if (connected == null) {
            pending = window
            connect()
        } else {
            start(connected, window)
        }
    }

    /** «Reproducir a continuación»: justo detrás de la pista que suena (si no suena nada, empieza a reproducir). */
    fun playNext(tracks: List<PlayableTrack>) {
        val connected = controller
        if (connected == null || connected.mediaItemCount == 0) {
            play(tracks, 0)
        } else if (tracks.isNotEmpty()) {
            connected.addMediaItems(connected.currentMediaItemIndex + 1, tracks.take(PlaybackQueue.MAX_ITEMS).map(::mediaItemOf))
        }
    }

    /** «Agregar al final de la cola» (si no suena nada, empieza a reproducir). */
    fun addToEnd(tracks: List<PlayableTrack>) {
        val connected = controller
        if (connected == null || connected.mediaItemCount == 0) {
            play(tracks, 0)
        } else if (tracks.isNotEmpty()) {
            connected.addMediaItems(tracks.take(PlaybackQueue.MAX_ITEMS).map(::mediaItemOf))
        }
    }

    /** Salta a la pista `index` de la cola y la reproduce. */
    fun jumpTo(index: Int) {
        val connected = controller ?: return
        if (index in 0 until connected.mediaItemCount) {
            connected.seekToDefaultPosition(index)
            connected.play()
        }
    }

    fun removeAt(index: Int) {
        val connected = controller ?: return
        if (index in 0 until connected.mediaItemCount && index != connected.currentMediaItemIndex) connected.removeMediaItem(index)
    }

    /** «Vaciar»: quita todo MENOS la pista que suena (como en el escritorio). */
    fun clearQueue() {
        val connected = controller ?: return
        val current = connected.currentMediaItemIndex
        if (current < connected.mediaItemCount - 1) connected.removeMediaItems(current + 1, connected.mediaItemCount)
        if (current > 0) connected.removeMediaItems(0, current)
    }

    fun toggleShuffle() {
        val connected = controller ?: return
        val enabled = !connected.shuffleModeEnabled
        connected.shuffleModeEnabled = enabled
        prefs.edit().putBoolean(KEY_SHUFFLE, enabled).apply()
    }

    /** Sin repetir → todas → una → sin repetir. */
    fun cycleRepeat() {
        val connected = controller ?: return
        val next = PlaybackModes.nextRepeat(connected.repeatMode)
        connected.repeatMode = next
        prefs.edit().putInt(KEY_REPEAT, next).apply()
    }

    fun togglePlay() {
        val current = controller ?: return
        if (current.isPlaying) {
            current.pause()
        } else {
            if (current.playbackState == Player.STATE_ENDED) current.seekToDefaultPosition(0)
            current.play()
        }
    }

    fun next() {
        controller?.seekToNext()
    }

    fun previous() {
        controller?.seekToPrevious()
    }

    fun seekTo(positionMs: Long) {
        controller?.seekTo(positionMs)
    }

    fun release() {
        ticker?.cancel()
        controller?.removeListener(listener)
        controller = null
        future?.let { MediaController.releaseFuture(it) }
        future = null
        scope.cancel()
    }

    private fun start(connected: MediaController, window: PlaybackQueue.Window) {
        val items = window.tracks.map(::mediaItemOf)
        mutableState.update { it.copy(error = null) }
        connected.setMediaItems(items, window.startIndex, 0L)
        connected.prepare()
        connected.play()
    }

    private fun mediaItemOf(track: PlayableTrack): MediaItem {
        val uri = Uri.parse(track.uri)
        return MediaItem.Builder()
            .setMediaId(track.uuid)
            .setUri(uri)
            .setRequestMetadata(MediaItem.RequestMetadata.Builder().setMediaUri(uri).build())
            .setMediaMetadata(
                MediaMetadata.Builder()
                    .setTitle(track.title)
                    .setArtist(track.artist.ifEmpty { track.albumArtist })
                    .setAlbumTitle(track.album)
                    .build(),
            )
            .build()
    }

    private fun refresh(player: Player) {
        mutableState.update { old ->
            old.copy(
                hasItem = player.mediaItemCount > 0,
                title = player.mediaMetadata.title?.toString().orEmpty(),
                artist = player.mediaMetadata.artist?.toString().orEmpty(),
                isPlaying = player.isPlaying,
                positionMs = player.currentPosition.coerceAtLeast(0),
                durationMs = player.duration.coerceAtLeast(0),   // C.TIME_UNSET es negativo
                hasNext = player.hasNextMediaItem(),
                shuffle = player.shuffleModeEnabled,
                repeatMode = player.repeatMode,
                queue = (0 until player.mediaItemCount).map { index ->
                    val item = player.getMediaItemAt(index)
                    QueueItem(item.mediaId, item.mediaMetadata.title?.toString().orEmpty(), item.mediaMetadata.artist?.toString().orEmpty())
                },
                currentIndex = if (player.mediaItemCount > 0) player.currentMediaItemIndex else -1,
            )
        }
    }

    private companion object {
        const val POSITION_POLL_MS = 500L
        const val KEY_SHUFFLE = "shuffle"
        const val KEY_REPEAT = "repeat"
    }
}
