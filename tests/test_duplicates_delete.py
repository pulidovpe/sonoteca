"""Duplicados (archivos idénticos, con cualquier nombre) y borrado seguro a la papelera."""
import shutil
import sqlite3

from sonoteca.core import duplicates, file_delete, library
from sonoteca.core.db import connect


def _library(tmp_path):
    conn = connect(tmp_path / "d.db")
    conn.row_factory = sqlite3.Row
    artist = conn.execute("INSERT INTO artists (name, sort_name) VALUES ('Banda', 'banda')").lastrowid
    album = conn.execute("INSERT INTO albums (title, album_artist_id) VALUES ('Disco', ?)", (artist,)).lastrowid
    return conn, artist, album


def _file(conn, tmp_path, folder, name, content, artist, album, title="Canción", duration=200.2, bitrate=192,
          inferred=0, has_cover=0, mtime=1):
    path = tmp_path / folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    fid = conn.execute("INSERT INTO files (path, size, mtime_ns, format, kind) VALUES (?, ?, ?, 'mp3', 'audio')",
                       (str(path), len(content), mtime)).lastrowid
    return conn.execute(
        "INSERT INTO tracks (file_id, album_id, artist_id, title, duration, bitrate, inferred, has_cover)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (fid, album, artist, title, duration, bitrate, inferred, has_cover)).lastrowid


def _fake_trash(tmp_path):
    bin_dir = tmp_path / "papelera"
    bin_dir.mkdir(exist_ok=True)
    moved = []

    def trash(path):
        target = bin_dir / f"{len(moved)}-{path.split('/')[-1]}"
        shutil.move(path, target)
        moved.append(path)
        return True
    trash.moved = moved
    return trash


def test_duplicates_are_identical_files_whatever_their_name_folder_or_tags(tmp_path):
    conn, artist, album = _library(tmp_path)
    a = _file(conn, tmp_path, "uno", "cancion.mp3", b"x" * 100, artist, album)
    b = _file(conn, tmp_path, "dos", "cancion.mp3", b"x" * 100, artist, album)
    renamed = _file(conn, tmp_path, "tres", "otro-nombre (1).mp3", b"x" * 100, artist, album)
    retagged = _file(conn, tmp_path, "cuatro", "01 - Sin tags.mp3", b"x" * 100, artist, album,
                     title="Otro título", duration=0, inferred=1)
    _file(conn, tmp_path, "cinco", "cancion.mp3", b"x" * 101, artist, album)                  # otro tamaño: no es igual
    _file(conn, tmp_path, "seis", "cancion.mp3", b"y" * 100, artist, album)                   # mismo tamaño, otro contenido
    _file(conn, tmp_path, "siete", "unica.mp3", b"z" * 77, artist, album)                     # tamaño único: ni se lee
    conn.commit()
    groups = duplicates.find_groups(conn)
    assert len(groups) == 1 and {m.track_id for m in groups[0]} == {a, b, renamed, retagged}


def test_missing_files_are_not_listed_because_they_cannot_be_verified(tmp_path):
    conn, artist, album = _library(tmp_path)
    _file(conn, tmp_path, "a", "t.mp3", b"k" * 30, artist, album)
    gone = _file(conn, tmp_path, "b", "t2.mp3", b"k" * 30, artist, album)
    conn.commit()
    (tmp_path / "b" / "t2.mp3").unlink()
    assert gone and duplicates.find_groups(conn) == []


def test_best_copy_is_kept_first(tmp_path):
    conn, artist, album = _library(tmp_path)
    inferred = _file(conn, tmp_path, "a", "t.mp3", b"y" * 50, artist, album, inferred=1, bitrate=320)
    tagged = _file(conn, tmp_path, "b", "t.mp3", b"y" * 50, artist, album, inferred=0, bitrate=128)
    cover_old = _file(conn, tmp_path, "c", "t.mp3", b"y" * 50, artist, album, inferred=0, bitrate=128, has_cover=1, mtime=5)
    cover_older = _file(conn, tmp_path, "d", "t.mp3", b"y" * 50, artist, album, inferred=0, bitrate=128, has_cover=1, mtime=2)
    conn.commit()
    order = [m.track_id for m in duplicates.find_groups(conn)[0]]
    assert order == [cover_older, cover_old, tagged, inferred]      # tags reales, portada, bitrate, más antigua


def test_delete_one_file_moves_it_to_the_trash_and_removes_it_from_the_library(tmp_path):
    conn, artist, album = _library(tmp_path)
    t = _file(conn, tmp_path, "a", "t.mp3", b"z" * 10, artist, album)
    conn.commit()
    trash = _fake_trash(tmp_path)
    ok, _msg = file_delete.delete_track(conn, t, trash)
    assert ok and not (tmp_path / "a" / "t.mp3").exists() and len(list((tmp_path / "papelera").iterdir())) == 1
    assert conn.execute("SELECT COUNT(*) FROM tracks").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM albums").fetchone()[0] == 0          # el álbum vacío se limpia


def test_a_failed_trash_changes_nothing(tmp_path):
    conn, artist, album = _library(tmp_path)
    t = _file(conn, tmp_path, "a", "t.mp3", b"z" * 10, artist, album)
    conn.commit()
    ok, msg = file_delete.delete_track(conn, t, lambda path: False)
    assert not ok and "papelera" in msg and (tmp_path / "a" / "t.mp3").exists()
    assert conn.execute("SELECT COUNT(*) FROM tracks").fetchone()[0] == 1


def test_batch_deletes_only_verified_identical_copies_and_never_the_kept_one(tmp_path):
    conn, artist, album = _library(tmp_path)
    keep = _file(conn, tmp_path, "a", "t.mp3", b"q" * 40, artist, album)
    same = _file(conn, tmp_path, "b", "t.mp3", b"q" * 40, artist, album)
    differs = _file(conn, tmp_path, "c", "t.mp3", b"r" * 40, artist, album)          # mismo tamaño pero otro contenido
    conn.commit()
    trash = _fake_trash(tmp_path)
    out = file_delete.delete_duplicates(conn, [{"keep": keep, "remove": [same, differs, keep]}], trash)
    assert out["deleted"] == [same] and out["bytes"] == 40
    reasons = dict(out["skipped"])
    assert "idéntico" in reasons[differs] and "conserva" in reasons[keep]
    assert (tmp_path / "a" / "t.mp3").exists() and (tmp_path / "c" / "t.mp3").exists() and not (tmp_path / "b" / "t.mp3").exists()
    assert trash.moved == [str(tmp_path / "b" / "t.mp3")]


def test_batch_does_nothing_when_the_kept_copy_is_missing(tmp_path):
    conn, artist, album = _library(tmp_path)
    keep = _file(conn, tmp_path, "a", "t.mp3", b"q" * 40, artist, album)
    other = _file(conn, tmp_path, "b", "t.mp3", b"q" * 40, artist, album)
    conn.commit()
    (tmp_path / "a" / "t.mp3").unlink()
    out = file_delete.delete_duplicates(conn, [{"keep": keep, "remove": [other]}], _fake_trash(tmp_path))
    assert out["deleted"] == [] and (tmp_path / "b" / "t.mp3").exists()


def test_files_without_duration_are_listed_for_review_as_possibly_damaged(tmp_path):
    conn, artist, album = _library(tmp_path)
    healthy = _file(conn, tmp_path, "a", "ok.mp3", b"1" * 5, artist, album)
    broken = _file(conn, tmp_path, "b", "roto.mp3", b"2" * 5, artist, album, duration=0)
    conn.commit()
    listed = {r["id"]: r["damaged"] for r in library.list_incomplete(conn)}
    assert broken in listed and listed[broken] == 1 and healthy not in listed
