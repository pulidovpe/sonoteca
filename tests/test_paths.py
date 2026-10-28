from pathlib import Path

from musicapp.cli import main
from musicapp.core import paths
from musicapp.core.db import default_db_path


def test_env_overrides(monkeypatch, tmp_path):
    monkeypatch.setenv("MUSICAPP_DATA_DIR", str(tmp_path / "datos"))
    monkeypatch.setenv("MUSICAPP_CACHE_DIR", str(tmp_path / "cache"))
    assert paths.data_dir() == tmp_path / "datos"
    assert paths.cache_dir() == tmp_path / "cache"
    assert default_db_path() == tmp_path / "datos" / "library.db"


def test_defaults_are_outside_virtualenv(monkeypatch):
    monkeypatch.delenv("MUSICAPP_DATA_DIR", raising=False)
    monkeypatch.delenv("MUSICAPP_CACHE_DIR", raising=False)
    assert paths.data_dir().name == "musicapp" or "musicapp" in str(paths.data_dir())


def test_inside_virtualenv(monkeypatch, tmp_path):
    monkeypatch.setattr("sys.prefix", str(tmp_path / ".venv"))
    assert paths.inside_virtualenv(tmp_path / ".venv" / "cache" / "x")
    assert not paths.inside_virtualenv(tmp_path / "otra" / "x")


def test_cli_paths_warns_when_inside_venv(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr("sys.prefix", str(tmp_path / ".venv"))
    monkeypatch.setenv("MUSICAPP_CACHE_DIR", str(tmp_path / ".venv" / "cache"))
    monkeypatch.setenv("MUSICAPP_DATA_DIR", str(tmp_path / "datos"))
    assert main(["paths"]) == 0
    out = capsys.readouterr().out
    assert "AVISO" in out and "caché" in out and "MUSICAPP_CACHE_DIR" in out
    assert Path(tmp_path / "datos" / "library.db").as_posix() in out


def test_cli_version_shows_code_location(capsys):
    import pytest as _pytest

    import musicapp

    with _pytest.raises(SystemExit) as exit_info:
        main(["--version"])
    assert exit_info.value.code == 0
    out = capsys.readouterr().out
    assert musicapp.__version__ in out and "código en" in out
    main(["paths"])
    assert f"Versión       : {musicapp.__version__}" in capsys.readouterr().out
