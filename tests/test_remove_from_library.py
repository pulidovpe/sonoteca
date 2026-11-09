"""«Quitar de la biblioteca…» en el menú ⋮ de canciones: no toca archivos, sale de «Reproduciendo» y no vuelve al escanear."""
import re
from pathlib import Path

from conftest import needs_ffmpeg

ROOT = Path(__file__).resolve().parent.parent
QML = ROOT / "src" / "sonoteca" / "ui" / "qml"


def _read(path):
    return path.read_text(encoding="utf-8")


def test_menu_item_and_confirmation_are_wired():
    menu, main = _read(QML / "TrackMenu.qml"), _read(QML / "Main.qml")
    assert "signal removeRequested(var ids)" in menu and "Quitar de la biblioteca" in menu
    assert "onRemoveRequested: (ids) => win.confirmRemoveFromLibrary(ids)" in main
    body = main[main.index("function confirmRemoveFromLibrary("):][:2600]
    assert "confirmDialog.ask(" in body and "NO se borran" in body                      # siempre con confirmación y aviso
    assert body.index("player.forgetTracks(ids)") < body.index("library.removeFromLibrary(ids)")   # sale de «Reproduciendo»
    # la opción está en el único menú de canciones, sin condición (disponible en todo el programa)
    start = menu.index("id: removeItem")
    item = menu[start:menu.index("}", menu.index("onTriggered", start))]
    assert "visible:" not in item and "enabled:" not in item


def test_controller_never_touches_files():
    source = _read(ROOT / "src" / "sonoteca" / "ui" / "controller.py")
    block = source[source.index("def removeFromLibrary"):][:700]
    assert not re.search(r"os\.remove|unlink|rmtree|moveToTrash", block)
    assert "library_folders.exclude_files" in block


@needs_ffmpeg
def test_remove_from_library_keeps_files_leaves_the_queue_and_survives_rescan(qapp, tmp_path, library_dir):
    from fakes import FakeBackend

    from sonoteca.core.db import connect
    from sonoteca.core.scanner import scan
    from sonoteca.ui.controller import LibraryController
    from sonoteca.ui.player_controller import PlayerController

    db = tmp_path / "l.db"
    conn = connect(db)
    scan(conn, library_dir)
    rows = conn.execute("SELECT t.id, f.path FROM tracks t JOIN files f ON f.id = t.file_id ORDER BY t.id").fetchall()
    ids = [r["id"] for r in rows]
    victim, victim_path = ids[1], rows[1]["path"]
    conn.close()

    player = PlayerController(FakeBackend(), db)
    player.playTrackIds(ids, 0)
    length = player.queueLength
    controller = LibraryController(db)
    player.forgetTracks([victim])
    result = controller.removeFromLibrary([victim])
    assert result["ok"] and result["removed"] == 1 and "siguen en el disco" in result["message"]
    assert player.queueLength == length - 1
    assert Path(victim_path).exists()                                   # el archivo sigue en el disco
    assert controller.trackInfo(victim) == {}
    check = connect(db)
    scan(check, library_dir)                                           # un escaneo nuevo no lo trae de vuelta
    assert check.execute("SELECT COUNT(*) FROM files WHERE path = ?", (victim_path,)).fetchone()[0] == 0
    assert check.execute("SELECT COUNT(*) FROM tracks").fetchone()[0] == len(ids) - 1
    check.close()
