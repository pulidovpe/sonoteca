import hashlib
import sys

import pytest
from conftest import make_cover, make_mp3, needs_ffmpeg

from sonoteca.cli import main
from sonoteca.core import cover_store, library, paths, tag_edit
from sonoteca.core.covers import extract_embedded_cover
from sonoteca.core.db import connect
from sonoteca.core.scanner import scan
from sonoteca.core.tags import read_tags


@pytest.fixture
def datadir(tmp_path, monkeypatch):
    monkeypatch.setenv("SONOTECA_DATA_DIR", str(tmp_path / "datos"))
    return tmp_path / "datos"


def jpeg(tmp_path, color, name):
    return make_cover(tmp_path / name, color).read_bytes()


@needs_ffmpeg
def test_store_chosen_is_content_addressed_and_idempotent(tmp_path, datadir):
    data = jpeg(tmp_path, "0xcc3333", "a.jpg")
    first = cover_store.store_chosen(data)
    second = cover_store.store_chosen(data)
    assert first == second and first.parent == datadir / "covers" / "chosen"
    assert first.name == hashlib.sha1(data).hexdigest() + ".jpg"
    assert first.read_bytes() == data
    assert [p.name for p in first.parent.iterdir()] == [first.name]  # sin temporales ni duplicados
    with pytest.raises(ValueError):
        cover_store.store_chosen(b"no es una imagen")


@needs_ffmpeg
def test_archive_previous_writes_manifest_and_dedupes(tmp_path, datadir):
    data = jpeg(tmp_path, "0x3366cc", "a.jpg")
    a = cover_store.archive_previous(tmp_path / "x/1.mp3", data)
    b = cover_store.archive_previous(tmp_path / "x/2.mp3", data)
    assert a == b and a.parent == datadir / "covers" / "previous"
    lines = (a.parent / "manifest.tsv").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2  # una línea por archivo: fecha, ruta de origen, imagen archivada
    assert lines[0].split("\t")[1].endswith("1.mp3") and lines[1].split("\t")[1].endswith("2.mp3")
    assert all(line.split("\t")[2] == a.name for line in lines)


@pytest.fixture
def library_with_cover(tmp_path, datadir):
    old = make_cover(tmp_path / "old.jpg", "0xcc3333")
    root = tmp_path / "music"
    make_mp3(root / "A/1.mp3", old, title="Uno", artist="X", album="Disco")
    make_mp3(root / "A/2.mp3", title="Dos", artist="X", album="Disco")  # sin portada previa
    conn = connect(tmp_path / "t.db")
    scan(conn, root)
    ids = [r["id"] for r in library.list_tracks(conn)]
    new = make_cover(tmp_path / "new.jpg", "0x33cc33")
    return conn, root, ids, old, new


@needs_ffmpeg
def test_edit_with_cover_keeps_a_copy_of_the_chosen_and_the_replaced_cover(
        library_with_cover, datadir):
    conn, root, ids, old, new = library_with_cover
    old_bytes, new_bytes = old.read_bytes(), new.read_bytes()
    res = tag_edit.apply_edit(conn, ids, {}, str(new), backup=False)
    assert res.updated == 2 and res.failed == []
    # la imagen elegida tiene copia propia (sigue existiendo aunque se borre el original)
    new.unlink()
    chosen = list((datadir / "covers" / "chosen").iterdir())
    assert [p.read_bytes() for p in chosen] == [new_bytes]
    # la portada anterior del archivo que la tenía quedó archivada; el que no tenía no genera nada
    prev = list((datadir / "covers" / "previous").glob("*.jpg"))
    assert len(prev) == 1 and prev[0].read_bytes() == old_bytes
    manifest = (datadir / "covers" / "previous" / "manifest.tsv").read_text(encoding="utf-8")
    assert "1.mp3" in manifest and "2.mp3" not in manifest
    # y los archivos ya tienen la portada nueva
    assert extract_embedded_cover(root / "A/1.mp3") == new_bytes
    assert read_tags(root / "A/2.mp3").has_cover is True


@needs_ffmpeg
def test_if_archiving_fails_the_file_is_left_untouched(library_with_cover, monkeypatch):
    conn, root, ids, _old, new = library_with_cover
    before = (root / "A/1.mp3").read_bytes()

    def boom(path):
        raise OSError("disco lleno")

    monkeypatch.setattr(cover_store, "archive_embedded", boom)
    res = tag_edit.apply_edit(conn, ids[:1], {}, str(new), backup=False)
    assert res.updated == 0 and "disco lleno" in res.failed[0][1]
    assert (root / "A/1.mp3").read_bytes() == before


def test_no_cover_means_nothing_is_stored(tmp_path, datadir):
    root = tmp_path / "music"
    make_mp3(root / "a.mp3", title="T", artist="A", album="B")
    conn = connect(tmp_path / "t.db")
    scan(conn, root)
    tag_edit.apply_edit(conn, [r["id"] for r in library.list_tracks(conn)], {"genre": "Rock"},
                        backup=False)
    assert not (datadir / "covers").exists()


def test_data_and_cache_never_default_inside_a_virtualenv(tmp_path, monkeypatch):
    venv = tmp_path / "repo" / ".venv"
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delenv("SONOTECA_DATA_DIR", raising=False)
    monkeypatch.delenv("SONOTECA_CACHE_DIR", raising=False)
    monkeypatch.setattr(sys, "prefix", str(venv))
    monkeypatch.setattr(sys, "base_prefix", "/usr")
    monkeypatch.setattr(paths, "user_data_dir", lambda *a, **k: str(venv / "share" / "sonoteca"))
    monkeypatch.setattr(paths, "user_cache_dir", lambda *a, **k: str(venv / "cache" / "sonoteca"))
    assert paths.data_dir() == tmp_path / "home" / ".sonoteca" / "data"
    assert paths.cache_dir() == tmp_path / "home" / ".sonoteca" / "cache"
    assert paths.covers_dir() == tmp_path / "home" / ".sonoteca" / "data" / "covers"
    # una ruta fijada a propósito con la variable de entorno se respeta
    monkeypatch.setenv("SONOTECA_DATA_DIR", str(venv / "mis_datos"))
    assert paths.data_dir() == venv / "mis_datos"


def test_standard_dirs_are_untouched_outside_a_virtualenv(tmp_path, monkeypatch):
    monkeypatch.delenv("SONOTECA_DATA_DIR", raising=False)
    monkeypatch.setattr(sys, "prefix", "/usr")
    monkeypatch.setattr(sys, "base_prefix", "/usr")  # sin venv: nada que corregir
    monkeypatch.setattr(paths, "user_data_dir", lambda *a, **k: str(tmp_path / "std"))
    assert paths.data_dir() == tmp_path / "std"


def test_cli_paths_shows_the_covers_folder(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("SONOTECA_DATA_DIR", str(tmp_path / "datos"))
    assert main(["paths"]) == 0
    out = capsys.readouterr().out
    assert "Portadas guardadas" in out and str(tmp_path / "datos" / "covers") in out
