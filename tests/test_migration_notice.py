"""Migración de la base (partes 1 y 2): aviso tras actualizar y mensajes claros cuando no se puede abrir (sin Qt)."""
import sqlite3

from sonoteca.core import db, migration_notice as mn


def _v9(tmp_path):
    """Una base «de la versión anterior»: el esquema actual con user_version 9 (la migración es repetible)."""
    path = tmp_path / "library.db"
    db.connect(path).close()
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA user_version = 9")
    conn.commit()
    conn.close()
    return path


def test_peek_version_reads_without_touching_the_file(tmp_path):
    assert mn.peek_version(tmp_path / "no_existe.db") == 0
    garbage = tmp_path / "basura.db"
    garbage.write_text("no soy una base de datos")
    assert mn.peek_version(garbage) == 0
    path = _v9(tmp_path)
    before = path.read_bytes()
    assert mn.peek_version(path) == 9
    assert path.read_bytes() == before


def test_after_open_reports_the_migration_and_where_the_backup_is(tmp_path):
    path = _v9(tmp_path)
    before = mn.peek_version(path)
    db.connect(path).close()                                   # migra
    info = mn.after_open(path, before)
    assert info["migrated"] is True and info["fromVersion"] == 9 and info["toVersion"] == db.SCHEMA_VERSION
    assert info["backup"].endswith("library.db.v9.bak") and info["folderUrl"].startswith("file://")
    assert mn.after_open(path, mn.peek_version(path)) == {"migrated": False}          # abrir otra vez: sin aviso
    assert mn.after_open(tmp_path / "nueva.db", 0) == {"migrated": False}             # base nueva: sin aviso


def test_a_newer_library_is_explained_and_points_to_the_backup_if_there_is_one(tmp_path):
    path = tmp_path / "library.db"
    db.connect(path).close()
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA user_version = 99")
    conn.commit()
    conn.close()
    try:
        db.connect(path)
    except RuntimeError as exc:
        error = exc
    else:
        raise AssertionError("debía negarse a abrir una base más nueva")
    info = mn.describe_failure(path, error)
    assert info["kind"] == "newer" and "v99" in info["message"] and f"v{db.SCHEMA_VERSION}" in info["message"]
    assert info["backup"] == "" and "No se ha cambiado nada" in info["message"]
    backup = db.backup_path(path, db.SCHEMA_VERSION)
    backup.write_bytes(b"copia")
    again = mn.describe_failure(path, error)
    assert again["backup"] == str(backup) and backup.name in again["message"]


def test_a_damaged_file_a_locked_database_and_other_errors_get_their_own_message(tmp_path):
    path = tmp_path / "library.db"
    path.write_text("no soy una base de datos")
    try:
        db.connect(path)
    except sqlite3.DatabaseError as exc:
        error = exc
    else:
        raise AssertionError("debía fallar con un archivo que no es una base")
    damaged = mn.describe_failure(path, error)
    assert damaged["kind"] == "damaged" and "library.db" in damaged["message"] and damaged["backup"] == ""
    copy = tmp_path / "library.db.v9.bak"
    copy.write_bytes(b"copia")
    assert mn.describe_failure(path, error)["backup"] == str(copy)
    assert mn.describe_failure(path, sqlite3.OperationalError("database is locked"))["kind"] == "locked"
    other = mn.describe_failure(path, ValueError("boom"), before=9)
    assert other["kind"] == "other" and other["details"] == "ValueError: boom" and other["backup"] == str(copy)
