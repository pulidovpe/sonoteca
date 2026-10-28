"""Teclas multimedia: registro de comandos en macOS (con MediaPlayer simulado) y mapa de teclas de Qt."""
import ast
import sys
from pathlib import Path

from sonoteca.ui import media_keys_macos as mk

ROOT = Path(__file__).resolve().parent.parent


class FakeCommand:
    def __init__(self):
        self.enabled, self.handler = None, None

    def setEnabled_(self, value):
        self.enabled = value

    def addTargetWithHandler_(self, handler):
        self.handler = handler
        return object()


class FakeCenter:
    """MPRemoteCommandCenter y MPNowPlayingInfoCenter de pega."""

    def __init__(self):
        self.commands = {}
        self.info, self.state = "sin tocar", None

    def sharedCommandCenter(self):
        return self

    def defaultCenter(self):
        return self

    def __getattr__(self, name):
        if name.endswith("Command"):
            return lambda: self.commands.setdefault(name, FakeCommand())
        raise AttributeError(name)

    def setNowPlayingInfo_(self, info):
        self.info = info

    def setPlaybackState_(self, state):
        self.state = state


def _fake_mediaplayer():
    center = FakeCenter()
    module = type(sys)("MediaPlayer")
    module.MPRemoteCommandCenter = center
    module.MPNowPlayingInfoCenter = center
    for name in ("Title", "Artist", "AlbumTitle", "PlaybackDuration"):
        setattr(module, f"MPMediaItemProperty{name}", f"mp.{name}")
    for name in ("ElapsedPlaybackTime", "PlaybackRate"):
        setattr(module, f"MPNowPlayingInfoProperty{name}", f"np.{name}")
    return module, center


def test_supported_commands_are_enabled_and_forward_their_name():
    module, center = _fake_mediaplayer()
    received = []
    mk.MacRemoteControls(received.append, mp=module)
    for command_name, name in mk.SUPPORTED:
        command = center.commands[command_name]
        assert command.enabled is True
        assert command.handler(object()) == mk.STATUS_SUCCESS      # el sistema espera «éxito»
        assert received[-1] == name
    assert received == ["toggle", "play", "pause", "next", "previous"]


def test_unsupported_commands_are_disabled():
    module, center = _fake_mediaplayer()
    mk.MacRemoteControls(lambda name: None, mp=module)
    for command_name in mk.UNSUPPORTED:
        assert center.commands[command_name].enabled is False, command_name


def test_now_playing_info_uses_seconds_and_playback_rate():
    module, center = _fake_mediaplayer()
    controls = mk.MacRemoteControls(lambda name: None, mp=module)
    controls.update("Título", "Artista", "Álbum", 215.5, 12.0, True)
    assert center.info == {"mp.Title": "Título", "mp.Artist": "Artista", "mp.AlbumTitle": "Álbum",
                           "mp.PlaybackDuration": 215.5, "np.ElapsedPlaybackTime": 12.0, "np.PlaybackRate": 1.0}
    assert center.state == mk.STATE_PLAYING
    controls.update("Título", "Artista", "Álbum", 215.5, 30.0, False)
    assert center.info["np.PlaybackRate"] == 0.0 and center.state == mk.STATE_PAUSED
    controls.update("", "", "", 0, 0, False, has_track=False)        # nada que sonar: se limpia el «Ahora suena»
    assert center.info is None and center.state == mk.STATE_STOPPED


def test_qt_key_map_covers_play_pause_next_previous():
    tree = ast.parse((ROOT / "src" / "sonoteca" / "ui" / "media_keys.py").read_text(encoding="utf-8"))
    mapping = next(ast.literal_eval(node.value) for node in ast.walk(tree)
                   if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "KEY_COMMANDS")
    assert mapping["Key_MediaTogglePlayPause"] == "toggle" and mapping["Key_MediaPlay"] == "toggle"
    assert mapping["Key_MediaNext"] == "next" and mapping["Key_MediaPrevious"] == "previous"
    assert set(mapping.values()) <= {"toggle", "pause", "next", "previous"}


def test_dependency_and_packaging_are_declared():
    assert "pyobjc-framework-MediaPlayer" in (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "MediaPlayer" in (ROOT / "packaging" / "sonoteca.spec").read_text(encoding="utf-8")
