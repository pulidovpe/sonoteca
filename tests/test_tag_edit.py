import pytest
from conftest import make_cover, make_mp3, needs_ffmpeg

from sonoteca.core import library, tag_edit
from sonoteca.core.db import connect
from sonoteca.core.scanner import scan
from sonoteca.core.tag_writer import read_cover_file
from sonoteca.core.tags import read_tags

pytestmark = needs_ffmpeg


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("SONOTECA_DATA_DIR", str(tmp_path / "datos"))
    root = tmp_path / "music"
    for n in (1, 2, 3):
        make_mp3(root / f"A/{n}.mp3", title=f"Pista {n}", artist="FOR NON BLONDIES",
                 album="What's Up", date="1993", track=f"{n}/3")
    make_mp3(root / "B/1.mp3", title="Otra", artist="Otro", album="Disco B", date="2000")
    conn = connect(tmp_path / "t.db")
    scan(conn, root)
    ids = [r["id"] for r in library.list_tracks(conn)]
    return conn, root, ids


def ids_of(conn, album):
    row = conn.execute("SELECT id FROM albums WHERE title = ?", (album,)).fetchone()
    return [t["id"] for t in library.list_tracks(conn, album_id=row["id"])]


def test_common_values_and_mixed(env):
    conn, _, _ = env
    album = ids_of(conn, "What's Up")
    v = tag_edit.common_values(conn, album)
    assert v["count"] == 3 and v["single"] is False
    assert v["artist"] == {"value": "FOR NON BLONDIES", "mixed": False}
    assert v["title"] == {"value": "", "mixed": True}
    assert v["year"]["value"] == "1993"
    both = tag_edit.common_values(conn, album + ids_of(conn, "Disco B"))
    assert both["album"]["mixed"] is True


def test_preview_lines_and_validation(env):
    conn, _, _ = env
    album = ids_of(conn, "What's Up")
    p = tag_edit.preview(conn, album, {"artist": "4 Non Blondes", "year": ""})
    assert p["count"] == 3
    assert "Artista: «FOR NON BLONDIES» → «4 Non Blondes»" in p["lines"]
    assert any(line.startswith("Año:") and line.endswith("quitar") for line in p["lines"])
    with pytest.raises(ValueError, match="una pista a la vez"):
        tag_edit.preview(conn, album, {"title": "x"})
    with pytest.raises(ValueError):
        tag_edit.preview(conn, album, {"year": "abc"})


def test_apply_batch_updates_files_and_db_keeping_track_ids(env, tmp_path):
    conn, root, _ = env
    album = ids_of(conn, "What's Up")
    seen = []
    res = tag_edit.apply_edit(conn, album, {"artist": "4 Non Blondes", "album_artist": "4 Non Blondes"},
                              progress=lambda d, t: seen.append((d, t)))
    assert (res.updated, res.failed) == (3, [])
    assert seen == [(1, 3), (2, 3), (3, 3)]
    assert read_tags(root / "A/1.mp3").artist == "4 Non Blondes"
    # los ids de pista se conservan y el artista viejo desaparece
    assert ids_of(conn, "What's Up") == album
    names = [a["name"] for a in library.list_artists(conn)]
    assert "4 Non Blondes" in names and "FOR NON BLONDIES" not in names
    # hay copia de respaldo de los 3 originales
    assert len(list((tmp_path / "datos" / "backups").glob("*/manifest.tsv"))) == 1
    assert res.backup_dir and res.album_id


def test_album_rename_and_year_refresh(env):
    conn, _, _ = env
    album = ids_of(conn, "What's Up")
    tag_edit.apply_edit(conn, album, {"album": "Bigger, Better, Faster, More!", "year": "1992"},
                        backup=False)
    albums = {a["title"]: a for a in library.list_albums(conn)}
    assert "What's Up" not in albums
    assert albums["Bigger, Better, Faster, More!"]["year"] == 1992
    assert albums["Bigger, Better, Faster, More!"]["tracks"] == 3


def test_single_track_title_and_cover(env, tmp_path):
    conn, root, _ = env
    one = ids_of(conn, "Disco B")
    cover = make_cover(tmp_path / "c.jpg")
    res = tag_edit.apply_edit(conn, one, {"title": "Título corregido"}, str(cover), backup=False)
    assert res.updated == 1
    assert library.search(conn, "corregido")[0]["id"] == one[0]
    assert read_tags(root / "B/1.mp3").has_cover is True
    assert read_cover_file(cover)  # válida


def test_failures_do_not_stop_the_rest(env):
    conn, root, _ = env
    album = ids_of(conn, "What's Up")
    (root / "A/2.mp3").unlink()
    res = tag_edit.apply_edit(conn, album, {"genre": "Rock"}, backup=False)
    assert res.updated == 2 and len(res.failed) == 1
    assert "2.mp3" in res.failed[0][0]


def test_apply_without_changes_is_rejected(env):
    conn, _, ids = env
    with pytest.raises(ValueError, match="No hay cambios"):
        tag_edit.apply_edit(conn, ids[:1], {}, backup=False)


def test_title_stays_clean_after_editing_other_fields(tmp_path, monkeypatch):
    """Regresión: editar artista/álbum de archivos sin título en los tags no debe convertir el
    título en el nombre completo del archivo."""
    monkeypatch.setenv("SONOTECA_DATA_DIR", str(tmp_path / "datos"))
    root = tmp_path / "music"
    make_mp3(root / "03- Ace Of Base - Happy Nation.mp3")
    make_mp3(root / "04- Ace Of Base - The Sign.mp3")
    conn = connect(tmp_path / "t.db")
    scan(conn, root)
    ids = [r["id"] for r in library.list_tracks(conn)]
    tag_edit.apply_edit(conn, ids, {"artist": "Ace of Base", "album": "The Sign"}, backup=False)
    tracks = {r["title"]: r for r in library.list_tracks(conn)}
    assert set(tracks) == {"Happy Nation", "The Sign"}
    assert tracks["Happy Nation"]["track_no"] == 3 and tracks["The Sign"]["track_no"] == 4
    assert {r["artist"] for r in tracks.values()} == {"Ace of Base"}
    # también al reescanear con --force (relee los archivos desde cero)
    scan(conn, root, force=True)
    assert {r["title"] for r in library.list_tracks(conn)} == {"Happy Nation", "The Sign"}
