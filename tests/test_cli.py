from conftest import needs_ffmpeg

from sonoteca.cli import main

pytestmark = needs_ffmpeg


def test_cli_end_to_end(library_dir, tmp_path, capsys):
    db = tmp_path / "t.db"
    assert main(["--db", str(db), "scan", str(library_dir)]) == 0
    assert "Nuevos: 6" in capsys.readouterr().out

    assert main(["--db", str(db), "stats"]) == 0
    assert "Pistas: 6" in capsys.readouterr().out

    assert main(["--db", str(db), "albums", "--decade", "1960"]) == 0
    out = capsys.readouterr().out
    assert "Abbey Road" in out and "Signos" not in out

    assert main(["--db", str(db), "search", "taxman"]) == 0
    assert "Taxman" in capsys.readouterr().out
