"""0.8.2: listas desplegables en la barra lateral y arrastre de canciones."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

import pytest

pytest.importorskip("PySide6.QtQml")

from conftest import needs_ffmpeg
from test_ui_edit import album_ids

pytestmark = needs_ffmpeg


def test_sidebar_lists_expand_and_show_existing_playlists(qml_env):
    env = qml_env
    _, ids = album_ids(env.controller)
    env.playlists.create("Mi lista")
    env.playlists.create("Otra")
    assert env.js("listsGroup.expanded") is False and env.js("listsGroup.open") is False
    env.act("listsGroup.expanded = true", 300)
    assert env.js("listsGroup.open") is True
    assert env.js("listsBox.contentHeight") >= 64  # una fila de 32 px por lista
    assert env.warnings == []


def test_dropping_a_dragged_track_on_a_sidebar_list_adds_it(qml_env):
    env = qml_env
    _, ids = album_ids(env.controller)
    pid = env.playlists.create("Destino")["id"]
    # el arrastre despliega las listas aunque estén plegadas
    env.act(f"DragState.begin([{ids[0]}], 'Pista', 10, 10)", 200)
    assert env.js("listsGroup.open") is True
    env.act(f"DragState.hoverListId = {pid}", 50)
    env.act(f"var id = DragState.hoverListId; DragState.end(); DragState.dropOnList(id, [{ids[0]}])", 300)
    assert env.playlists.trackIds(pid) == [ids[0]]
    assert env.js("listsGroup.open") is False        # al soltar vuelve a plegarse
    # soltar de nuevo la misma canción avisa en vez de duplicarla en silencio
    env.act(f"DragState.dropOnList({pid}, [{ids[0]}])", 200)
    assert env.playlists.trackIds(pid) == [ids[0]]
    assert "ya estaba" in env.js("toastText.text")
    assert env.warnings == []


def test_begin_ignores_empty_selection(qml_env):
    env = qml_env
    env.act("DragState.begin([], 'nada', 0, 0)", 50)
    assert env.js("DragState.active") is False
