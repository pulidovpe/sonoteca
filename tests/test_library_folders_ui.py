"""Diálogo «Carpetas de la biblioteca» (menú Archivo): listar, quitar con confirmación y volver a incluir."""
from pathlib import Path

from conftest import needs_ffmpeg


def test_menu_and_dialog_are_wired():
    qml_dir = Path(__file__).resolve().parents[1] / "src/sonoteca/ui/qml"
    main = (qml_dir / "Main.qml").read_text(encoding="utf-8")
    assert "AppMenuItem { action: actFolders }" in main and "foldersDialog.openDialog()" in main
    assert "LibraryFoldersDialog 1.0 LibraryFoldersDialog.qml" in (qml_dir / "qmldir").read_text(encoding="utf-8")
    app = (Path(__file__).resolve().parents[1] / "src/sonoteca/ui/app.py").read_text(encoding="utf-8")
    assert '"libraryFolders"' in app


@needs_ffmpeg
def test_folders_dialog_lists_removes_and_includes_again(qml_env):
    env = qml_env
    env.act("actFolders.trigger()", 400)
    assert env.js("foldersDialog.visible") is True
    before = env.js("foldersDialog.folders.length")
    assert before >= 3 and env.js("foldersDialog.excluded.length") == 0
    env.act("foldersDialog.askRemove(foldersDialog.folders[0].path, foldersDialog.folders[0].name, foldersDialog.folders[0].total)", 200)
    assert env.js("foldersDialog.pending !== null") is True
    env.act("foldersDialog.pending = null", 100)                      # cancelar no quita nada
    assert env.js("foldersDialog.folders.length") == before
    env.act("foldersDialog.askRemove(foldersDialog.folders[0].path, foldersDialog.folders[0].name, foldersDialog.folders[0].total)", 200)
    env.act("foldersDialog.confirmRemove()", 400)
    assert env.js("foldersDialog.folders.length") == before - 1
    assert env.js("foldersDialog.excluded.length") == 1
    env.act("foldersDialog.includeAgain(foldersDialog.excluded[0].path)", 300)
    assert env.js("foldersDialog.excluded.length") == 0
    assert env.warnings == []
