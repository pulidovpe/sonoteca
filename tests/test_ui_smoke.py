"""Pruebas de la UI sin pantalla (Qt 'offscreen'). Se omiten si PySide6 no está instalado."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")


import pytest

pytest.importorskip("PySide6.QtQml")

from conftest import make_cover, make_mp3, needs_ffmpeg
from PySide6.QtCore import QSize

from musicapp.core.db import connect
from musicapp.core.scanner import scan
from musicapp.ui.controller import LibraryController
from musicapp.ui.cover_provider import CoverProvider, bucket_for

pytestmark = needs_ffmpeg


@pytest.fixture
def db_file(tmp_path):
    root = tmp_path / "music"
    cover = make_cover(tmp_path / "c.jpg", "0xcc3333")
    make_mp3(root / "A/1.mp3", cover, title="Uno", artist="Artista A", album="Con Portada",
             date="1999", track="1/2")
    make_mp3(root / "A/2.mp3", cover, title="Dos", artist="Artista A", album="Con Portada",
             date="1999", track="2/2")
    make_mp3(root / "B/2001-Wheatus - Teenage Dirtbag.mp3")  # sin tags
    path = tmp_path / "t.db"
    conn = connect(path)
    scan(conn, root)
    conn.close()
    return path


def test_controller(qapp, db_file):
    c = LibraryController(db_file)
    assert c.stats()["tracks"] == 3 and c.stats()["incomplete"] == 1
    albums = {a["displayTitle"]: a for a in c.albums(0, 0, 0)}
    assert set(albums) == {"Con Portada", "Sin álbum"}
    assert [d["decade"] for d in c.decades()] == [1990, 2000]
    tracks = c.tracks(albums["Con Portada"]["id"])
    assert [t["number"] for t in tracks] == ["1", "2"]
    assert tracks[0]["subtitle"] == ""  # mismo artista que el álbum
    assert c.album(albums["Con Portada"]["id"])["artist"] == "Artista A"
    assert c.searchAll("a")["tracks"] == []  # menos de 2 letras
    found = c.searchAll("DIRTBAG")
    assert found["tracks"][0]["subtitle"].startswith("Wheatus")
    assert [a["name"] for a in c.searchAll("artista a")["artists"]] == ["Artista A"]
    assert c.searchAll("con portada")["albums"][0]["title"] == "Con Portada"
    assert "deducido del nombre" in c.incomplete()[0]["subtitle"]
    assert c.album(9999) == {}


def test_bucket_for():
    assert [bucket_for(x) for x in (0, 100, 160, 161, 320, 500, 2000)] == [
        320, 160, 160, 320, 320, 640, 640]


def test_cover_provider(qapp, db_file, tmp_path):
    conn = connect(db_file)
    with_cover = conn.execute("SELECT id FROM albums WHERE title='Con Portada'").fetchone()[0]
    without = conn.execute("SELECT id FROM albums WHERE title!='Con Portada'").fetchone()[0]
    prov = CoverProvider(db_file, cache_dir=tmp_path / "cache")
    img = prov.requestImage(str(with_cover), QSize(), QSize(320, 320))
    assert (img.width(), img.height()) == (320, 320)
    assert img.pixelColor(10, 10).red() > 150  # portada roja, no el degradado
    assert list((tmp_path / "cache" / "covers").glob("*.jpg"))  # quedó en caché de disco
    again = prov.requestImage(str(with_cover), QSize(), QSize(320, 320))  # desde caché
    assert (again.width(), again.height()) == (320, 320)
    ph = prov.requestImage(str(without), QSize(), QSize(160, 160))
    assert (ph.width(), ph.height()) == (160, 160) and not ph.isNull()
    assert prov.requestImage("no-es-un-numero", QSize(), QSize(160, 160)).width() == 160
    # el artista usa la portada de su álbum con portada embebida (rojo), no el degradado
    artist = conn.execute("SELECT id FROM artists WHERE name='Artista A'").fetchone()[0]
    art_img = prov.requestImage(f"artist/{artist}", QSize(), QSize(320, 320))
    assert art_img.pixelColor(10, 10).red() > 150


def test_qml_loads_without_warnings(qml_env):
    qml_env.wait(200)
    assert qml_env.warnings == []


def test_menu_clear_button_and_actions(qml_env):
    env = qml_env
    js, act, wait, player = env.js, env.act, env.wait, env.player
    wait(100)
    assert [js(f"menuBar.menuAt({i}).title") for i in range(4)] == [
        "Archivo", "Ver", "Reproducción", "Ayuda"]
    # el botón de limpiar solo existe con texto, y limpiar vuelve a la sección anterior
    assert js("clearBtn.visible") is False
    act("searchField.text = 'pista'")
    assert js("clearBtn.visible") is True and js("searching") is True
    act("clearSearch()")
    assert js("searchField.text") == "" and js("searching") is False
    assert js("clearBtn.visible") is False
    # las acciones del menú funcionan
    act("actArtists.trigger()")
    assert js("section") == "artists"
    act("actReview.trigger()")
    assert js("section") == "review"
    assert js("actPlay.enabled") is False  # sin pista no se puede pausar
    act("player.playTrackIds([1], 0)")
    assert player.hasTrack and js("actPlay.enabled") is True and js("actPlay.text") == "Pausar"
    act("actShuffle.trigger()")
    assert player.shuffle is True
    act("actVolDown.trigger()")
    assert player.volume == pytest.approx(0.7)
    assert env.controller.about()["version"]
    assert env.warnings == []


def test_artist_photo_is_preferred_over_album_covers(qapp, db_file, tmp_path, monkeypatch):
    """Si se descargó la foto de un artista, esa foto se usa en la sección de artistas."""
    monkeypatch.setenv("MUSICAPP_DATA_DIR", str(tmp_path / "datos"))
    conn = connect(db_file)
    artist = conn.execute("SELECT id FROM artists WHERE name='Artista A'").fetchone()[0]
    prov = CoverProvider(db_file, cache_dir=tmp_path / "cache")
    before = prov.requestImage(f"artist/{artist}", QSize(), QSize(320, 320))
    assert before.pixelColor(10, 10).red() > 150  # sin foto: la portada roja del álbum
    photo = tmp_path / "datos" / "artists" / f"{artist}.jpg"
    photo.parent.mkdir(parents=True)
    photo.write_bytes(make_cover(tmp_path / "foto.jpg", "0x2288cc").read_bytes())
    after = prov.requestImage(f"artist/{artist}", QSize(), QSize(320, 320))
    px = after.pixelColor(10, 10)
    assert px.blue() > 150 and px.red() < 100  # ahora la foto azul
    assert (after.width(), after.height()) == (320, 320)
    # la portada del álbum sigue siendo la del álbum
    album = conn.execute("SELECT id FROM albums WHERE title='Con Portada'").fetchone()[0]
    assert prov.requestImage(str(album), QSize(), QSize(320, 320)).pixelColor(10, 10).red() > 150
