"""0.8.5: cabecera de lista, pregunta al reproducir una canción suelta y letra en panel lateral."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

import pytest

from conftest import needs_ffmpeg

from sonoteca.core import playlists as store
from sonoteca.core.db import connect




def _seed(conn, artists):
    """Una pista por cada artista de `artists` (con repeticiones) y devuelve los ids de pista."""
    ids = []
    known = {}
    base = conn.execute("INSERT INTO artists (name, sort_name) VALUES ('Base', 'base')").lastrowid
    conn.execute("INSERT INTO albums (id, title, album_artist_id) VALUES (1, 'Al', ?)", (base,))
    for n, name in enumerate(artists, 1):
        if name not in known:
            known[name] = conn.execute("INSERT INTO artists (name, sort_name) VALUES (?, ?)", (name, name.lower())).lastrowid
        fid = conn.execute("INSERT INTO files (path, size, mtime_ns, format, kind) VALUES (?, 1, 1, 'mp3', 'audio')",
                           (f"/x/{n}.mp3",)).lastrowid
        ids.append(conn.execute("INSERT INTO tracks (file_id, album_id, artist_id, title, duration) VALUES (?, 1, ?, ?, 1)",
                                (fid, known[name], f"T{n}")).lastrowid)
    conn.commit()
    return ids


def test_describe_artists_orders_by_count_and_summarises(tmp_path):
    conn = connect(tmp_path / "d.db")
    pid = store.create(conn, "L")
    assert store.describe_artists(conn, pid) == ""
    ids = _seed(conn, ["A", "B", "B", "C", "D", "E"])
    store.add_tracks(conn, pid, ids[:1])
    assert store.describe_artists(conn, pid) == "Con A"
    store.add_tracks(conn, pid, ids[1:3])
    assert store.describe_artists(conn, pid) == "Con B y A"       # B tiene 2 canciones
    store.add_tracks(conn, pid, ids[3:4])
    assert store.describe_artists(conn, pid) == "Con B, A y C"
    store.add_tracks(conn, pid, ids[4:])
    assert store.describe_artists(conn, pid) == "Con B, A, C y 2 m\u00e1s"


@pytest.fixture
def db_file(tmp_path):
    pytest.importorskip("PySide6.QtQml")
    from conftest import make_mp3
    from sonoteca.core.scanner import scan
    root = tmp_path / "music"
    for n in (1, 2, 3):
        make_mp3(root / f"A/{n}.mp3", title=f"Pista {n}", artist="Artista", album="Disco",
                 date="2000", track=f"{n}/3")
    db = tmp_path / "t.db"
    conn = connect(db)
    scan(conn, root)
    conn.close()
    return db


def _ids(env):
    album = env.controller.albums(0, 0, 0)[0]["id"]
    return album, [t["id"] for t in env.controller.tracks(album)]


@needs_ffmpeg
def test_playlist_header_shows_cover_name_and_description(qml_env):
    env = qml_env
    album, ids = _ids(env)
    pid = env.playlists.createWithTracks("Mi lista", ids)["id"]
    env.act("showSection('playlists')", 400)
    env.act(f"openPlaylist({pid})", 600)
    assert env.js("stack.currentItem.nameText.text") == "Mi lista"
    assert "Artista" in env.js("stack.currentItem.descriptionText.text")
    assert "3 canciones" in env.js("stack.currentItem.descriptionText.text")
    assert env.js("stack.currentItem.cover.width") == 190 and env.js("stack.currentItem.cover.height") == 190
    assert env.warnings == []


@needs_ffmpeg
def test_single_track_with_a_running_list_asks_to_replace_or_keep(qml_env):
    env = qml_env
    album, ids = _ids(env)
    env.act(f"openAlbum({album})", 600)
    env.act("stack.currentItem.playOneRequested(%d)" % ids[1], 300)   # sin lista: no hay diálogo
    env.player.playTrackIds(ids, 0)
    env.act("stack.currentItem.playOneRequested(%d)" % ids[2], 300)
    assert env.js("queueChoice.visible") is True
    env.act("queueChoice.keepList()", 300)
    assert env.player.queueTrackIds() == [ids[0], ids[2], ids[1], ids[2]]   # suena ya; la lista sigue después
    assert env.player.currentId == ids[2]
    env.act("queueChoice.ask(%d); queueChoice.replaceList()" % ids[1], 300)
    assert env.player.queueTrackIds() == [ids[1]]
    assert env.warnings == []


@needs_ffmpeg
def test_lyrics_replaces_the_queue_in_the_right_panel(qml_env):
    env = qml_env
    album, ids = _ids(env)
    assert env.js("rightMode") == "queue" and env.js("rightPanel.width") > 0      # siempre hay panel: Reproduciendo
    env.player.playTrackIds(ids, 0)
    env.act("showSection('albums')", 300)
    env.act("toggleLyrics()", 500)                                                 # Letra reemplaza la lista
    assert env.js("lyricsPanelShown") is True and env.js("queuePanelShown") is False and env.js("win.section") == "albums"
    env.act("toggleLyrics()", 500)                                                 # sin letra: vuelve Reproduciendo
    assert env.js("lyricsPanelShown") is False and env.js("queuePanelShown") is True
    env.act("toggleLyrics(); toggleQueue()", 500)                                  # el icono Reproduciendo tambi\u00e9n devuelve la lista
    assert env.js("queuePanelShown") is True
    env.act("toggleQueue()", 500)                                                  # y, con la lista a la vista, pliega el panel
    assert env.js("rightCollapsed") is True
    env.act("toggleLyrics()", 500)                                                 # Letra lo vuelve a abrir
    assert env.js("lyricsPanelShown") is True and env.js("rightCollapsed") is False
    assert env.warnings == []


@needs_ffmpeg
def test_album_has_go_to_artist_button(qml_env):
    env = qml_env
    album, _ = _ids(env)
    info = env.controller.album(album)
    env.act(f"openAlbum({album})", 600)
    env.act("stack.currentItem.artistRequested(%d, 'Artista')" % info["artist_id"], 600)
    assert env.js("stack.currentItem.artistId") == info["artist_id"]
    assert env.warnings == []


@needs_ffmpeg
def test_review_page_dismiss_and_restore(qml_env):
    env = qml_env
    env.act("showSection('review')", 500)
    before = env.js("stack.currentItem.items.length")
    env.act("dismissReview(%d); confirmDialog.confirm()" % before, 400)
    assert env.js("stack.currentItem.items.length") == 0
    env.act("restoreReview()", 400)
    assert env.js("stack.currentItem.items.length") == before
    assert env.warnings == []


@needs_ffmpeg
def test_lyrics_page_has_manual_button_and_audio_button_tooltip(qml_env):
    env = qml_env
    album, ids = _ids(env)
    env.player.playTrackIds(ids, 0)
    env.act("showSection('albums')", 300)
    env.act("toggleLyrics()", 500)
    assert env.js("lyricsPanelShown") is True
    assert env.js("playerBar.audioButton.toolTip").startswith("Salida de audio")
    assert env.warnings == []


@needs_ffmpeg
def test_player_bar_links_to_artist_and_album_from_any_page(qml_env):
    env = qml_env
    album, ids = _ids(env)
    env.player.playTrackIds(ids, 0)
    env.act("showSection('home')", 400)
    assert env.js("playerBar.artistLink.linked") is True and env.js("playerBar.albumLink.linked") is True
    env.act("playerBar.albumRequested(player.currentTrack.albumId)", 600)
    assert env.js("stack.currentItem.albumId") == album
    env.act("playerBar.artistRequested(player.currentTrack.artistId, 'Artista')", 600)
    assert env.js("stack.currentItem.artistId") == env.player.currentTrack["artistId"]
    assert env.warnings == []


def test_set_artist_image_only_changes_the_photo(tmp_path, monkeypatch):
    pytest.importorskip("PySide6.QtCore")
    monkeypatch.setenv("SONOTECA_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("SONOTECA_CACHE_DIR", str(tmp_path / "cache"))
    from sonoteca.ui.online_controller import OnlineController
    db = tmp_path / "i.db"
    conn = connect(db)
    _seed(conn, ["Solo foto"])
    aid = conn.execute("SELECT id FROM artists WHERE name = 'Solo foto'").fetchone()["id"]
    conn.close()
    ctrl = OnlineController(db)
    png = tmp_path / "f.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 32)
    out = ctrl.setArtistImage(aid, str(png))
    assert out["ok"] and out["info"]["imagePath"] and out["info"]["bio"] == ""   # sin descripción: solo foto
    bad = tmp_path / "x.txt"
    bad.write_bytes(b"no es imagen")
    assert ctrl.setArtistImage(aid, str(bad))["ok"] is False


# ---- 0.9.0 ----
@needs_ffmpeg
def test_import_dialog_flow_and_harvest_dialog(qml_env, db_file, tmp_path, monkeypatch):
    from sonoteca.core import portable
    monkeypatch.setenv("SONOTECA_DATA_DIR", str(tmp_path / "datos"))
    bundle = tmp_path / "b.sonoteca"
    portable.export_library(db_file, bundle, data=tmp_path / "datos")
    env = qml_env
    env.act("transfer.importDialog.begin(%r)" % str(bundle), 300)
    assert env.js("transfer.importDialog.visible") is True and env.js("transfer.importDialog.stage") == "confirm"
    env.act("transfer.importDialog.doImport()", 300)
    assert env.js("transfer.importDialog.stage") == "restart"       # nada cambia hasta reiniciar
    assert portable.has_pending_import(tmp_path / "datos")
    env.act("transfer.importDialog.close(); harvestDialog.offer(true)", 300)   # el plan se calcula sin internet
    assert env.warnings == []


# ---- 0.9.1 ----
@needs_ffmpeg
def test_track_menu_has_artist_and_album_links_for_a_single_track(qml_env):
    env = qml_env
    album, ids = _ids(env)
    env.act("trackMenu.ids = [%d]" % ids[0], 200)
    assert env.js("trackMenu.artistItem.enabled") is True and env.js("trackMenu.albumItem.enabled") is True
    env.act("trackMenu.ids = [%d, %d]" % (ids[0], ids[1]), 200)       # varias pistas: sin enlaces
    assert env.js("trackMenu.artistItem.enabled") is False
    env.act("trackMenu.ids = [%d]; trackMenu.albumRequested(%d)" % (ids[0], album), 600)
    assert env.js("stack.currentItem.albumId") == album
    assert env.warnings == []


@needs_ffmpeg
def test_reset_dialog_stages_a_reset_and_servers_dialog_adds_a_server(qml_env, tmp_path, monkeypatch):
    from sonoteca.core import portable
    monkeypatch.setenv("SONOTECA_DATA_DIR", str(tmp_path / "datos"))
    env = qml_env
    env.act("transfer.resetLibrary()", 300)
    assert env.js("transfer.resetDialog.visible") is True and env.js("transfer.resetDialog.stage") == "confirm"
    env.act("transfer.resetDialog.doReset()", 300)
    assert env.js("transfer.resetDialog.stage") == "restart" and portable.has_pending_reset(tmp_path / "datos")
    env.act("transfer.resetDialog.close(); serversDialog.openDialog()", 300)
    env.act("serversDialog.nameField.text = 'Mi LRCLIB'; serversDialog.addLyrics()", 300)   # falta la direcci\u00f3n: error claro
    assert env.js("serversDialog.messageOk") is False
    r = env.js("serverConfig.addLyrics('Mi LRCLIB', 'https://letras.casa/api').ok")
    assert r is True and len(env.js("serverConfig.state().lyrics")) == 2
    assert env.warnings == []


# ---- 0.9.4: barra lateral de iconos ----
@needs_ffmpeg
def test_sidebar_is_an_icon_rail(qml_env):
    env = qml_env
    assert env.js("sidebarRail.width") == 72
    env.act("listsGroup.expanded = true", 200)
    assert env.js("listsGroup.open") is True and env.js("onlineBadge.text") in ("En línea", "Sin conexión")
    assert env.warnings == []
