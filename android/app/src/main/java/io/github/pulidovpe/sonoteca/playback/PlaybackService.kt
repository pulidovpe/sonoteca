package io.github.pulidovpe.sonoteca.playback

import android.content.Intent
import android.os.Handler
import android.os.Looper
import androidx.annotation.OptIn
import androidx.media3.common.AudioAttributes
import androidx.media3.common.C
import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import androidx.media3.common.util.UnstableApi
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.session.MediaSession
import androidx.media3.session.MediaSessionService
import com.google.common.util.concurrent.Futures
import com.google.common.util.concurrent.ListenableFuture
import io.github.pulidovpe.sonoteca.db.AppDatabase
import io.github.pulidovpe.sonoteca.db.PlayEventEntity
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import java.util.UUID

/**
 * Reproduce en segundo plano lo descargado en el teléfono (ExoPlayer + sesión de medios: notificación, pantalla de bloqueo, auriculares).
 * No usa red: solo abre entradas `content://media/…` que la app misma publicó con MediaStore.
 */
@OptIn(UnstableApi::class)
class PlaybackService : MediaSessionService() {
    private var mediaSession: MediaSession? = null

    // Estadísticas: se anota cada reproducción (a los 3 s de escucha) aquí, en el servicio, para que cuente aunque la app esté cerrada.
    private val handler = Handler(Looper.getMainLooper())
    private val ioScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val counter = PlayCounter { trackUuid -> recordPlay(trackUuid) }
    private val tick = object : Runnable {
        override fun run() {
            val player = mediaSession?.player ?: return
            if (player.isPlaying) counter.onPosition(player.currentPosition, player.duration.coerceAtLeast(0))
            handler.postDelayed(this, POSITION_TICK_MS)
        }
    }
    private val statsListener = object : Player.Listener {
        override fun onMediaItemTransition(mediaItem: MediaItem?, reason: Int) {
            counter.startItem(mediaItem?.mediaId?.takeIf { it.isNotEmpty() })
        }

        override fun onIsPlayingChanged(isPlaying: Boolean) {
            handler.removeCallbacks(tick)
            if (isPlaying) handler.post(tick)
        }
    }

    private fun recordPlay(trackUuid: String) {
        val event = PlayEventEntity(UUID.randomUUID().toString(), trackUuid, PlayEvents.timestamp(System.currentTimeMillis()))
        ioScope.launch { AppDatabase.get(applicationContext).library().insertPlay(event) }
    }

    override fun onCreate() {
        super.onCreate()
        val player = ExoPlayer.Builder(this)
            .setAudioAttributes(
                AudioAttributes.Builder().setUsage(C.USAGE_MEDIA).setContentType(C.AUDIO_CONTENT_TYPE_MUSIC).build(),
                true,   // gestiona el foco de audio: se pausa con una llamada y se cede a otras apps
            )
            .setHandleAudioBecomingNoisy(true)   // pausa al desconectar los auriculares
            .setWakeMode(C.WAKE_MODE_LOCAL)      // archivos locales: mantiene la CPU despierta con la pantalla apagada
            .build()
        player.addListener(statsListener)
        mediaSession = MediaSession.Builder(this, player).setCallback(ResolveFromRequestMetadata()).build()
    }

    override fun onGetSession(controllerInfo: MediaSession.ControllerInfo): MediaSession? = mediaSession

    /** Si el usuario cierra la app desde recientes: se detiene el servicio salvo que esté sonando. */
    override fun onTaskRemoved(rootIntent: Intent?) {
        val player = mediaSession?.player
        if (player == null || !player.playWhenReady || player.mediaItemCount == 0) stopSelf()
    }

    override fun onDestroy() {
        handler.removeCallbacksAndMessages(null)
        ioScope.cancel()
        mediaSession?.run {
            player.removeListener(statsListener)
            player.release()
            release()
        }
        mediaSession = null
        super.onDestroy()
    }

    private companion object {
        const val POSITION_TICK_MS = 500L
    }

    /**
     * Los clientes mandan las pistas con su URI en `requestMetadata`; aquí se convierten en pistas reproducibles, pero SOLO si son de
     * MediaStore (así otra app que se conecte a la sesión no puede hacer que se abra cualquier archivo o URL).
     */
    private class ResolveFromRequestMetadata : MediaSession.Callback {
        override fun onAddMediaItems(
            mediaSession: MediaSession,
            controller: MediaSession.ControllerInfo,
            mediaItems: MutableList<MediaItem>,
        ): ListenableFuture<MutableList<MediaItem>> {
            val playable = mediaItems.mapNotNull { item ->
                val uri = item.requestMetadata.mediaUri ?: item.localConfiguration?.uri
                if (uri != null && PlaybackQueue.isAllowedUri(uri.toString())) item.buildUpon().setUri(uri).build() else null
            }.toMutableList()
            return Futures.immediateFuture(playable)
        }
    }
}
