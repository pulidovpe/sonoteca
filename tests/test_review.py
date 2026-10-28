"""«Por revisar»: descartar la lista, restaurarla y re-escanear sus archivos."""
import pytest

from conftest import make_mp3, needs_ffmpeg

from musicapp.core import library, review
from musicapp.core.db import SCHEMA_VERSION, connect
from musicapp.core.scanner import scan

pytestmark = needs_ffmpeg


@pytest.fixture
def conn(tmp_path):
    root = tmp_path / "m"
    make_mp3(root / "completa.mp3", title="Completa", artist="X", album="Y", date="2000", track="1/1")
    make_mp3(root / "sin_album.mp3", title="Sin album", artist="X")
    make_mp3(root / "Otro Artista - Cancion.mp3")          # sin tags: se deduce del nombre
    c = connect(tmp_path / "r.db")
    scan(c, root)
    c.root = root
    return c


def test_schema_has_dismiss_table(conn):
    assert SCHEMA_VERSION >= 7
    assert conn.execute("SELECT COUNT(*) FROM review_dismissed").fetchone()[0] == 0


def test_dismiss_empties_the_list_and_survives_a_rescan(conn):
    assert len(library.list_incomplete(conn)) == 2
    assert review.dismiss_listed(conn) == 2
    assert library.list_incomplete(conn) == []
    scan(conn, conn.root, force=True)                       # re-escanear la carpeta no los trae de vuelta
    assert library.list_incomplete(conn) == []
    assert review.dismissed_count(conn) == 2
    assert review.restore_dismissed(conn) == 2
    assert len(library.list_incomplete(conn)) == 2


def test_rescan_rereads_files_and_reports_what_got_resolved(conn):
    ids = [r["id"] for r in library.list_incomplete(conn)]
    # una fila desactualizada: el archivo está bien pero la base dice "deducido"
    conn.execute("UPDATE tracks SET inferred = 1 WHERE title = 'Completa'")
    conn.commit()
    assert len(library.list_incomplete(conn)) == 3
    all_ids = [r["id"] for r in library.list_incomplete(conn)]
    out = review.rescan_tracks(conn, all_ids)
    assert out["checked"] == 3 and out["resolved"] == 1 and out["missing"] == 0
    assert len(library.list_incomplete(conn)) == 2 and ids
