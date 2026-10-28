"""Exportar / importar la biblioteca."""
import json
import sqlite3
import zipfile

import pytest

from sonoteca.core import portable
from sonoteca.core.db import connect


def _library(data, music_root):
    data.mkdir(parents=True, exist_ok=True)
    conn = connect(data / "library.db")
    conn.execute("INSERT INTO artists (name, sort_name) VALUES ('A', 'a')")
    conn.execute("INSERT INTO albums (title, album_artist_id, cover_path) VALUES ('X', 1, ?)",
                 (str(data / "covers" / "chosen" / "c.jpg"),))
    for n in (1, 2):
        fid = conn.execute("INSERT INTO files (path, size, mtime_ns, format, kind) VALUES (?, 1, 1, 'mp3', 'audio')",
                           (str(music_root / "Rock" / f"{n}.mp3"),)).lastrowid
        conn.execute("INSERT INTO tracks (file_id, album_id, artist_id, title, duration) VALUES (?, 1, 1, ?, 1)",
                     (fid, f"T{n}"))
    conn.execute("INSERT INTO playlists (name) VALUES ('Mi lista')") if _has(conn, "playlists") else None
    conn.commit()
    conn.close()
    (data / "covers" / "chosen").mkdir(parents=True)
    (data / "covers" / "chosen" / "c.jpg").write_bytes(b"cover")
    (data / "artists").mkdir()
    (data / "artists" / "1.jpg").write_bytes(b"foto")
    (data / "online.json").write_text('{"contact": "yo@correo.com"}')


def _has(conn, table):
    return conn.execute("SELECT 1 FROM sqlite_master WHERE name = ?", (table,)).fetchone() is not None


def test_export_has_manifest_db_images_and_no_settings(tmp_path):
    data = tmp_path / "d1"
    _library(data, tmp_path / "Music")
    out = tmp_path / "salida" / "mi.sonoteca"
    manifest = portable.export_library(data / "library.db", out, data=data)
    assert manifest["tracks"] == 2 and manifest["albums"] == 1 and manifest["music_root"] == str(tmp_path / "Music" / "Rock")
    with zipfile.ZipFile(out) as z:
        names = set(z.namelist())
    assert names == {"manifest.json", "library.db", "covers/chosen/c.jpg", "artists/1.jpg"}   # sin ajustes ni claves
    assert portable.inspect_bundle(out)["version"] == manifest["version"]


def test_import_replaces_library_after_backup_and_remaps_paths(tmp_path):
    src, music = tmp_path / "origen", tmp_path / "Music"
    _library(src, music)
    bundle = tmp_path / "x.sonoteca"
    portable.export_library(src / "library.db", bundle, data=src)

    dest = tmp_path / "destino"                       # otro equipo: otra carpeta de datos y de música
    dest.mkdir()
    connect(dest / "library.db").close()              # biblioteca previa (vac\u00eda) que debe respaldarse
    (dest / "online.json").write_text("{}")
    new_music = tmp_path / "Otra" / "Musica"
    portable.stage_import(bundle, str(new_music), data=dest)
    assert portable.has_pending_import(dest)
    assert (dest / "library.db").stat().st_size > 0 and not (dest / "artists").exists()   # a\u00fan no se aplic\u00f3

    report = portable.apply_pending_import(dest)
    assert report["remapped"] == 2 and report["cover_paths"] == 1 and report["missing"] == 2
    assert not portable.has_pending_import(dest) and (dest / "backups").is_dir()
    assert (dest / "artists" / "1.jpg").read_bytes() == b"foto"
    conn = sqlite3.connect(dest / "library.db")
    assert {r[0] for r in conn.execute("SELECT path FROM files")} == {str(new_music / "1.mp3"),
                                                                     str(new_music / "2.mp3")}   # sustituye la carpeta común
    assert conn.execute("SELECT cover_path FROM albums").fetchone()[0] == str(dest / "covers" / "chosen" / "c.jpg")
    assert (dest / "online.json").exists()           # los ajustes locales no se tocan
    assert portable.apply_pending_import(dest) is None


def test_inspect_rejects_foreign_and_unsafe_archives(tmp_path):
    with pytest.raises(portable.PortableError):
        portable.inspect_bundle(tmp_path / "no-existe.sonoteca")
    bad = tmp_path / "malo.sonoteca"
    with zipfile.ZipFile(bad, "w") as z:
        z.writestr("../evil.txt", "x")
    with pytest.raises(portable.PortableError):
        portable.inspect_bundle(bad)
    newer = tmp_path / "nuevo.sonoteca"
    with zipfile.ZipFile(newer, "w") as z:
        z.writestr("manifest.json", json.dumps({"app": "sonoteca", "format": 1, "schema": 999}))
        z.writestr("library.db", b"")
    with pytest.raises(portable.PortableError, match="m\u00e1s nueva"):
        portable.inspect_bundle(newer)


def test_check_bundle_flags_personal_data_only(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("check_bundle", "packaging/check_bundle.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    clean = tmp_path / "clean"
    (clean / "sonoteca" / "ui" / "qml").mkdir(parents=True)
    (clean / "sonoteca" / "ui" / "qml" / "Main.qml").write_text("x")
    (clean / "libQt6Core.dylib").write_bytes(b"x")
    assert mod.find_personal_data(clean) == []
    dirty = tmp_path / "dirty"
    (dirty / "data" / "covers" / "chosen").mkdir(parents=True)
    (dirty / "data" / "covers" / "chosen" / "a.jpg").write_bytes(b"x")
    (dirty / "library.db").write_bytes(b"x")
    assert len(mod.find_personal_data(dirty)) == 2


def test_cli_export_then_import_roundtrip(tmp_path, monkeypatch, capsys=None):
    import io
    import sys

    from sonoteca import cli
    data = tmp_path / "datos"
    monkeypatch.setenv("SONOTECA_DATA_DIR", str(data))
    monkeypatch.setenv("SONOTECA_CACHE_DIR", str(tmp_path / "cache"))
    _library(data, tmp_path / "Music")
    dest = tmp_path / "copia"
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        assert cli.main(["export", str(dest)]) == 0
        assert (tmp_path / "copia.sonoteca").exists()
        (data / "library.db").unlink()
        connect(data / "library.db").close()               # biblioteca vac\u00eda
        assert cli.main(["import", str(tmp_path / "copia.sonoteca")]) == 0
    finally:
        sys.stdout = old
    n = sqlite3.connect(data / "library.db").execute("SELECT COUNT(*) FROM tracks").fetchone()[0]
    assert n == 2 and "Importado: 2 canciones" in buf.getvalue()


def test_reset_backs_up_and_clears_library_but_keeps_settings(tmp_path):
    data, cache = tmp_path / "d", tmp_path / "c"
    _library(data, tmp_path / "Music")
    (data / "settings.json").write_text('{"offline": false}')
    cache.mkdir()
    (cache / "thumb.png").write_bytes(b"t")
    portable.stage_reset(True, data=data)
    assert portable.has_pending_reset(data) and (data / "library.db").exists()      # aún no se aplicó
    report = portable.apply_pending_reset(data, cache)
    assert not portable.has_pending_reset(data)
    assert not (data / "library.db").exists() and not (data / "artists").exists() and not cache.exists()
    assert (data / "settings.json").exists()                                         # los ajustes se conservan
    backup = tmp_path / "d" / "backups"
    assert report["backup"] and (next(backup.iterdir()) / "library.db").exists()
    assert (next(backup.iterdir()) / "covers" / "chosen" / "c.jpg").exists()
    assert portable.apply_pending_reset(data, cache) is None


def test_reset_without_backup_and_import_cancels_pending_reset(tmp_path):
    data = tmp_path / "d"
    _library(data, tmp_path / "Music")
    portable.stage_reset(False, data=data)
    report = portable.apply_pending_reset(data, tmp_path / "c")
    assert report["backup"] == "" and not (data / "backups").exists() and not (data / "library.db").exists()
    # un «empezar de cero» pendiente se anula si después se prepara una importación
    src = tmp_path / "o"
    _library(src, tmp_path / "Music")
    bundle = tmp_path / "x.sonoteca"
    portable.export_library(src / "library.db", bundle, data=src)
    portable.stage_reset(True, data=data)
    portable.stage_import(bundle, data=data)
    assert not portable.has_pending_reset(data) and portable.has_pending_import(data)
