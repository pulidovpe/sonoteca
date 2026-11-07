"""0.14.3: ajustes de rendimiento y de dependencias."""
import re
import tempfile
from pathlib import Path

from sonoteca.core.db import connect

ROOT = Path(__file__).resolve().parents[1]


def test_file_database_uses_wal_with_synchronous_normal():
    with tempfile.TemporaryDirectory() as tmp:
        conn = connect(Path(tmp) / "t.db")
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert conn.execute("PRAGMA synchronous").fetchone()[0] == 1          # 1 = NORMAL
        conn.close()


def test_ui_extra_does_not_pull_webengine_or_pdf():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    ui = text[text.index("ui = ["):text.index("dev = [")]
    assert '"PySide6-Essentials>=6.7"' in ui and '"PySide6-Addons>=6.7"' in ui
    assert not re.search(r'"PySide6[>=<~]', ui)                              # el metapaquete trae WebEngine y Pdf desde 6.12


def test_build_constraints_pin_the_verified_pyside6():
    text = (ROOT / "packaging" / "build-constraints.txt").read_text(encoding="utf-8")
    pins = [line for line in text.splitlines() if line and not line.startswith("#")]
    assert pins == ["PySide6_Essentials==6.12.0", "PySide6_Addons==6.12.0", "shiboken6==6.12.0"]


def test_startup_timing_is_opt_in_and_never_breaks_startup():
    app = (ROOT / "src" / "sonoteca" / "ui" / "app.py").read_text(encoding="utf-8")
    assert 'os.environ.get("SONOTECA_DEBUG_TIMING")' in app and "if timing:" in app
    assert "except Exception as exc:  # noqa: BLE001  (solo diagnóstico" in app
    for label in ("imports de Qt y de la aplicación", "base de datos y controladores listos", "QML cargado", "primer fotograma en pantalla"):
        assert label in app
