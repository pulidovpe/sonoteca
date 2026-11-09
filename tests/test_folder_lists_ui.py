"""Crear listas desde carpetas: botón en la página Listas y diálogo con elección de subcarpetas y nombres repetidos."""
from pathlib import Path

from conftest import needs_ffmpeg

QML = Path(__file__).resolve().parent.parent / "src" / "sonoteca" / "ui" / "qml"


def _read(name):
    return (QML / name).read_text(encoding="utf-8")


def test_button_is_on_the_playlists_page_and_dialog_is_wired():
    page, main = _read("PlaylistsPage.qml"), _read("Main.qml")
    assert "Crear desde carpetas" in page and "signal foldersRequested()" in page
    assert "onFoldersRequested: folderListsDialog.openDialog()" in main
    assert "FolderListsDialog 1.0 FolderListsDialog.qml" in _read("qmldir")


def test_dialog_asks_on_name_conflicts_and_offers_subfolders():
    dialog = _read("FolderListsDialog.qml")
    assert "con subcarpetas" in dialog
    for mode in ("rename", "append", "skip"):
        assert f'"{mode}"' in dialog                                             # las tres decisiones posibles
    assert 'p.conflict === "" ? "create"' in dialog and 'stage = "conflicts"' in dialog   # solo pregunta si hay conflicto
    assert "playlists.createFromFolders(decisions)" in dialog


@needs_ffmpeg
def test_dialog_creates_lists_from_library_folders(qml_env):
    env = qml_env
    env.act("folderListsDialog.openDialog()", 400)
    assert env.js("folderListsDialog.visible") is True
    count = env.js("folderListsDialog.candidates.length")
    assert count >= 3
    before = len(env.playlists.lists())
    env.act("folderListsDialog.setPicked(folderListsDialog.candidates[0].path, true)", 200)
    assert env.js("folderListsDialog.pickedCount") == 1
    env.act("folderListsDialog.start()", 500)
    if env.js("folderListsDialog.stage") == "conflicts":                          # no debería: no hay listas con ese nombre
        env.act("folderListsDialog.finish()", 400)
    assert len(env.playlists.lists()) == before + 1
    # una segunda vez con la misma carpeta: ahora hay conflicto y el diálogo pregunta
    env.act("folderListsDialog.openDialog()", 300)
    env.act("folderListsDialog.setPicked(folderListsDialog.candidates[0].path, true)", 200)
    env.act("folderListsDialog.start()", 500)
    assert env.js("folderListsDialog.stage") == "conflicts"
    env.act("folderListsDialog.finish()", 400)                                    # por defecto: crear con otro nombre
    assert len(env.playlists.lists()) == before + 2
    assert env.warnings == []
