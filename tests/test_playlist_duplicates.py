"""0.12.8: al agregar a una lista canciones que ya están, se pregunta (selector y arrastrar)."""
from pathlib import Path

QML = Path(__file__).resolve().parents[1] / "src" / "sonoteca" / "ui" / "qml"


def _read(name):
    return (QML / name).read_text(encoding="utf-8")


def test_picker_and_drop_ask_before_repeating():
    picker = _read("PlaylistPicker.qml")
    assert "playlists.existingCount(playlistId, ids)" in picker and "duplicatesFound(playlistId, chosen, dup)" in picker
    main = _read("Main.qml")
    assert "onDuplicatesFound: (listId, ids, count) => duplicateDialog.openFor(listId, ids, count)" in main
    assert "if (dup > 0) { duplicateDialog.openFor(listId, ids, dup); return }" in main
    assert "DuplicateInListDialog 1.0 DuplicateInListDialog.qml" in _read("qmldir")


def test_dialog_offers_new_only_all_or_cancel():
    dialog = _read("DuplicateInListDialog.qml")
    for text in ('label: "Cancelar"', 'label: "Agregar solo las nuevas"', 'root.all ? "Agregar de nuevo" : "Agregar todas"'):
        assert text in dialog, text
    assert "playlists.addNewTracks(listId, ids)" in dialog and "playlists.addTracks(listId, ids)" in dialog
