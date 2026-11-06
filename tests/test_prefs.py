"""Almacén de preferencias de interfaz (0.12.15)."""
import json

import pytest

from sonoteca.core.prefs import Prefs


def test_values_persist_between_sessions(tmp_path):
    path = tmp_path / "sub" / "ui_prefs.json"
    prefs = Prefs(path)
    assert prefs.get("playlists.grid", False) is False
    assert prefs.set("playlists.grid", True) is True
    assert prefs.set("playlists.grid", True) is False                 # sin cambios: no reescribe
    assert Prefs(path).get("playlists.grid") is True                  # otra «sesión» lo lee
    assert json.loads(path.read_text(encoding="utf-8")) == {"playlists.grid": True}
    assert list(path.parent.glob(".ui_prefs-*")) == []                # sin temporales


def test_missing_or_corrupt_file_means_no_preferences(tmp_path):
    path = tmp_path / "ui_prefs.json"
    assert Prefs(path).get("x", 7) == 7
    path.write_text("{no es json", encoding="utf-8")
    assert Prefs(path).get("x", 7) == 7
    path.write_text("[1, 2]", encoding="utf-8")                       # JSON válido pero no es un diccionario
    assert Prefs(path).get("x", 7) == 7


def test_remove_and_validation(tmp_path):
    prefs = Prefs(tmp_path / "p.json")
    prefs.set("a", "texto")
    assert prefs.remove("a") is True and prefs.remove("a") is False and prefs.get("a") is None
    for bad in ("", "   ", "x" * 81):
        with pytest.raises(ValueError):
            prefs.set(bad, 1)
    with pytest.raises(TypeError):
        prefs.set("obj", object())


def test_unwritable_location_keeps_values_in_memory(tmp_path):
    blocker = tmp_path / "archivo"
    blocker.write_text("x", encoding="utf-8")
    prefs = Prefs(blocker / "ui_prefs.json")                          # la «carpeta» es un archivo: no se puede escribir
    assert prefs.set("k", 1) is True and prefs.get("k") == 1


def test_default_path_uses_the_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("SONOTECA_DATA_DIR", str(tmp_path / "datos"))
    assert Prefs().path == tmp_path / "datos" / "ui_prefs.json"
