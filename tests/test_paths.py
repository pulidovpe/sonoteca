from pathlib import Path

from sonoteca.cli import main
from sonoteca.core import paths
from sonoteca.core.db import default_db_path


def test_env_overrides(monkeypatch, tmp_path):
    monkeypatch.setenv("SONOTECA_DATA_DIR", str(tmp_path / "datos"))
    monkeypatch.setenv("SONOTECA_CACHE_DIR", str(tmp_path / "cache"))
    assert paths.data_dir() == tmp_path / "datos"
    assert paths.cache_dir() == tmp_path / "cache"
    assert default_db_path() == tmp_path / "datos" / "library.db"


def test_defaults_are_outside_virtualenv(monkeypatch):
    monkeypatch.delenv("SONOTECA_DATA_DIR", raising=False)
    monkeypatch.delenv("SONOTECA_CACHE_DIR", raising=False)
    assert paths.data_dir().name == "sonoteca" or "sonoteca" in str(paths.data_dir())


def test_inside_virtualenv(monkeypatch, tmp_path):
    monkeypatch.setattr("sys.prefix", str(tmp_path / ".venv"))
    assert paths.inside_virtualenv(tmp_path / ".venv" / "cache" / "x")
    assert not paths.inside_virtualenv(tmp_path / "otra" / "x")


def test_cli_paths_warns_when_inside_venv(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr("sys.prefix", str(tmp_path / ".venv"))
    monkeypatch.setenv("SONOTECA_CACHE_DIR", str(tmp_path / ".venv" / "cache"))
    monkeypatch.setenv("SONOTECA_DATA_DIR", str(tmp_path / "datos"))
    assert main(["paths"]) == 0
    out = capsys.readouterr().out
    assert "AVISO" in out and "caché" in out and "SONOTECA_CACHE_DIR" in out
    assert Path(tmp_path / "datos" / "library.db").as_posix() in out


def test_cli_version_shows_code_location(capsys):
    import pytest as _pytest

    import sonoteca

    with _pytest.raises(SystemExit) as exit_info:
        main(["--version"])
    assert exit_info.value.code == 0
    out = capsys.readouterr().out
    assert sonoteca.__version__ in out and "código en" in out
    main(["paths"])
    assert f"Versión       : {sonoteca.__version__}" in capsys.readouterr().out
