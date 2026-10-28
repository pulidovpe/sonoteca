import pytest
from conftest import make_m4a, make_mp3, make_mp4, needs_ffmpeg

from musicapp.core.models import UNKNOWN_ALBUM, UNKNOWN_ARTIST
from musicapp.core.tags import TagReadError, parse_pair, parse_year, read_tags


def test_parse_year():
    assert parse_year("2019") == 2019
    assert parse_year("2019-05-03T00:00:00Z") == 2019
    assert parse_year("sin año") is None
    assert parse_year(None) is None
    assert parse_year("0000") is None


def test_parse_pair():
    assert parse_pair("3/12") == 3
    assert parse_pair("7") == 7
    assert parse_pair("0/10") is None
    assert parse_pair("x") is None


@needs_ffmpeg
def test_read_mp3_id3v23(tmp_path):
    p = make_mp3(tmp_path / "a.mp3", title="Come Together", artist="The Beatles",
                 album="Abbey Road", date="1969", track="1/17", disc="2/2", genre="Rock")
    m = read_tags(p)
    assert (m.title, m.artist, m.album, m.year) == ("Come Together", "The Beatles",
                                                    "Abbey Road", 1969)
    assert (m.track_no, m.disc_no, m.genre) == (1, 2, "Rock")
    assert m.album_artist == "The Beatles"  # cae a artist si no hay TPE2
    assert m.kind == "audio" and m.format == "mp3"
    assert m.duration == pytest.approx(1.0, abs=0.2)


@needs_ffmpeg
def test_read_mp3_without_tags(tmp_path):
    m = read_tags(make_mp3(tmp_path / "suelto.mp3"))
    assert m.title == "suelto"
    assert m.artist == UNKNOWN_ARTIST and m.album == UNKNOWN_ALBUM


@needs_ffmpeg
def test_read_m4a(tmp_path):
    m = read_tags(make_m4a(tmp_path / "a.m4a", title="Signos", artist="Soda Stereo",
                           album="Signos", date="1986", track="3/9", album_artist="Soda"))
    assert (m.title, m.artist, m.album_artist, m.year, m.track_no) == (
        "Signos", "Soda Stereo", "Soda", 1986, 3)
    assert m.format == "m4a" and m.kind == "audio"


@needs_ffmpeg
def test_read_mp4_is_video(tmp_path):
    m = read_tags(make_mp4(tmp_path / "v.mp4", title="Clip"))
    assert m.kind == "video" and m.format == "mp4" and m.title == "Clip"


def test_corrupt_file_raises(tmp_path):
    bad = tmp_path / "roto.mp3"
    bad.write_bytes(b"esto no es un mp3" * 10)
    with pytest.raises(TagReadError):
        read_tags(bad)


def test_parse_filename():
    from musicapp.core.tags import parse_filename

    def tup(stem):
        i = parse_filename(stem)
        return (i.year, i.track_no, i.artist, i.album, i.title)

    # los nombres reales que reportó el usuario
    assert tup("03- Ace Of Base - Happy Nation") == (None, 3, "Ace Of Base", None, "Happy Nation")
    assert tup("04- Ace Of Base - The Sign") == (None, 4, "Ace Of Base", None, "The Sign")
    assert tup("1991-Spin Doctors - Two Princes") == (1991, None, "Spin Doctors", None, "Two Princes")
    assert tup("1997-Eagle-Eye Cherry - Save Tonight") == (
        1997, None, "Eagle-Eye Cherry", None, "Save Tonight")
    assert tup("Camilo Sesto - Amor mío") == (None, None, "Camilo Sesto", None, "Amor mío")
    assert tup("01 - Come Together") == (None, 1, None, None, "Come Together")
    assert tup("03. Perdóname") == (None, 3, None, None, "Perdóname")
    assert tup("99 Luftballons") == (None, None, None, None, "99 Luftballons")
    assert tup("2112") == (None, None, None, None, "2112")
    assert tup("suelto") == (None, None, None, None, "suelto")
    # estilo "Artista - Álbum - NN - Título"
    assert tup("Soda Stereo - Signos - 03 - Persiana Americana") == (
        None, 3, "Soda Stereo", "Signos", "Persiana Americana")
    # tres partes sin nº de pista: no se inventa un álbum
    assert tup("Artista - Título - Remix") == (None, None, "Artista", None, "Título - Remix")


@needs_ffmpeg
def test_filename_fills_only_missing_fields_when_title_tag_is_missing(tmp_path):
    # Caso reportado: el archivo tiene artista y álbum en los tags pero no título.
    # El título NO debe ser el nombre completo del archivo.
    p = make_mp3(tmp_path / "03- Ace Of Base - Happy Nation.mp3", artist="Ace of Base",
                 album="Happy Nation")
    m = read_tags(p)
    assert m.title == "Happy Nation" and m.track_no == 3
    assert (m.artist, m.album, m.inferred) == ("Ace of Base", "Happy Nation", True)
    assert "03" not in m.title and "Ace" not in m.title


@needs_ffmpeg
def test_filename_with_swapped_order_uses_artist_tag(tmp_path):
    p = make_mp3(tmp_path / "Happy Nation - Ace of Base.mp3", artist="Ace of Base")
    assert read_tags(p).title == "Happy Nation"


@needs_ffmpeg
def test_artist_is_confirmed_from_filename_only_if_title_matches(tmp_path):
    ok = read_tags(make_mp3(tmp_path / "1991-Spin Doctors - Two Princes.mp3", title="Two Princes"))
    assert ok.artist == "Spin Doctors" and ok.inferred is True
    other = read_tags(make_mp3(tmp_path / "1991-Spin Doctors - Two Princes (2).mp3",
                               title="Otro título"))
    assert other.artist == "Artista desconocido" and other.inferred is False


@needs_ffmpeg
def test_complete_tags_are_never_overridden_by_filename(tmp_path):
    m = read_tags(make_mp3(tmp_path / "2001-Otro - Nombre.mp3", title="Real", artist="Artista Real"))
    assert (m.artist, m.title, m.year, m.track_no, m.inferred) == (
        "Artista Real", "Real", None, None, False)


@needs_ffmpeg
def test_filename_inference_without_any_tags(tmp_path):
    m = read_tags(make_mp3(tmp_path / "2000-Wheatus - Teenage Dirtbag.mp3"))
    assert (m.artist, m.title, m.year, m.inferred) == ("Wheatus", "Teenage Dirtbag", 2000, True)

