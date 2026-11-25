"""Migración de la base (partes 1 y 2): comprobación del texto de los QML y de app.py (sin Qt)."""
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src" / "sonoteca" / "ui"


def _read(*parts):
    return SRC.joinpath(*parts).read_text(encoding="utf-8")


def test_the_new_windows_are_registered_and_wired_into_main():
    qmldir = _read("qml", "qmldir")
    assert "MigrationNoticeDialog 1.0 MigrationNoticeDialog.qml" in qmldir and "StartupError 1.0 StartupError.qml" in qmldir
    main = _read("qml", "Main.qml")
    assert "MigrationNoticeDialog { id: migrationNotice }" in main and "migrationNotice.showIfNeeded()" in main
    assert "library.migrationNotice()" in _read("qml", "MigrationNoticeDialog.qml")
    assert "startupError.title" in _read("qml", "StartupError.qml")


def test_app_shows_the_startup_error_window_instead_of_a_traceback():
    app = _read("app.py")
    assert "return _startup_error(app, engine, real_db, version_before, exc)" in app
    assert "controller.set_migration_notice(migration_notice.after_open(real_db, version_before))" in app
    assert "def _startup_error(" in app
