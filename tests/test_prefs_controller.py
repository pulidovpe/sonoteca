import pytest

pytest.importorskip("PySide6")

from sonoteca.core.prefs import Prefs  # noqa: E402
from sonoteca.ui.prefs_controller import PrefsController  # noqa: E402


def test_typed_values_with_defaults_and_persistence(tmp_path):
    path = tmp_path / "ui_prefs.json"
    ctrl = PrefsController(Prefs(path))
    seen = []
    ctrl.changed.connect(seen.append)
    assert ctrl.boolValue("playlists.grid", False) is False
    ctrl.setBool("playlists.grid", True)
    ctrl.setBool("playlists.grid", True)                      # sin cambio: no avisa dos veces
    ctrl.setInt("n", 3)
    ctrl.setString("s", "hola")
    assert seen == ["playlists.grid", "n", "s"]
    again = PrefsController(Prefs(path))                       # nueva sesión
    assert again.boolValue("playlists.grid", False) is True and again.intValue("n", 0) == 3 and again.stringValue("s", "") == "hola"


def test_wrong_type_or_bad_key_falls_back_to_the_default(tmp_path):
    ctrl = PrefsController(Prefs(tmp_path / "p.json"))
    ctrl.setString("k", "texto")
    assert ctrl.boolValue("k", True) is True and ctrl.intValue("k", 9) == 9
    ctrl.setBool("", True)                                     # clave no válida: se ignora sin romper
    ctrl.setBool("flag", True)
    assert ctrl.intValue("flag", 5) == 5                       # un bool no cuenta como entero
