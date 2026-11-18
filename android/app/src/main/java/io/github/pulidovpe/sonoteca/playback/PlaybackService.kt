package io.github.pulidovpe.sonoteca.playback

import android.content.Intent
import androidx.annotation.OptIn
import androidx.media3.common.AudioAttributes
import androidx.media3.common.C
import androidx.media3.common.MediaItem
import androidx.media3.common.util.UnstableApi
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.session.MediaSession
import androidx.media3.session.MediaSessionService
import com.google.common.util.concurrent.Futures
import com.google.common.util.concurrent.ListenableFuture

/**
 * Reproduce en segundo plano lo descargado en el teléfono (ExoPlayer + sesión de medios: notificación, pantalla de bloqueo, auriculares).
 * No usa red: solo abre entradas `content://media/…` que la app misma publicó con MediaStore.
 */
@OptIn(UnstableApi::class)
class PlaybackService : MediaSessionService() {
    private var mediaSession: MediaSession? = null

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
        mediaSession = MediaSession.Builder(this, player).setCallback(ResolveFromRequestMetadata()).build()
    }

    override fun onGetSession(controllerInfo: MediaSession.ControllerInfo): MediaSession? = mediaSession

    /** Si el usuario cierra la app desde recientes: se detiene el servicio salvo que esté sonando. */
    override fun onTaskRemoved(rootIntent: Intent?) {
        val player = mediaSession?.player
        if (player == null || !player.playWhenReady || player.mediaItemCount == 0) stopSelf()
    }

    override fun onDestroy() {
        mediaSession?.run {
            player.release()
            release()
        }
        mediaSession = null
        super.onDestroy()
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
