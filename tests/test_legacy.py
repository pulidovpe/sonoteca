"""Migración desde las carpetas «musicapp» a «sonoteca»."""
import sqlite3

from sonoteca.core import legacy
from sonoteca.core.db import connect


def _old_library(old_data):
    old_data.mkdir(parents=True)
    conn = connect(old_data / "library.db")
    conn.execute("INSERT INTO artists (name, sort_name) VALUES ('A', 'a')")
    conn.execute("INSERT INTO albums (title, album_artist_id, cover_path) VALUES "
                 "('X', 1, ?), ('Y', 1, '/otra/parte/portada.jpg')",
                 (str(old_data / "covers" / "chosen" / "abc.jpg"),))
    conn.commit()
    conn.close()
    (old_data / "covers" / "chosen").mkdir(parents=True)
    (old_data / "covers" / "chosen" / "abc.jpg").write_bytes(b"img")
    (old_data / "artists").mkdir()
    (old_data / "artists" / "1.jpg").write_bytes(b"foto")


def test_migrate_moves_data_and_rewrites_cover_paths(tmp_path):
    old, new = tmp_path / "old" / "musicapp", tmp_path / "new" / "sonoteca"
    old_cache, new_cache = tmp_path / "oldc", tmp_path / "newc"
    _old_library(old)
    old_cache.mkdir()
    (old_cache / "thumb.png").write_bytes(b"t")
    rep = legacy.migrate([old], [old_cache], new, new_cache, keyring_too=False)
    assert rep.migrated and not rep.errors and rep.rewritten_paths == 1
    assert not old.exists()                                  # se MUEVE: no queda copia
    assert (new / "library.db").exists() and (new / "artists" / "1.jpg").read_bytes() == b"foto"
    assert (new_cache / "thumb.png").exists()
    rows = dict(sqlite3.connect(new / "library.db").execute("SELECT title, cover_path FROM albums"))
    assert rows["X"] == str(new / "covers" / "chosen" / "abc.jpg")
    assert rows["Y"] == "/otra/parte/portada.jpg"            # lo que no era de la carpeta antigua no se toca
    assert (new / "covers" / "chosen" / "abc.jpg").exists()


def test_migrate_never_overwrites_an_existing_new_library(tmp_path):
    old, new = tmp_path / "old", tmp_path / "new"
    _old_library(old)
    connect(new / "library.db").close()
    rep = legacy.migrate([old], [], new, tmp_path / "c", keyring_too=False)
    assert not rep.migrated and rep.skipped and (old / "library.db").exists()


def test_migrate_with_nothing_to_move_is_a_noop(tmp_path):
    rep = legacy.migrate([tmp_path / "no-existe"], [], tmp_path / "new", tmp_path / "c", keyring_too=False)
    assert not rep.migrated and not rep.errors and not (tmp_path / "new").exists()
