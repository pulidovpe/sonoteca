"""Edición de tags desde la UI: controlador (hilo de trabajo) y editor QML."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

import time

import pytest

pytest.importorskip("PySide6.QtQml")

from conftest import make_cover, make_mp3, needs_ffmpeg
from PySide6.QtCore import QObject, Slot

from musicapp.core import library
from musicapp.core.db import connect
from musicapp.core.scanner import scan
from musicapp.core.tags import read_tags
from musicapp.ui.controller import LibraryController

pytestmark = needs_ffmpeg


class Collector(QObject):
    def __init__(self):
        super().__init__()
        self.finished: list[dict] = []
        self.progress: list[tuple[int, int]] = []

    @Slot("QVariantMap")
    def on_finished(self, result):
        self.finished.append(result)

    @Slot(int, int)
    def on_progress(self, done, total):
        self.progress.append((done, total))


def wait_until(qapp, cond, timeout=10.0):
    end = time.time() + timeout
    while not cond() and time.time() < end:
        qapp.processEvents()
        time.sleep(0.01)
    return cond()


@pytest.fixture
def lib(tmp_path, monkeypatch):
    monkeypatch.setenv("MUSICAPP_DATA_DIR", str(tmp_path / "datos"))
    root = tmp_path / "music"
    cover = make_cover(tmp_path / "c.jpg", "0xcc3333")
    for n in (1, 2):
        make_mp3(root / f"A/{n}.mp3", cover, title=f"Pista {n}", artist="FOR NON BLONDIES",
                 album="What's Up", date="1993", track=f"{n}/2")
    db = tmp_path / "t.db"
    conn = connect(db)
    scan(conn, root)
    conn.close()
    return db, root


@pytest.fixture
def db_file(lib):
    """Base que usa la fixture compartida `qml_env`."""
    return lib[0]


def album_ids(controller):
    album = controller.albums(0, 0, 0)[0]
    return album["id"], [t["id"] for t in controller.tracks(album["id"])]


def test_controller_tag_values_preview_and_local_path(qapp, lib):
    db, _ = lib
    c = LibraryController(db)
    _, ids = album_ids(c)
    assert c.tagValues(ids)["artist"] == {"value": "FOR NON BLONDIES", "mixed": False}
    ok = c.previewEdit(ids, {"artist": "4 Non Blondes"}, "")
    assert ok["error"] == "" and ok["count"] == 2 and len(ok["lines"]) == 1
    assert "una pista a la vez" in c.previewEdit(ids, {"title": "x"}, "")["error"]
    assert "número" in c.previewEdit(ids, {"year": "abc"}, "")["error"]
    assert c.previewEdit(ids, {}, "")["error"] == "No hay cambios que aplicar"
    assert c.localPath("file:///tmp/a%20b.jpg") == "/tmp/a b.jpg"


def test_controller_apply_runs_in_background_and_refreshes_search(qapp, lib):
    db, root = lib
    c = LibraryController(db)
    col = Collector()
    c.editFinished.connect(col.on_finished)
    c.editProgress.connect(col.on_progress)
    assert c.searchAll("non blondies")["artists"]  # arma el índice de búsqueda
    _, ids = album_ids(c)
    c.applyEdit(ids, {"artist": "4 Non Blondes", "album": "Bigger"}, "", False)
    assert wait_until(qapp, lambda: col.finished), "la edición no terminó"
    res = col.finished[0]
    assert res["updated"] == 2 and res["failed"] == [] and res["albumId"]
    assert col.progress[-1] == (2, 2)
    assert read_tags(root / "A/1.mp3").artist == "4 Non Blondes"
    # el índice se descartó: la búsqueda ya ve los datos nuevos
    assert c.searchAll("bigger")["albums"][0]["title"] == "Bigger"
    assert not c.searchAll("for non blondies")["artists"]


def test_controller_rejects_concurrent_edit_and_reports_errors(qapp, lib):
    db, root = lib
    c = LibraryController(db)
    col = Collector()
    c.editFinished.connect(col.on_finished)
    _, ids = album_ids(c)
    c._editing = True  # simula una edición en curso
    c.applyEdit(ids, {"genre": "Rock"}, "", False)
    assert wait_until(qapp, lambda: col.finished)
    assert "en curso" in col.finished[0]["failed"][0]["message"]
    c._editing = False
    (root / "A/2.mp3").unlink()  # un archivo desaparece: se informa, el otro se edita
    c.applyEdit(ids, {"genre": "Rock"}, "", False)
    assert wait_until(qapp, lambda: len(col.finished) == 2)
    assert col.finished[1]["updated"] == 1 and len(col.finished[1]["failed"]) == 1


def test_editor_flow_from_qml(qml_env, monkeypatch, tmp_path):
    env = qml_env
    monkeypatch.setenv("MUSICAPP_DATA_DIR", str(tmp_path / "datos"))
    js, act, wait = env.js, env.act, env.wait
    _, ids = album_ids(env.controller)
    tid = ids[0]
    act(f"win.editTags([{tid}])", 300)
    assert js("tagEditor.visible") is True and js("tagEditor.step") == 0
    assert js("tagEditor.info.title.value") == "Pista 1"
    # el título/nº de pista solo se editan de una pista; con una sola está disponible
    act("tagEditor.setField('title', 'Pista 1 corregida'); tagEditor.goReview()", 200)
    assert js("tagEditor.step") == 1 and js("tagEditor.reviewData.lines.length") == 1
    act("tagEditor.apply()", 100)
    for _ in range(40):  # al terminar, el editor se cierra solo y aparece un aviso breve
        if js("tagEditor.visible") is False and js("toastBox.visible") is True:
            break
        wait(200)
    assert js("tagEditor.visible") is False and js("tagEditor.step") == 0
    assert js("toastText.text") == "1 archivo actualizado"
    assert js("Theme.dataRevision") >= 1
    path = library.get_track(connect(env.controller._db_path), tid)["path"]
    assert read_tags(__import__("pathlib").Path(path)).title == "Pista 1 corregida"
    assert env.warnings == []


def test_open_album_follows_renamed_album(qml_env):
    env = qml_env
    js, act, wait = env.js, env.act, env.wait
    old_album, ids = album_ids(env.controller)
    act(f"openAlbum({old_album})", 400)
    assert js("stack.depth") == 2 and js("stack.currentItem.albumId") == old_album
    env.controller.applyEdit(ids, {"album": "Renombrado"}, "", False)
    for _ in range(40):
        if js("stack.currentItem.albumId") != old_album:
            break
        wait(200)
    new_album = js("stack.currentItem.albumId")
    assert new_album != old_album and js("stack.depth") == 2
    assert js("stack.currentItem.info.displayTitle") == "Renombrado"
    assert env.warnings == []


def test_edit_summary_messages(qml_env):
    js = qml_env.js
    assert js("editSummary({updated: 3, failed: []})") == "3 archivos actualizados"
    assert js("editSummary({updated: 1})") == "1 archivo actualizado"
    assert js("editSummary({updated: 2, failed: [{path: '/a/b.mp3', message: 'x'}]})") == (
        "2 archivos actualizados \u00b7 1 fall\u00f3: b.mp3 \u2014 x")
    assert js("editSummary({updated: 0, failed: [{path: 'C:\\\\m\\\\b.mp3', message: 'x'}]})") == (
        "No se pudo actualizar ning\u00fan archivo: b.mp3 \u2014 x")
    assert qml_env.warnings == []


LONG_NAME = "Portada_del_album_con_un_nombre_de_archivo_ridiculamente_largo_version_final_v2_(copia).jpg"


def test_long_cover_name_and_long_tags_stay_inside_the_form(qml_env, tmp_path):
    env = qml_env
    js, act = env.js, env.act
    long_title = "Un título larguísimo " * 8
    conn = connect(env.controller._db_path)
    tid = album_ids(env.controller)[1][0]
    track = library.get_track(conn, tid)
    from pathlib import Path as _P

    from musicapp.core.tag_writer import write_tags

    write_tags(_P(track["path"]), {"title": long_title, "album": "A" * 150})
    from musicapp.core.scanner import reindex_file

    reindex_file(conn, _P(track["path"]))
    conn.close()
    act(f"win.editTags([{tid}])", 400)
    # los campos largos muestran el principio del texto, no el final
    assert js("tagEditor.fieldCursor('title')") == 0
    assert js("tagEditor.fieldCursor('album')") == 0
    # nombre de portada largo: se elide y el botón "Quitar" no se sale del formulario
    act(f"tagEditor.coverPath = '/algun/lugar/{LONG_NAME}'", 300)
    assert js("tagEditor.coverNameItem.truncated") is True
    assert js("tagEditor.coverNameItem.text").endswith(".jpg")
    right_edge = js("tagEditor.removeCoverItem.mapToItem(tagEditor.contentItem, "
                    "tagEditor.removeCoverItem.width, 0).x")
    assert right_edge <= js("tagEditor.contentItem.width") + 0.5
    # y uno corto no se elide
    act("tagEditor.coverPath = '/x/a.jpg'", 200)
    assert js("tagEditor.coverNameItem.truncated") is False
    assert env.warnings == []


def test_controller_cover_preview(qapp, lib):
    db, _ = lib
    c = LibraryController(db)
    album_id, ids = album_ids(c)
    one = c.coverPreview(ids, 0)
    assert one["state"] == "single" and one["source"] == f"image://cover/{album_id}"
    artist = c.artists()[0]
    assert c.coverPreview([], artist["id"])["source"] == f"image://cover/artist/{artist['id']}"
    assert sorted(c.artistTrackIds(artist["id"])) == sorted(ids)


def test_editor_shows_current_and_new_cover(qml_env, tmp_path):
    env = qml_env
    js, act = env.js, env.act
    album_id, ids = album_ids(env.controller)
    act(f"win.editTags([{ids[0]}])", 400)
    assert js("tagEditor.coverState.state") == "single"
    assert js("tagEditor.currentThumbItem.visible") is True
    assert js("tagEditor.coverPath") == ""
    # al elegir una imagen aparece la miniatura nueva junto a la actual
    new = make_cover(tmp_path / "nueva.jpg", "0x33cc33")
    act(f"tagEditor.coverPath = '{new}'", 400)
    assert js("tagEditor.newThumbItem.source.toString()").endswith("nueva.jpg")
    assert js("tagEditor.currentThumbItem.visible") is True
    # modo artista: la imagen actual es la del artista
    artist_id = env.controller.artists()[0]["id"]
    act(f"tagEditor.close(); win.editArtistTags({artist_id}, 'FOR NON BLONDIES')", 400)
    assert js("tagEditor.visible") is True and js("tagEditor.artistId") == artist_id
    assert js("tagEditor.ids.length") == 2
    assert js("tagEditor.currentThumbItem.source.toString()").startswith(
        f"image://cover/artist/{artist_id}")
    assert env.warnings == []
