from musicapp.core.db import connect
from musicapp.core.search import SearchIndex, normalize, tokenize


def test_normalize():
    assert normalize("José Luis Perales") == "jose luis perales"
    assert normalize("PERDÓNAME") == "perdoname"
    assert normalize("T.a.t.u.") == "tatu"
    assert normalize("Guns N' Roses") == "guns n roses"
    assert normalize("AC/DC") == "ac dc"
    assert normalize("Ñandú  —  Año") == "nandu ano"
    assert normalize("Тату") == "тату"  # otros alfabetos se conservan
    assert normalize(None) == "" and normalize("  !!  ") == ""
    assert tokenize("camilo   sesto") == ["camilo", "sesto"]


def _db():
    conn = connect(":memory:")
    conn.executescript("""
    INSERT INTO artists (id, name, sort_name) VALUES
        (1, 'José Luis Perales', 'José Luis Perales'), (2, 'Camilo Sesto', 'Camilo Sesto'),
        (3, 'T.a.t.u.', 'T.a.t.u.'), (4, 'Amor Perdido', 'Amor Perdido');
    INSERT INTO albums (id, title, album_artist_id, year) VALUES
        (1, 'Álbum desconocido', 1, NULL), (2, 'Mi Amor', 2, 1974), (3, 'The Best', 3, 2006),
        (4, 'Sin Amor', 4, 1999);
    INSERT INTO files (id, path, size, mtime_ns, format, kind) VALUES
        (1,'/1.mp3',1,1,'mp3','audio'),(2,'/2.mp3',1,1,'mp3','audio'),
        (3,'/3.mp3',1,1,'mp3','audio'),(4,'/4.mp3',1,1,'mp3','audio'),(5,'/5.mp3',1,1,'mp3','audio');
    INSERT INTO tracks (file_id, album_id, artist_id, title, duration) VALUES
        (1, 1, 1, 'Me gusta la palabra libertad', 200), (2, 2, 2, 'Perdóname', 200),
        (3, 2, 2, 'Amor mío', 200), (4, 3, 3, 'All The Things She Said', 200),
        (5, 4, 4, 'Perdóname Amor', 200);
    """)
    return SearchIndex.build(conn)


def titles(res):
    return [t["title"] for t in res.tracks]


def test_ignores_accents_and_case():
    idx = _db()
    assert titles(idx.query("perdoname"))[0] == "Perdóname"
    assert titles(idx.query("PERDÓNAME"))[0] == "Perdóname"
    assert [a["name"] for a in idx.query("jose").artists] == ["José Luis Perales"]
    assert [a["name"] for a in idx.query("tatu").artists] == ["T.a.t.u."]


def test_words_can_come_from_different_fields():
    idx = _db()
    assert titles(idx.query("camilo perdon")) == ["Perdóname"]  # artista + título
    assert titles(idx.query("perales libertad")) == ["Me gusta la palabra libertad"]
    assert titles(idx.query("sesto mi amor")) == ["Amor mío", "Perdóname"]  # álbum + artista


def test_relevance_title_match_before_artist_or_album_match():
    idx = _db()
    res = titles(idx.query("amor"))
    # 'Amor mío' (título que empieza por la palabra) y 'Perdóname Amor' antes que las pistas
    # que solo coinciden por el álbum/artista ("Mi Amor" -> Perdóname)
    assert res.index("Amor mío") < res.index("Perdóname")
    assert res.index("Perdóname Amor") < res.index("Perdóname")


def test_groups_artists_albums_tracks():
    res = _db().query("amor")
    assert [a["name"] for a in res.artists] == ["Amor Perdido"]
    assert {a["title"] for a in res.albums} == {"Mi Amor", "Sin Amor"}
    assert res.tracks


def test_no_match_and_empty_queries():
    idx = _db()
    assert not idx.query("zzzz")
    assert not idx.query("")
    assert not idx.query("   !!! ")
    assert not idx.query("100%")  # los signos no actúan como comodines


def test_limits():
    res = _db().query("a", max_artists=1, max_albums=1, max_tracks=2)
    assert len(res.artists) <= 1 and len(res.albums) <= 1 and len(res.tracks) <= 2
