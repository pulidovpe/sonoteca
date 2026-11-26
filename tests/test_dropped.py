"""Parte D1: qué hay en lo soltado sobre la ventana (archivos y carpetas), nombre de la lista y dispositivos externos (sin Qt)."""
import os
from pathlib import Path

import pytest

from sonoteca.core import dropped


def _tree(root):
    for rel in ("a/02 y.mp3", "a/01 x.mp3", "a/.oculto.mp3", "a/.DS_Store", "a/portada.jpg", "a/sub/03 w.m4a",
                "b/10 z.m4a", "b/2 z.m4a", "b/nota.txt", "video.mp4", "SONIDO.MP3"):
        f = root / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"")
    return root


def test_to_path_understands_file_urls_with_spaces_and_windows_drives():
    assert dropped.to_path("file:///tmp/x%20y.mp3") == Path("/tmp/x y.mp3")
    assert dropped.to_path("/tmp/a.mp3") == Path("/tmp/a.mp3")
    assert str(dropped.to_path("file:///C:/Users/a%20b.mp3")).replace("\\", "/").endswith("C:/Users/a b.mp3")


def test_collect_takes_files_and_folders_recursively_without_hidden_unsupported_or_repeated(tmp_path):
    root = _tree(tmp_path)
    got = dropped.collect([root / "a", root / "b" / "10 z.m4a", root / "video.mp4", root / "a", root / "a" / "01 x.mp3",
                           root / "b" / "nota.txt", root / "a" / ".oculto.mp3", root / "no_existe.mp3"])
    assert [p.relative_to(root).as_posix() for p in got] == [
        "a/01 x.mp3", "a/02 y.mp3", "a/sub/03 w.m4a", "b/10 z.m4a", "video.mp4"]


def test_collect_orders_naturally_and_accepts_urls_and_uppercase_extensions(tmp_path):
    root = _tree(tmp_path)
    got = dropped.collect([(root / "b").as_uri(), (root / "SONIDO.MP3").as_uri()])
    assert [p.relative_to(root).as_posix() for p in got] == ["b/2 z.m4a", "b/10 z.m4a", "SONIDO.MP3"]      # sin distinguir mayúsculas


def test_collect_matches_the_library_scanner_rules(tmp_path):
    pytest.importorskip("mutagen")
    from sonoteca.core import scanner
    root = _tree(tmp_path)
    assert {str(p) for p in dropped.collect([root])} == {str(p) for p in scanner.iter_media_files(root)}


def test_default_list_name_uses_the_dropped_folder_or_the_common_parent(tmp_path):
    root = _tree(tmp_path)
    assert dropped.default_list_name([root / "a"]) == "a"
    assert dropped.default_list_name([root / "b" / "10 z.m4a", root / "b" / "2 z.m4a"]) == "b"
    assert dropped.default_list_name([root / "a" / "01 x.mp3", root / "b" / "2 z.m4a"]) == dropped.DEFAULT_LIST_NAME
    assert dropped.default_list_name([root / "no_existe"]) == dropped.DEFAULT_LIST_NAME


def test_is_external_by_platform():
    boot = lambda vol: vol.name == "Macintosh HD"                                                   # noqa: E731
    assert dropped.is_external("/Volumes/PENDRIVE/musica/a.mp3", "darwin", is_boot_volume=boot) is True
    assert dropped.is_external("/Volumes/Macintosh HD/Users/p/a.mp3", "darwin", is_boot_volume=boot) is False
    assert dropped.is_external("/Users/p/Music/a.mp3", "darwin") is False
    assert dropped.is_external("/media/p/USB/a.mp3", "linux") is True
    assert dropped.is_external("/run/media/p/CD/a.mp3", "linux") is True
    assert dropped.is_external("/home/p/Musica/a.mp3", "linux") is False
    kinds = {"C:\\": 3, "E:\\": 2, "D:\\": 5, "Z:\\": 4}
    assert [dropped.is_external(f"{d}:\\m\\a.mp3", "win32", drive_type=lambda r: kinds[r]) for d in "CEDZ"] == [False, True, True, False]
    assert dropped.is_external("\\\\servidor\\share\\a.mp3", "win32", drive_type=lambda r: 2) is False   # ruta de red (UNC)
    assert dropped.is_external("/x/y", "otro") is False
    assert os.sep                                                                                   # (usa os: evita F401 si se simplifica)
