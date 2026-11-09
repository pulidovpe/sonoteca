"""Mini reproductor: ventana compacta con la portada del álbum (o del artista) y los botones."""
import re
import sqlite3
from pathlib import Path

from sonoteca.core import covers
from sonoteca.core.db import connect

QML = Path(__file__).resolve().parent.parent / "src" / "sonoteca" / "ui" / "qml"


def test_mini_mode_shrinks_the_main_window_and_restores_it():
    main = (QML / "Main.qml").read_text(encoding="utf-8")
    assert "function enterMini()" in main and "function exitMini()" in main and "property bool miniMode: false" in main
    assert "Qt.WindowStaysOnTopHint" in main                                   # siempre visible
    assert re.search(r"fullGeometry = \{ x: win\.x, y: win\.y, w: win\.width, h: win\.height", main)
    for restored in ("win.width = g.w", "win.height = g.h", "win.x = g.x", "win.y = g.y", "win.maximumWidth = 16777215"):
        assert restored in main, restored
    assert "id: fullUi\n        visible: !win.miniMode" in main and "visible: win.miniMode" in main
    assert "visible: !win.miniMode\n" in main.split("menuBar: AppMenuBar {")[1][:60]     # sin barra de menú en el modo mini


def test_corner_icon_and_shortcut_enter_mini_mode_and_mini_has_a_restore_icon():
    bar = (QML / "PlayerBar.qml").read_text(encoding="utf-8")
    assert "signal miniRequested()" in bar and "id: miniButton" in bar and "Theme.iconMini" in bar
    mini = (QML / "MiniPlayer.qml").read_text(encoding="utf-8")
    assert "Theme.iconExpand" in mini and "restoreRequested" in mini
    # solo portada y botones de reproducción (más el tooltip con el título)
    for call in ("player.previous()", "player.toggle()", "player.next()"):
        assert call in mini
    assert "Slider" not in mini
    assert "Ctrl+Shift+M" in (QML / "Main.qml").read_text(encoding="utf-8")


def _library(tmp_path, monkeypatch):
    monkeypatch.setenv("SONOTECA_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("SONOTECA_CACHE_DIR", str(tmp_path / "cache"))
    conn = connect(tmp_path / "m.db")
    conn.row_factory = sqlite3.Row
    artist = conn.execute("INSERT INTO artists (name, sort_name) VALUES ('Banda', 'banda')").lastrowid
    albums = [conn.execute("INSERT INTO albums (title, album_artist_id, year) VALUES (?, ?, ?)", (t, artist, y)).lastrowid
              for t, y in (("Con portada", 2000), ("Sin portada", 2005))]
    for n, album in enumerate(albums):
        fid = conn.execute("INSERT INTO files (path, size, mtime_ns, format, kind) VALUES (?, 1, 1, 'mp3', 'audio')",
                           (str(tmp_path / f"{n}.mp3"),)).lastrowid
        conn.execute("INSERT INTO tracks (file_id, album_id, artist_id, title, duration) VALUES (?, ?, ?, 'T', 1)",
                     (fid, album, artist))
    conn.commit()
    return conn, artist, albums


def test_cover_kind_prefers_the_album_then_the_artist_then_nothing(tmp_path, monkeypatch):
    conn, artist, (with_cover, without_cover) = _library(tmp_path, monkeypatch)
    assert covers.cover_kind(conn, without_cover, artist) == ""                      # nada: marcador de posición
    image = tmp_path / "downloaded.jpg"
    image.write_bytes(b"\xff\xd8\xff" + b"0" * 20)
    conn.execute("UPDATE albums SET cover_path = ? WHERE id = ?", (str(image), with_cover))
    conn.commit()
    assert covers.cover_kind(conn, with_cover, artist) == "album"
    assert covers.cover_kind(conn, without_cover, artist) == "artist"                # el otro álbum del artista tiene portada
    conn.execute("UPDATE albums SET cover_path = NULL WHERE id = ?", (with_cover,))
    conn.commit()
    photo = tmp_path / "data" / "artists"
    photo.mkdir(parents=True)
    (photo / f"{artist}.jpg").write_bytes(b"\xff\xd8\xff" + b"0" * 20)
    assert covers.cover_kind(conn, without_cover, artist) == "artist"                # foto del artista


def test_mini_player_shows_a_scrolling_accent_title_over_the_cover_with_a_contrast_background():
    mini = (QML / "MiniPlayer.qml").read_text(encoding="utf-8")
    assert "text: player.hasTrack ? player.currentTrack.title : \"\"" in mini and "color: Theme.accent" in mini
    assert "readonly property real overflow: Math.max(0, titleText.implicitWidth - width)" in mini
    assert "SequentialAnimation" in mini and "loops: Animation.Infinite" in mini and "PauseAnimation" in mini
    cover = mini[mini.index("id: coverBox"):mini.index("Row {\n")]
    assert "id: titleBar" in cover and "id: titleBox" in cover        # el título y su fondo van dentro de la portada
    assert "color: Theme.bg" in cover and "opacity: 0.86" in cover
    assert "top: coverBox.bottom; bottom: parent.bottom" in mini
    assert "parent.height - 8 - 52 - 6" in mini                       # la portada solo cede alto a los botones
    assert "readonly property int miniHeight: 236" in (QML / "Main.qml").read_text(encoding="utf-8")


def test_toast_appears_at_the_top_of_the_window():
    main = (QML / "Main.qml").read_text(encoding="utf-8")
    box = main[main.index("id: toastBox"):main.index("Timer { id: toastTimer")]
    assert "top: parent.top; topMargin: 20" in box and "bottom: parent.bottom" not in box


def test_mini_mode_on_wayland_does_not_change_flags_and_resizes_after_the_state_change():
    main = (QML / "Main.qml").read_text(encoding="utf-8")
    assert "readonly property bool isWayland" in main and "onWayland" not in main      # «on»+Mayúscula rompe QML
    assert main.count("if (!isWayland) win.flags") == 2                                  # entrar y salir
    assert "function applyMiniSize()" in main and "id: miniFallback" in main and "id: miniSettle" in main
    assert "function onVisibilityChanged()" in main and "finishPendingMini" in main
