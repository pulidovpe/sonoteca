"""Imágenes para el móvil: portada de una pista y imagen del artista (foto o portada de un álbum suyo), como en el escritorio."""
from __future__ import annotations

import threading

from sync_support import add_track
from test_sync_server import Client, _pair

from sonoteca.core import covers
from sonoteca.core.db import connect
from sonoteca.sync.server import default_artist_image_provider, make_server

JPEG = b"\xff\xd8\xff\xe0JFIF-folder-cover"
PNG = b"\x89PNG\r\n\x1a\n" + b"png-body"
PHOTO = b"\xff\xd8\xff\xe0PHOTO-OF-ARTIST"


def _library(tmp_path):
    conn = connect(tmp_path / "lib.db")
    t1 = add_track(conn, tmp_path / "m", "uno")
    uuid = conn.execute("SELECT uuid FROM tracks WHERE id = ?", (t1,)).fetchone()[0]
    return conn, t1, uuid


def test_artist_image_is_the_album_cover_in_the_folder_when_there_is_no_photo(tmp_path, monkeypatch):
    conn, t1, _ = _library(tmp_path)
    monkeypatch.setattr(covers, "artist_photo", lambda artist_id: None)
    (tmp_path / "m" / "cover.jpg").write_bytes(JPEG)
    assert default_artist_image_provider(conn, t1) == (JPEG, "image/jpeg")


def test_artist_photo_is_preferred_over_the_album_cover(tmp_path, monkeypatch):
    conn, t1, _ = _library(tmp_path)
    photo = tmp_path / "foto.jpg"
    photo.write_bytes(PHOTO)
    monkeypatch.setattr(covers, "artist_photo", lambda artist_id: photo)
    (tmp_path / "m" / "cover.jpg").write_bytes(JPEG)
    assert default_artist_image_provider(conn, t1) == (PHOTO, "image/jpeg")


def test_png_images_keep_their_mime_type(tmp_path, monkeypatch):
    conn, t1, _ = _library(tmp_path)
    monkeypatch.setattr(covers, "artist_photo", lambda artist_id: None)
    (tmp_path / "m" / "cover.png").write_bytes(PNG)
    assert default_artist_image_provider(conn, t1) == (PNG, "image/png")


def test_no_image_at_all_means_none(tmp_path, monkeypatch):
    conn, t1, _ = _library(tmp_path)
    monkeypatch.setattr(covers, "artist_photo", lambda artist_id: None)
    assert default_artist_image_provider(conn, t1) is None
    assert default_artist_image_provider(conn, 99999) is None   # pista que no existe


def test_an_unreadable_photo_falls_back_to_the_album_cover(tmp_path, monkeypatch):
    conn, t1, _ = _library(tmp_path)
    monkeypatch.setattr(covers, "artist_photo", lambda artist_id: tmp_path / "no-existe.jpg")
    (tmp_path / "m" / "cover.jpg").write_bytes(JPEG)
    assert default_artist_image_provider(conn, t1) == (JPEG, "image/jpeg")


def _serve(tmp_path, **providers):
    server = make_server(tmp_path / "lib.db", host="127.0.0.1", port=0, tls_dir=tmp_path / "tls", **providers)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def test_artist_route_serves_the_image_and_needs_a_token(tmp_path):
    conn, t1, uuid = _library(tmp_path)
    server = _serve(tmp_path, artist_image_provider=lambda c, tid: (PHOTO, "image/jpeg") if tid == t1 else None)
    try:
        assert Client(server).json("GET", f"/v1/tracks/{uuid}/artist")[0] == 401
        client = Client(server, _pair(server))
        resp, raw = client.call("GET", f"/v1/tracks/{uuid}/artist")
        assert resp.status == 200 and raw == PHOTO and resp.getheader("Content-Type") == "image/jpeg"
        assert resp.getheader("Cache-Control", "").startswith("private")
    finally:
        server.shutdown()
        server.server_close()
        conn.close()


def test_artist_route_returns_404_without_an_image_or_for_unknown_tracks(tmp_path):
    conn, t1, uuid = _library(tmp_path)
    server = _serve(tmp_path, artist_image_provider=lambda c, tid: None)
    try:
        client = Client(server, _pair(server))
        resp, raw = client.call("GET", f"/v1/tracks/{uuid}/artist")
        assert resp.status == 404 and b"no tiene imagen" in raw
        assert client.call("GET", "/v1/tracks/99999999-9999-4999-8999-999999999999/artist")[0].status == 404
    finally:
        server.shutdown()
        server.server_close()
        conn.close()


def test_cover_route_still_uses_its_own_provider(tmp_path):
    conn, t1, uuid = _library(tmp_path)
    server = _serve(tmp_path, cover_provider=lambda c, tid: (JPEG, "image/jpeg"),
                    artist_image_provider=lambda c, tid: (PHOTO, "image/jpeg"))
    try:
        client = Client(server, _pair(server))
        assert client.call("GET", f"/v1/tracks/{uuid}/cover")[1] == JPEG
        assert client.call("GET", f"/v1/tracks/{uuid}/artist")[1] == PHOTO
    finally:
        server.shutdown()
        server.server_close()
        conn.close()
