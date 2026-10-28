"""Teclas multimedia globales en macOS (MPRemoteCommandCenter).

macOS NO entrega las teclas de reproducir/pausa, siguiente y anterior a las aplicaciones como eventos de teclado: las
recibe el sistema y las envía a la aplicación que figura como «Ahora suena». Para serlo hay que registrar comandos en
`MPRemoteCommandCenter` y publicar los datos en `MPNowPlayingInfoCenter` (sin permisos especiales). Esto usa PyObjC:
`pip install pyobjc-framework-MediaPlayer` (ya incluido en el extra `ui` de Sonoteca en macOS).

Los manejadores pueden llamarse desde cualquier hilo; `on_command(nombre)` debe ser seguro entre hilos (una señal de Qt).
No importa PySide6, para poder probarse con un módulo MediaPlayer simulado.
"""
from __future__ import annotations

# MPRemoteCommandHandlerStatusSuccess
STATUS_SUCCESS = 0
# MPNowPlayingPlaybackState: unknown 0, playing 1, paused 2, stopped 3, interrupted 4
STATE_PLAYING, STATE_PAUSED, STATE_STOPPED = 1, 2, 3

# comando de macOS -> nombre que se envía a la aplicación
SUPPORTED = (
    ("togglePlayPauseCommand", "toggle"),
    ("playCommand", "play"),
    ("pauseCommand", "pause"),
    ("nextTrackCommand", "next"),
    ("previousTrackCommand", "previous"),
)
# Los comandos que no se atienden se desactivan: así macOS no los ofrece (ni espera respuesta).
UNSUPPORTED = (
    "stopCommand", "changePlaybackPositionCommand", "skipForwardCommand", "skipBackwardCommand",
    "seekForwardCommand", "seekBackwardCommand", "likeCommand", "dislikeCommand", "bookmarkCommand",
    "changeRepeatModeCommand", "changeShuffleModeCommand", "changePlaybackRateCommand", "ratingCommand",
    "enableLanguageOptionCommand", "disableLanguageOptionCommand",
)


class MacRemoteControls:
    def __init__(self, on_command, mp=None) -> None:
        self._mp = mp if mp is not None else __import__("MediaPlayer")   # ImportError si falta PyObjC
        self._on_command = on_command
        self._keep: list = []            # PyObjC convierte los manejadores en bloques: hay que conservar las referencias
        center = self._mp.MPRemoteCommandCenter.sharedCommandCenter()
        for command_name, name in SUPPORTED:
            command = getattr(center, command_name)()
            command.setEnabled_(True)

            def handler(event, _name=name):
                self._on_command(_name)
                return STATUS_SUCCESS

            self._keep.append((command, command.addTargetWithHandler_(handler), handler))
        for command_name in UNSUPPORTED:
            command = getattr(center, command_name, None)
            if command is not None:
                command().setEnabled_(False)

    def update(self, title: str, artist: str, album: str, duration_s: float, position_s: float, playing: bool,
               has_track: bool = True) -> None:
        """Publica la pista y el estado. macOS calcula el avance a partir de la posición y la velocidad."""
        mp = self._mp
        center = mp.MPNowPlayingInfoCenter.defaultCenter()
        if not has_track:
            center.setNowPlayingInfo_(None)
            center.setPlaybackState_(STATE_STOPPED)
            return
        info = {
            mp.MPMediaItemPropertyTitle: title or "",
            mp.MPMediaItemPropertyArtist: artist or "",
            mp.MPMediaItemPropertyAlbumTitle: album or "",
            mp.MPMediaItemPropertyPlaybackDuration: float(duration_s),
            mp.MPNowPlayingInfoPropertyElapsedPlaybackTime: float(position_s),
            mp.MPNowPlayingInfoPropertyPlaybackRate: 1.0 if playing else 0.0,
        }
        center.setNowPlayingInfo_(info)
        center.setPlaybackState_(STATE_PLAYING if playing else STATE_PAUSED)
