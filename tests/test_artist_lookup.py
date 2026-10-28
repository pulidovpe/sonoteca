"""0.8.4: elegir el artista correcto (candidatos de Wikipedia) o escribir una descripción propia."""
import httpx
from test_online import Net, js, make_client, url_has

from sonoteca.core.db import connect
from sonoteca.online import enrich, wikipedia


def summary(title, desc, text="Texto largo del artículo.", thumb=True):
    body = {"type": "standard", "title": title, "description": desc, "extract": text,
            "content_urls": {"desktop": {"page": f"https://es.wikipedia.org/wiki/{title.replace(' ', '_')}"}}}
    if thumb:
        body["thumbnail"] = {"source": f"https://upload.example/{title.replace(' ', '_')}.jpg"}
    return js(body)


def make_artist(conn, name="Nirvana"):
    conn.execute("INSERT INTO artists(id, name, sort_name) VALUES (1, ?, ?)", (name, name))
    conn.commit()
    return 1


def routes():
    hits = [{"title": "Nirvana (banda)"}, {"title": "Nirvana"}, {"title": "Nirvana (religión)"}]
    return {
        url_has("/w/api.php"): js({"query": {"search": hits}}),
        url_has("Nirvana_%28banda%29"): summary("Nirvana (banda)", "banda de rock estadounidense"),
        url_has("Nirvana_%28religi"): summary("Nirvana (religión)", "concepto budista"),
        url_has("/page/summary/Nirvana"): summary("Nirvana", "término sánscrito"),
    }


def test_candidates_list_musical_articles_first_without_duplicates(tmp_path):
    client = make_client(tmp_path, Net(routes()))
    found = wikipedia.search_candidates(client, "Nirvana", languages=("es",))
    assert [c.name for c in found][0] == "Nirvana (banda)"      # el musical, primero
    assert {c.name for c in found} == {"Nirvana (banda)", "Nirvana", "Nirvana (religión)"}
    both = wikipedia.search_candidates(make_client(tmp_path, Net(routes())), "Nirvana",
                                       languages=("es", "es"))
    assert len(both) == 3                                          # misma URL dos veces: no se repite


def test_artist_candidates_use_corrected_query_and_skip_unknown(tmp_path):
    conn = connect(":memory:")
    aid = make_artist(conn, "Nirvna")
    net = Net(routes())
    enrich.artist_candidates(make_client(tmp_path, net), conn, aid, "Nirvana")
    assert "srsearch=Nirvana" in str(net.calls[0].url)             # buscó lo que escribió el usuario
    conn.execute("UPDATE artists SET name = 'Artista desconocido'")
    assert enrich.artist_candidates(make_client(tmp_path, Net(routes())), conn, aid) == []


def test_apply_candidate_and_manual_description_roundtrip(tmp_path):
    conn = connect(":memory:")
    aid = make_artist(conn)
    info = wikipedia.ArtistInfo(name="Nirvana (banda)", summary="Banda de Seattle.",
                                url="https://es.wikipedia.org/wiki/Nirvana", language="es",
                                image_url="https://upload.example/n.jpg")
    enrich.apply_artist_info(conn, aid, info)
    stored = enrich.stored_artist_info(conn, aid)
    assert stored["bio"] == "Banda de Seattle." and stored["bio_source"] == "Wikipedia"
    assert stored["image_url"] == "https://upload.example/n.jpg"
    enrich.set_manual_artist_info(conn, aid, "  Mi grupo favorito de los noventa.  ")
    stored = enrich.stored_artist_info(conn, aid)
    assert stored["bio"] == "Mi grupo favorito de los noventa." and stored["bio_source"] == "Manual"
    assert stored["bio_url"] is None and stored["image_url"] is None
    for bad in ("", "   "):
        try:
            enrich.set_manual_artist_info(conn, aid, bad)
        except ValueError:
            pass
        else:
            raise AssertionError("debía rechazar la descripción vacía")
