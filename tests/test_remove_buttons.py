"""Botón «Quitar de la biblioteca» junto a «Seleccionar canciones» (álbum y búsqueda): con selección, solo lo marcado."""
from pathlib import Path

QML = Path(__file__).resolve().parent.parent / "src" / "sonoteca" / "ui" / "qml"


def _read(name):
    return (QML / name).read_text(encoding="utf-8")


def test_album_button_acts_on_selection_or_whole_album():
    page = _read("AlbumDetail.qml")
    func = page[page.index("function requestRemove()"):][:520]
    assert "sel.active ? sel.ordered(trackIds()) : trackIds()" in func          # con selección, solo las marcadas
    assert "whole" in func and "removeRequested(" in func
    button = page[page.index("id: removeButton"):][:420]
    assert "sel.active ? sel.count > 0" in button                               # en modo selección sin marcar nada: desactivado
    assert page.index("Seleccionar canciones") < page.index("id: removeButton")  # junto al botón de seleccionar


def test_search_button_acts_on_selection_or_results():
    page = _read("SearchPage.qml")
    func = page[page.index("function requestRemove()"):][:380]
    assert "sel.active ? sel.ordered(trackIds()) : page.actionIds" in func
    button = page[page.index("id: removeButton"):][:420]
    assert "sel.active ? sel.count > 0" in button
    assert page.index("Seleccionar canciones") < page.index("id: removeButton")


def test_main_confirms_and_leaves_a_removed_album():
    main = _read("Main.qml")
    assert main.count("onRemoveRequested: (ids, label, whole) => win.confirmRemoveFromLibrary(ids, label, whole)") == 2
    body = main[main.index("function confirmRemoveFromLibrary(ids, label, whole)"):][:2600]
    assert "confirmDialog.ask(" in body and "NO se borran" in body
    assert body.index("player.forgetTracks(ids)") < body.index("library.removeFromLibrary(ids)")
    assert "if (whole) leaveRemovedAlbum()" in body
    assert "function leaveRemovedAlbum()" in main
