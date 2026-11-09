"""Listas de reproducción a partir de carpetas de la biblioteca. No necesita ffmpeg."""
import re
from pathlib import Path

from sonoteca.core import folder_lists as fl
from sonoteca.core import library_folders as lf
from sonoteca.core import playlists, scanner
from sonoteca.core.db import connect
from sonoteca.core.models import TrackMeta


def _fake_read_tags(path: Path) -> TrackMeta:
    m = re.match(r"(\d+)", path.stem)
    return TrackMeta(path=path, format="mp3", kind="audio", title=path.stem, artist=path.parent.parent.name,
                     album_artist=path.parent.parent.name, album=path.parent.name, duration=5.0,
                     track_no=int(m.group(1)) if m else None)


def _lib(tmp_path, monkeypatch):
    monkeypatch.setattr(scanner, "read_tags", _fake_read_tags)
    root = tmp_path / "Musica"
    for rel in ("Beatles/Abbey/10.mp3", "Beatles/Abbey/2.mp3", "Beatles/Revolver/1.mp3", "Soda/Signos/1.mp3",
                "Soda/Signos/sin_numero.mp3", "Suelta/x.mp3"):
        f = root / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"x")
    conn = connect(tmp_path / "f.db")
    scanner.scan(conn, root)
    return conn, root.resolve()


def _titles(conn, ids):
    return [conn.execute("SELECT title FROM tracks WHERE id = ?", (i,)).fetchone()[0] for i in ids]


def test_candidates_include_branching_parents_but_not_single_chains(tmp_path, monkeypatch):
    conn, root = _lib(tmp_path, monkeypatch)
    paths = {c["path"]: c for c in lf.list_candidates(conn)}
    assert str(root) in paths and paths[str(root)]["tracks"] == 0 and paths[str(root)]["total"] == 6   # raíz: se bifurca
    assert str(root / "Beatles") in paths and paths[str(root / "Beatles")]["total"] == 3                  # carpeta madre
    assert str(root / "Soda") not in paths                          # solo una rama (Signos): daría la misma lista
    assert str(root / "Suelta") in paths and paths[str(root / "Suelta")]["hasChildren"] is False
    assert paths[str(root / "Beatles")]["depth"] == 1 and paths[str(root / "Beatles" / "Abbey")]["depth"] == 2
    assert paths[str(root / "Beatles" / "Abbey")]["name"] == "Abbey"


def test_folder_order_is_by_disc_and_track_number_then_name_not_alphabetical(tmp_path, monkeypatch):
    conn, root = _lib(tmp_path, monkeypatch)
    assert _titles(conn, fl.folder_track_ids(conn, str(root / "Beatles" / "Abbey"), False)) == ["2", "10"]
    assert _titles(conn, fl.folder_track_ids(conn, str(root / "Soda" / "Signos"), False)) == ["1", "sin_numero"]


def test_subfolders_option_and_order_by_folder(tmp_path, monkeypatch):
    conn, root = _lib(tmp_path, monkeypatch)
    beatles = str(root / "Beatles")
    assert fl.folder_track_ids(conn, beatles, False) == []                      # sin música propia
    ids = fl.folder_track_ids(conn, beatles, True)
    assert _titles(conn, ids) == ["2", "10", "1"]                               # Abbey antes que Revolver


def test_plan_detects_name_conflicts_with_existing_lists_and_within_the_batch(tmp_path, monkeypatch):
    conn, root = _lib(tmp_path, monkeypatch)
    playlists.create(conn, "abbey")                                             # sin distinguir mayúsculas
    other = root / "Otro" / "Abbey"
    other.mkdir(parents=True)
    (other / "9.mp3").write_bytes(b"x")
    scanner.scan(conn, root)
    items = [{"path": str(root / "Beatles" / "Abbey"), "sub": False}, {"path": str(other), "sub": False},
             {"path": str(root / "Suelta"), "sub": False}, {"path": str(root / "Soda"), "sub": False}]
    result = {Path(p["path"]).name: p for p in fl.plan(conn, items)}
    assert result["Abbey"]["conflict"] == "existing" and result["Suelta"]["conflict"] == ""
    assert "Soda" not in result                                                 # sin canciones propias y sin subcarpetas
    second = [p for p in fl.plan(conn, items[1:2] + items[:1]) if p["path"] == str(other)][0]
    assert second["conflict"] == "existing"


def test_apply_create_rename_append_and_skip(tmp_path, monkeypatch):
    conn, root = _lib(tmp_path, monkeypatch)
    existing = playlists.create(conn, "Abbey")
    playlists.add_tracks(conn, existing, fl.folder_track_ids(conn, str(root / "Beatles" / "Abbey"), False)[:1])
    abbey, rev, suelta, signos = (str(root / "Beatles" / "Abbey"), str(root / "Beatles" / "Revolver"),
                                  str(root / "Suelta"), str(root / "Soda" / "Signos"))
    out = fl.apply(conn, [
        {"path": abbey, "sub": False, "name": "Abbey", "mode": "append"},
        {"path": rev, "sub": False, "name": "Revolver", "mode": "create"},
        {"path": suelta, "sub": False, "name": "Suelta", "mode": "skip"},
        {"path": signos, "sub": False, "name": "Abbey", "mode": "rename"},
    ])
    assert out["errors"] == [] and out["skipped"] == 1
    assert out["appended"] == [{"id": existing, "name": "Abbey", "added": 1}]   # la pista ya presente no se repite
    assert [c["name"] for c in out["created"]] == ["Revolver", "Abbey (2)"]
    names = {r["name"] for r in playlists.list_playlists(conn)}
    assert names == {"Abbey", "Revolver", "Abbey (2)"}
    assert len(playlists.track_ids(conn, existing)) == 2


def test_apply_with_subfolders_makes_one_list_with_everything(tmp_path, monkeypatch):
    conn, root = _lib(tmp_path, monkeypatch)
    out = fl.apply(conn, [{"path": str(root / "Beatles"), "sub": True, "name": "Beatles", "mode": "create"}])
    assert out["created"][0]["added"] == 3
    assert len(playlists.track_ids(conn, out["created"][0]["id"])) == 3


def test_append_to_a_missing_list_creates_it_and_unique_name_respects_the_limit(tmp_path, monkeypatch):
    conn, root = _lib(tmp_path, monkeypatch)
    out = fl.apply(conn, [{"path": str(root / "Suelta"), "sub": False, "name": "Suelta", "mode": "append"}])
    assert [c["name"] for c in out["created"]] == ["Suelta"]
    long_name = "x" * playlists.MAX_NAME
    playlists.create(conn, long_name)
    assert len(fl.unique_name(conn, long_name)) <= playlists.MAX_NAME and fl.unique_name(conn, long_name).endswith(" (2)")


def test_files_are_never_touched(tmp_path, monkeypatch):
    conn, root = _lib(tmp_path, monkeypatch)
    before = sorted(p.name for p in root.rglob("*.mp3"))
    fl.apply(conn, [{"path": str(root), "sub": True, "name": "Todo", "mode": "create"}])
    assert sorted(p.name for p in root.rglob("*.mp3")) == before


def test_plan_marks_same_named_folders_in_one_batch(tmp_path, monkeypatch):
    conn, root = _lib(tmp_path, monkeypatch)
    other = root / "Otro" / "Abbey"
    other.mkdir(parents=True)
    (other / "9.mp3").write_bytes(b"x")
    scanner.scan(conn, root)
    result = fl.plan(conn, [{"path": str(root / "Beatles" / "Abbey"), "sub": False}, {"path": str(other), "sub": False}])
    assert [p["conflict"] for p in result] == ["", "batch"]
