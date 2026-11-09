"""Registro de carpetas con música y exclusiones (quitar de la biblioteca sin tocar el disco). No necesita ffmpeg."""
from pathlib import Path

from sonoteca.core import library_folders as lf
from sonoteca.core import scanner
from sonoteca.core.db import SCHEMA_VERSION, connect
from sonoteca.core.models import TrackMeta


def _fake_read_tags(path: Path) -> TrackMeta:
    artist, album = path.parent.parent.name, path.parent.name
    return TrackMeta(path=path, format="mp3", kind="audio", title=path.stem, artist=artist,
                     album_artist=artist, album=album, duration=10.0)


def _lib(tmp_path, monkeypatch):
    monkeypatch.setattr(scanner, "read_tags", _fake_read_tags)
    root = tmp_path / "Musica"
    for rel in ("Beatles/Abbey/a.mp3", "Beatles/Abbey/b.mp3", "Beatles/Revolver/c.mp3", "Soda/Signos/d.mp3"):
        f = root / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"x")
    conn = connect(tmp_path / "l.db")
    return conn, root


def _paths(conn):
    return sorted(r["path"] for r in conn.execute("SELECT path FROM files"))


def test_schema_v9_tables(tmp_path):
    conn = connect(tmp_path / "x.db")
    assert SCHEMA_VERSION >= 9
    assert conn.execute("SELECT COUNT(*) FROM library_folders").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM excluded_paths").fetchone()[0] == 0


def test_migration_backfills_folders_from_existing_files(tmp_path):
    conn = connect(tmp_path / "m.db")
    conn.execute("INSERT INTO files (path, size, mtime_ns, format, kind) VALUES ('/m/A/x.mp3', 1, 1, 'mp3', 'audio')")
    conn.execute("DROP TABLE library_folders")
    conn.execute("DROP TABLE excluded_paths")
    conn.execute("PRAGMA user_version = 8")
    conn.commit()
    from sonoteca.core.db import migrate
    migrate(conn)
    assert [r["path"] for r in conn.execute("SELECT path FROM library_folders")] == ["/m/A"]


def test_scan_registers_folders_with_music(tmp_path, monkeypatch):
    conn, root = _lib(tmp_path, monkeypatch)
    scanner.scan(conn, root)
    assert {f["path"] for f in lf.list_folders(conn)} == {
        str(root.resolve() / "Beatles/Abbey"), str(root.resolve() / "Beatles/Revolver"),
        str(root.resolve() / "Soda/Signos")}
    abbey = [f for f in lf.list_folders(conn) if f["path"].endswith("Abbey")][0]
    assert abbey["tracks"] == 2 and abbey["total"] == 2


def test_rescan_forgets_folders_that_lost_their_music(tmp_path, monkeypatch):
    conn, root = _lib(tmp_path, monkeypatch)
    scanner.scan(conn, root)
    (root / "Soda/Signos/d.mp3").unlink()
    scanner.scan(conn, root)
    assert not any(f["path"].endswith("Signos") for f in lf.list_folders(conn))
    assert not conn.execute("SELECT 1 FROM library_folders WHERE path LIKE '%Signos'").fetchone()


def test_exclude_folder_removes_everything_inside_and_keeps_disk(tmp_path, monkeypatch):
    conn, root = _lib(tmp_path, monkeypatch)
    scanner.scan(conn, root)
    beatles = str(root.resolve() / "Beatles")
    result = lf.exclude_folder(conn, beatles)
    assert result["removed"] == 3 and result["pruned"] >= 2   # 3 pistas; álbumes y artista quedan vacíos
    assert _paths(conn) == [str(root.resolve() / "Soda/Signos/d.mp3")]
    assert (root / "Beatles/Abbey/a.mp3").exists()               # el disco no se toca
    assert [f["path"] for f in lf.list_folders(conn)] == [str(root.resolve() / "Soda/Signos")]
    assert [e["path"] for e in lf.list_excluded(conn)] == [beatles]
    assert conn.execute("SELECT COUNT(*) FROM artists").fetchone()[0] == 1


def test_excluded_folder_does_not_come_back_on_rescan_until_included_again(tmp_path, monkeypatch):
    conn, root = _lib(tmp_path, monkeypatch)
    scanner.scan(conn, root)
    beatles = str(root.resolve() / "Beatles")
    lf.exclude_folder(conn, beatles)
    again = scanner.scan(conn, root)
    assert again.added == 0 and len(_paths(conn)) == 1
    assert lf.include_again(conn, beatles) is True
    assert lf.list_excluded(conn) == []
    assert scanner.scan(conn, root).added == 3
    assert len(_paths(conn)) == 4


def test_scanning_an_excluded_root_does_nothing_and_removes_nothing(tmp_path, monkeypatch):
    conn, root = _lib(tmp_path, monkeypatch)
    scanner.scan(conn, root)
    lf.exclude_folder(conn, str(root.resolve() / "Soda"))
    result = scanner.scan(conn, root / "Soda")
    assert result.root_excluded is True and result.added == 0 and result.removed == 0
    assert len(_paths(conn)) == 3


def test_exclude_tracks_removes_files_and_survives_rescan(tmp_path, monkeypatch):
    conn, root = _lib(tmp_path, monkeypatch)
    scanner.scan(conn, root)
    tid = conn.execute("SELECT t.id FROM tracks t JOIN files f ON f.id = t.file_id WHERE f.path LIKE '%a.mp3'").fetchone()[0]
    assert lf.exclude_files(conn, [tid])["removed"] == 1
    scanner.scan(conn, root)
    assert not any(p.endswith("a.mp3") for p in _paths(conn)) and len(_paths(conn)) == 3
    assert (root / "Beatles/Abbey/a.mp3").exists()


def test_exclusion_prefix_does_not_catch_sibling_with_same_start(tmp_path, monkeypatch):
    conn, root = _lib(tmp_path, monkeypatch)
    sib = root / "Beatles Live/Show/z.mp3"
    sib.parent.mkdir(parents=True)
    sib.write_bytes(b"x")
    scanner.scan(conn, root)
    lf.exclude_folder(conn, str(root.resolve() / "Beatles"))
    assert any(p.endswith("z.mp3") for p in _paths(conn))


def test_playlist_entries_leave_with_the_removed_tracks(tmp_path, monkeypatch):
    conn, root = _lib(tmp_path, monkeypatch)
    scanner.scan(conn, root)
    tids = [r[0] for r in conn.execute("SELECT id FROM tracks ORDER BY id")]
    conn.execute("INSERT INTO playlists (name) VALUES ('L')")
    pid = conn.execute("SELECT id FROM playlists").fetchone()[0]
    for pos, t in enumerate(tids):
        conn.execute("INSERT INTO playlist_tracks (playlist_id, track_id, position) VALUES (?,?,?)", (pid, t, pos))
    conn.commit()
    lf.exclude_folder(conn, str(root.resolve() / "Soda"))
    assert conn.execute("SELECT COUNT(*) FROM playlist_tracks").fetchone()[0] == 3
