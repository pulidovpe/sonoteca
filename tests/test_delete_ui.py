"""Eliminar archivos desde «Por revisar»: a la papelera, de uno en uno; duplicados por lotes y con confirmación."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QML = ROOT / "src" / "sonoteca" / "ui" / "qml"
CORE = ROOT / "src" / "sonoteca" / "core"


def _read(path):
    return path.read_text(encoding="utf-8")


def test_nothing_is_ever_deleted_permanently():
    for source in (_read(CORE / "file_delete.py"), _read(ROOT / "src" / "sonoteca" / "ui" / "controller.py")):
        assert not re.search(r"os\.remove|\.unlink\(|shutil\.rmtree|os\.unlink", source)
    assert "QFile.moveToTrash" in _read(ROOT / "src" / "sonoteca" / "ui" / "controller.py")


def test_single_file_delete_is_only_in_review_and_one_at_a_time():
    menu, main = _read(QML / "TrackMenu.qml"), _read(QML / "Main.qml")
    assert "property bool allowDelete: false" in menu and "enabled: root.ids.length === 1" in menu
    assert main.count("win.showTrackMenu(ids, true)") == 1                      # solo la página «Por revisar»
    assert "trackMenu.allowDelete = !!allowDelete" in main
    body = main[main.index("function confirmDeleteFile(id)"):][:900]
    assert body.index("player.forgetTracks([id])") < body.index("library.deleteTrackFile(id)")
    assert "papelera" in body and "confirmDialog.ask(" in body                  # siempre con confirmación


def test_duplicates_are_batched_verified_and_need_a_confirmation_step():
    dialog = _read(QML / "DuplicatesDialog.qml")
    assert 'stage = "confirm"' in dialog and 'onClicked: root.start()' in dialog
    starts = [line for line in dialog.splitlines() if "root.start()" in line]
    assert len(starts) == 1 and 'stage === "confirm"' in starts[0]               # solo se ejecuta desde el paso de confirmación
    assert "player.forgetTracks(ids)" in dialog and "verifica" in dialog           # se avisa de la verificación del contenido
    assert "Buscar duplicados" in _read(QML / "Main.qml") and "DuplicatesDialog 1.0" in _read(QML / "qmldir")


def test_duplicate_criteria_are_the_four_requested():
    source = _read(CORE / "duplicates.py")
    for needle in ("normalize(r[\"artist\"])", "normalize(r[\"title\"])", 'round(r["duration"] or 0)', ".name.lower()", 'r["size"]'):
        assert needle in source, needle
