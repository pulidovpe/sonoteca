import hashlib

import pytest
from conftest import make_cover, make_m4a, make_mp3, make_mp4, needs_ffmpeg
from mutagen.id3 import ID3

from sonoteca.core import tag_writer
from sonoteca.core.tag_writer import (
    TagWriteError,
    normalize_changes,
    restore_backups,
    write_tags,
)
from sonoteca.core.tags import read_tags

pytestmark = needs_ffmpeg


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_normalize_changes():
    assert normalize_changes({"year": " 1999 ", "artist": "  X  ", "genre": ""}) == {
        "year": 1999, "artist": "X", "genre": None}
    assert normalize_changes({"track_no": ""}) == {"track_no": None}
    for bad in ({"year": "abc"}, {"year": "99999"}, {"track_no": "0"}, {"title": "  "},
                {"nope": "x"}):
        with pytest.raises(ValueError):
            normalize_changes(bad)


def test_mp3_write_all_fields_as_id3v23(tmp_path):
    p = make_mp3(tmp_path / "a.mp3", title="Viejo", artist="Viejo", album="Viejo", date="1990",
                 track="2/12", disc="1/2", genre="Pop")
    write_tags(p, {"title": "Canción ñandú", "artist": "José Pérez", "album_artist": "Varios",
                   "album": "Álbum Nuevo", "year": "2001", "track_no": "5", "disc_no": "2",
                   "genre": "Rock"}, id3_version=3)
    m = read_tags(p)
    assert (m.title, m.artist, m.album_artist, m.album) == (
        "Canción ñandú", "José Pérez", "Varios", "Álbum Nuevo")
    assert (m.year, m.track_no, m.disc_no, m.genre) == (2001, 5, 2, "Rock")
    assert ID3(p).version == (2, 3, 0)
    # el total de la pista/disco se conserva al cambiar solo el número
    assert str(ID3(p)["TRCK"].text[0]) == "5/12"
    assert str(ID3(p)["TPOS"].text[0]) == "2/2"
    assert not list(tmp_path.glob(".*sonoteca-tmp*"))  # sin temporales


def test_mp3_v24_and_partial_change_keeps_other_fields(tmp_path):
    p = make_mp3(tmp_path / "a.mp3", title="T", artist="A", album="B", date="1990", genre="Pop")
    write_tags(p, {"album": "C"}, id3_version=4)
    m = read_tags(p)
    assert (m.title, m.artist, m.album, m.year, m.genre) == ("T", "A", "C", 1990, "Pop")
    assert ID3(p).version == (2, 4, 0)


def test_mp3_without_tags_and_removal(tmp_path):
    p = make_mp3(tmp_path / "suelto.mp3")
    write_tags(p, {"title": "Nuevo", "artist": "X", "genre": "Jazz"})
    assert read_tags(p).title == "Nuevo"
    write_tags(p, {"genre": ""})  # quitar
    assert read_tags(p).genre is None
    assert read_tags(p).title == "Nuevo"


def test_m4a_and_mp4_write(tmp_path):
    p = make_m4a(tmp_path / "a.m4a", title="V", artist="V", album="V", track="3/9")
    write_tags(p, {"title": "Nuevo", "year": "1986", "track_no": "4", "genre": "Rock"})
    m = read_tags(p)
    assert (m.title, m.year, m.track_no, m.genre, m.artist) == ("Nuevo", 1986, 4, "Rock", "V")
    from mutagen.mp4 import MP4
    assert MP4(p).tags["trkn"] == [(4, 9)]  # conserva el total
    v = make_mp4(tmp_path / "v.mp4", title="Clip")
    write_tags(v, {"artist": "Daft Punk"})
    assert read_tags(v).artist == "Daft Punk" and read_tags(v).kind == "video"


def test_cover_mp3_and_m4a(tmp_path):
    img = make_cover(tmp_path / "c.jpg").read_bytes()
    for maker, name in ((make_mp3, "a.mp3"), (make_m4a, "a.m4a")):
        p = maker(tmp_path / name, title="T")
        assert read_tags(p).has_cover is False
        write_tags(p, {}, img)
        assert read_tags(p).has_cover is True


def test_failure_leaves_original_untouched(tmp_path, monkeypatch):
    p = make_mp3(tmp_path / "a.mp3", title="Original", artist="A")
    before = sha(p)

    def boom(*a, **k):
        raise RuntimeError("disco lleno")

    monkeypatch.setattr(tag_writer, "_apply_mp3", boom)
    with pytest.raises(TagWriteError, match="disco lleno"):
        write_tags(p, {"title": "Nuevo"})
    assert sha(p) == before
    assert not list(tmp_path.glob(".*sonoteca-tmp*"))


def test_verification_failure_does_not_replace_original(tmp_path, monkeypatch):
    p = make_mp3(tmp_path / "a.mp3", title="Original")
    before = sha(p)
    monkeypatch.setattr(tag_writer, "_apply_mp3", lambda *a, **k: None)  # "olvida" escribir
    with pytest.raises(TagWriteError, match="verificación"):
        write_tags(p, {"title": "Nuevo"})
    assert sha(p) == before


def test_invalid_input_and_formats(tmp_path):
    p = make_mp3(tmp_path / "a.mp3", title="T")
    with pytest.raises(TagWriteError):
        write_tags(p, {"year": "x"})
    with pytest.raises(TagWriteError, match="formato"):
        write_tags(tmp_path / "a.flac", {"title": "x"})
    with pytest.raises(TagWriteError):
        write_tags(tmp_path / "no_existe.mp3", {"title": "x"})
    with pytest.raises(ValueError):
        tag_writer.read_cover_file(p)  # un mp3 no es una imagen
    with pytest.raises(ValueError, match="«foto.jpg»: no existe") as err:
        tag_writer.read_cover_file(tmp_path / "carpeta" / "foto.jpg")
    assert "carpeta" not in str(err.value)  # el mensaje no vuelca la ruta completa


def test_backup_and_restore(tmp_path):
    p = make_mp3(tmp_path / "m/a.mp3", title="Original", artist="A")
    before = sha(p)
    backup = tmp_path / "backup"
    write_tags(p, {"title": "Cambiado"}, backup_dir=backup)
    assert read_tags(p).title == "Cambiado" and sha(p) != before
    assert (backup / "manifest.tsv").exists()
    restored, failed = restore_backups(backup)
    assert (restored, failed) == (1, [])
    assert sha(p) == before and read_tags(p).title == "Original"
    with pytest.raises(FileNotFoundError):
        restore_backups(tmp_path / "otro")


def test_replace_retries_permission_error_then_succeeds(monkeypatch, tmp_path):
    from sonoteca.core import tag_writer
    calls = []

    def flaky(src, dst):
        calls.append(1)
        if len(calls) < 3:
            raise PermissionError(13, "Acceso denegado")

    monkeypatch.setattr(tag_writer.os, "replace", flaky)
    monkeypatch.setattr(tag_writer.time, "sleep", lambda _s: None)
    tag_writer._replace_with_retry(tmp_path / "a", tmp_path / "b")
    assert len(calls) == 3


def test_replace_gives_up_after_attempts_and_does_not_retry_other_errors(monkeypatch, tmp_path):
    import pytest
    from sonoteca.core import tag_writer
    calls = []

    def locked(src, dst):
        calls.append(1)
        raise PermissionError(13, "Acceso denegado")

    monkeypatch.setattr(tag_writer.os, "replace", locked)
    monkeypatch.setattr(tag_writer.time, "sleep", lambda _s: None)
    with pytest.raises(PermissionError):
        tag_writer._replace_with_retry(tmp_path / "a", tmp_path / "b", attempts=4)
    assert len(calls) == 4

    calls.clear()
    monkeypatch.setattr(tag_writer.os, "replace", lambda s, d: (calls.append(1), (_ for _ in ()).throw(FileNotFoundError()))[1])
    with pytest.raises(FileNotFoundError):
        tag_writer._replace_with_retry(tmp_path / "a", tmp_path / "b")
    assert len(calls) == 1


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("SONOTECA_DATA_DIR", str(tmp_path / "datos"))
    return tmp_path / "datos"


def test_busy_file_gets_a_deferred_write_and_flush_applies_it(tmp_path, data_dir):
    from sonoteca.core import pending_tags
    p = make_mp3(tmp_path / "s.mp3", title="Viejo")
    before = sha(p)
    assert write_tags(p, {"title": "Nuevo"}, is_busy=lambda q: True) is False
    assert sha(p) == before                                     # el archivo que suena no se tocó
    assert pending_tags.has_pending(p) and pending_tags.registered() == [str(p)]
    assert read_tags(p).title == "Nuevo"                        # la app ya ve los tags nuevos (lee de la copia)
    assert pending_tags.flush(p) == "done"
    assert not pending_tags.has_pending(p) and pending_tags.registered() == []
    assert read_tags(p).title == "Nuevo" and sha(p) != before


def test_deferred_edits_accumulate(tmp_path, data_dir):
    p = make_mp3(tmp_path / "a.mp3", title="Viejo", artist="Viejo")
    assert write_tags(p, {"title": "T1"}, is_busy=lambda q: True) is False
    assert write_tags(p, {"artist": "A2"}, is_busy=lambda q: True) is False
    m = read_tags(p)
    assert (m.title, m.artist) == ("T1", "A2")                  # la segunda edición parte de la primera
    from sonoteca.core import pending_tags
    pending_tags.flush(p)
    m = read_tags(p)
    assert (m.title, m.artist) == ("T1", "A2")


def test_edit_after_the_file_is_free_includes_the_pending_and_clears_it(tmp_path, data_dir):
    from sonoteca.core import pending_tags
    p = make_mp3(tmp_path / "b.mp3", title="Viejo", artist="Viejo")
    write_tags(p, {"title": "T1"}, is_busy=lambda q: True)
    assert write_tags(p, {"artist": "A2"}, is_busy=lambda q: False) is True
    assert not pending_tags.has_pending(p) and pending_tags.registered() == []
    m = read_tags(p)
    assert (m.title, m.artist) == ("T1", "A2")


def test_lock_falls_back_to_deferral_only_when_allowed(tmp_path, data_dir, monkeypatch):
    from sonoteca.core import pending_tags
    p = make_mp3(tmp_path / "l.mp3", title="Viejo")
    real = tag_writer.os.replace

    def locked(src, dst):
        if str(dst) == str(p):
            raise PermissionError(13, "Acceso denegado")
        real(src, dst)

    monkeypatch.setattr(tag_writer.os, "replace", locked)
    monkeypatch.setattr(tag_writer.time, "sleep", lambda _s: None)
    with pytest.raises(TagWriteError):
        write_tags(p, {"title": "Nuevo"})                       # sin defer_on_lock (macOS/Linux) el error se informa
    assert not pending_tags.has_pending(p)
    assert write_tags(p, {"title": "Nuevo"}, defer_on_lock=True) is False
    assert pending_tags.has_pending(p) and read_tags(p).title == "Nuevo"


def test_flush_keeps_it_pending_while_locked_and_never_recreates_a_deleted_file(tmp_path, data_dir, monkeypatch):
    from sonoteca.core import pending_tags
    p = make_mp3(tmp_path / "k.mp3", title="Viejo")
    write_tags(p, {"title": "Nuevo"}, is_busy=lambda q: True)
    real = tag_writer.os.replace
    monkeypatch.setattr(tag_writer.os, "replace",
                        lambda s, d: (_ for _ in ()).throw(PermissionError(13, "x")))
    monkeypatch.setattr(tag_writer.time, "sleep", lambda _s: None)
    assert pending_tags.flush(p, attempts=2) == "locked"
    assert pending_tags.registered() == [str(p)]                # sigue en el diario: se reintentará
    monkeypatch.setattr(tag_writer.os, "replace", real)
    p.unlink()                                                  # el archivo se eliminó mientras tanto
    assert pending_tags.flush(p) == "none"
    assert not p.exists() and not pending_tags.has_pending(p) and pending_tags.registered() == []


def test_flush_all_skips_the_playing_file(tmp_path, data_dir):
    from sonoteca.core import pending_tags
    a = make_mp3(tmp_path / "x.mp3", title="X")
    b = make_mp3(tmp_path / "y.mp3", title="Y")
    for q in (a, b):
        write_tags(q, {"title": "Nuevo"}, is_busy=lambda _q: True)
    done = []
    out = pending_tags.flush_all(keep=[a], on_done=done.append)
    assert out == {"done": 1, "locked": 0, "skipped": 1} and done == [b]
    assert pending_tags.has_pending(a) and not pending_tags.has_pending(b)
