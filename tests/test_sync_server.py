"""Servidor HTTPS de sincronización de punta a punta (socket real en 127.0.0.1, certificado fijado por huella)."""
from __future__ import annotations

import hashlib
import http.client
import json
import ssl
import threading

import pytest
from sync_support import add_track

from sonoteca.core import content_hash, playlists
from sonoteca.core.db import connect
from sonoteca.sync import pairing
from sonoteca.sync.server import _parse_range, make_server

P1 = "11111111-1111-4111-8111-111111111111"
BODY = bytes(range(256)) * 400   # 102 400 bytes


class Client:
    def __init__(self, server, token: str | None = None):
        self.server, self.token = server, token
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE   # se valida a mano por huella, como hará el móvil
        self.conn = http.client.HTTPSConnection("127.0.0.1", server.port, context=ctx, timeout=10)

    def call(self, method, path, body=None, headers=None):
        headers = dict(headers or {})
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        data = json.dumps(body).encode() if body is not None else None
        if data is not None:
            headers["Content-Type"] = "application/json"
        self.conn.request(method, path, body=data, headers=headers)
        if self.conn.sock is not None:
            der = self.conn.sock.getpeercert(binary_form=True)
            assert hashlib.sha256(der).hexdigest() == self.server.fingerprint
        resp = self.conn.getresponse()
        return resp, resp.read()

    def json(self, method, path, body=None):
        resp, raw = self.call(method, path, body)
        return resp.status, json.loads(raw or b"{}")


@pytest.fixture
def env(tmp_path):
    db = tmp_path / "lib.db"
    conn = connect(db)
    t1 = add_track(conn, tmp_path / "m", "uno", content=BODY, track_no=1)
    t2 = add_track(conn, tmp_path / "m", "dos", content=b"segunda pista", track_no=2)
    add_track(conn, tmp_path / "m", "clip", kind="video", ext=".mp4")
    server = make_server(db, host="127.0.0.1", port=0, tls_dir=tmp_path / "tls",
                         cover_provider=lambda c, tid: (b"\xff\xd8JPEGDATA", "image/jpeg") if tid == t1 else None)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server, conn, t1, t2
    server.shutdown()
    server.server_close()
    conn.close()


def _pair(server):
    code = server.pairing.new_code()
    status, data = Client(server).json("POST", "/v1/pair", {"code": code, "device_id": "poco-x6-0001",
                                                             "device_name": "POCO X6"})
    assert status == 200, data
    return data["token"]


def test_ping_needs_no_token_and_leaks_nothing_else(env):
    server, *_ = env
    status, data = Client(server).json("GET", "/v1/ping")
    assert status == 200 and data["app"] == "sonoteca" and data["api"] == 1 and "tracks" not in data


def test_protected_routes_reject_missing_or_bad_token(env):
    server, *_ = env
    assert Client(server).json("GET", "/v1/manifest")[0] == 401
    assert Client(server, "nope").json("GET", "/v1/manifest")[0] == 401


def test_pairing_code_is_single_use_and_wrong_code_rejected(env):
    server, *_ = env
    code = server.pairing.new_code()
    body = {"device_id": "poco-x6-0001", "device_name": "POCO"}
    assert Client(server).json("POST", "/v1/pair", {**body, "code": "000000" if code != "000000" else "111111"})[0] == 403
    assert Client(server).json("POST", "/v1/pair", {**body, "code": code})[0] == 200
    assert Client(server).json("POST", "/v1/pair", {**body, "code": code})[0] == 403   # ya gastado


def test_pairing_locks_after_five_failures(env):
    server, *_ = env
    code = server.pairing.new_code()
    wrong = "999999" if code != "999999" else "888888"
    for _ in range(5):
        Client(server).json("POST", "/v1/pair", {"device_id": "poco-x6-0001", "device_name": "P", "code": wrong})
    assert Client(server).json("POST", "/v1/pair", {"device_id": "poco-x6-0001", "device_name": "P",
                                                    "code": code})[0] == 403


def test_token_is_stored_only_as_hash(env):
    server, conn, *_ = env
    token = _pair(server)
    row = conn.execute("SELECT token_hash FROM sync_devices").fetchone()
    assert row[0] == pairing.hash_token(token) and token not in row[0]


def test_manifest_hashes_in_background_then_lists_audio_only(env):
    server, conn, t1, t2 = env
    client = Client(server, _pair(server))
    status, first = client.json("GET", "/v1/manifest")
    assert status == 200 and first["api"] == 1 and first["schema"] == 10
    server.hasher.join(10)
    status, data = client.json("GET", "/v1/manifest")
    assert data["pending_hash"] == 0
    titles = [t["title"] for t in data["tracks"]]
    assert titles == ["uno", "dos"]          # el video no se sincroniza
    uno = data["tracks"][0]
    assert uno["size"] == len(BODY) and uno["hash"] == hashlib.sha256(BODY).hexdigest()
    assert uno["artist"] == "Artista" and uno["album"] == "Álbum" and uno["has_cover"] is False


def test_file_download_full_and_ranges_with_hash_header(env):
    server, conn, t1, _ = env
    client = Client(server, _pair(server))
    uuid = conn.execute("SELECT uuid FROM tracks WHERE id = ?", (t1,)).fetchone()[0]
    resp, raw = client.call("GET", f"/v1/tracks/{uuid}/file")
    assert resp.status == 200 and raw == BODY
    assert resp.getheader("X-Sonoteca-Hash") == hashlib.sha256(BODY).hexdigest()
    assert resp.getheader("Content-Type") == "audio/mpeg" and resp.getheader("Accept-Ranges") == "bytes"
    resp, raw = client.call("GET", f"/v1/tracks/{uuid}/file", headers={"Range": "bytes=100-199"})
    assert resp.status == 206 and raw == BODY[100:200]
    assert resp.getheader("Content-Range") == f"bytes 100-199/{len(BODY)}"
    resp, raw = client.call("GET", f"/v1/tracks/{uuid}/file", headers={"Range": f"bytes={len(BODY) - 10}-"})
    assert resp.status == 206 and raw == BODY[-10:]
    resp, raw = client.call("GET", f"/v1/tracks/{uuid}/file", headers={"Range": "bytes=-5"})
    assert resp.status == 206 and raw == BODY[-5:]
    resp, _ = client.call("GET", f"/v1/tracks/{uuid}/file", headers={"Range": "bytes=999999-"})
    assert resp.status == 416


def test_file_changed_on_disk_is_detected_by_header(env):
    server, conn, t1, _ = env
    client = Client(server, _pair(server))
    uuid, path = conn.execute("SELECT t.uuid, f.path FROM tracks t JOIN files f ON f.id = t.file_id"
                              " WHERE t.id = ?", (t1,)).fetchone()
    client.call("GET", f"/v1/tracks/{uuid}/file")
    new = b"editado" * 100
    with open(path, "wb") as handle:
        handle.write(new)
    resp, raw = client.call("GET", f"/v1/tracks/{uuid}/file")
    assert raw == new and resp.getheader("X-Sonoteca-Hash") == hashlib.sha256(new).hexdigest()


def test_video_and_unknown_tracks_are_not_served(env):
    server, conn, *_ = env
    client = Client(server, _pair(server))
    vid = conn.execute("SELECT t.uuid FROM tracks t JOIN files f ON f.id = t.file_id WHERE f.kind='video'").fetchone()[0]
    assert client.call("GET", f"/v1/tracks/{vid}/file")[0].status == 404
    assert client.call("GET", "/v1/tracks/33333333-3333-4333-8333-333333333333/file")[0].status == 404


def test_cover_and_lyrics(env):
    server, conn, t1, t2 = env
    client = Client(server, _pair(server))
    u1, u2 = (conn.execute("SELECT uuid FROM tracks WHERE id = ?", (i,)).fetchone()[0] for i in (t1, t2))
    resp, raw = client.call("GET", f"/v1/tracks/{u1}/cover")
    assert resp.status == 200 and raw == b"\xff\xd8JPEGDATA" and resp.getheader("Content-Type") == "image/jpeg"
    assert client.call("GET", f"/v1/tracks/{u2}/cover")[0].status == 404
    assert client.call("GET", f"/v1/tracks/{u1}/lyrics")[0].status == 404
    with conn:
        conn.execute("INSERT INTO lyrics (track_id, synced_lrc, original_text, language, source)"
                     " VALUES (?, '[00:01.00]hola', 'hola', 'es', 'manual')", (t1,))
    status, data = client.json("GET", f"/v1/tracks/{u1}/lyrics")
    assert status == 200 and data["synced_lrc"].startswith("[00:01.00]") and data["language"] == "es"
    client.json("GET", "/v1/manifest")   # (la primera petición lanza el cálculo de huellas)
    server.hasher.join(10)
    assert next(t for t in client.json("GET", "/v1/manifest")[1]["tracks"] if t["uuid"] == u1)["has_lyrics"]


def test_playlists_round_trip_both_directions(env):
    server, conn, t1, t2 = env
    client = Client(server, _pair(server))
    u = [conn.execute("SELECT uuid FROM tracks WHERE id = ?", (i,)).fetchone()[0] for i in (t1, t2)]
    pid = playlists.create(conn, "Del escritorio")
    playlists._rewrite(conn, pid, [t2, t1])
    client.json("GET", "/v1/manifest")
    server.hasher.join(10)
    status, data = client.json("GET", "/v1/manifest")
    assert [(p["name"], p["tracks"]) for p in data["playlists"]] == [("Del escritorio", [u[1], u[0]])]

    status, res = client.json("PUT", f"/v1/playlists/{P1}", {"name": "Del móvil", "tracks": [u[0]],
                                                              "updated_at": "2026-11-12T10:00:00.000Z"})
    assert status == 200 and res["applied"]
    assert [p["name"] for p in playlists.list_playlists(conn)] == ["Del escritorio", "Del móvil"]
    status, res = client.json("PUT", f"/v1/playlists/{P1}", {"name": "x", "tracks": [], "updated_at": "ayer"})
    assert status == 400
    assert client.json("DELETE", f"/v1/playlists/{P1}", {"deleted_at": "2026-11-12T12:00:00.000Z"})[1]["deleted"]
    status, data = client.json("GET", "/v1/manifest")
    assert P1 in [d["uuid"] for d in data["deleted_playlists"]]


def test_revoked_device_loses_access(env):
    server, conn, *_ = env
    client = Client(server, _pair(server))
    assert client.json("GET", "/v1/manifest")[0] == 200
    assert pairing.revoke(conn, "poco-x6-0001")
    assert client.json("GET", "/v1/manifest")[0] == 401


def test_certificate_is_reused_between_runs(tmp_path):
    db = tmp_path / "lib.db"
    connect(db).close()
    a = make_server(db, host="127.0.0.1", port=0, tls_dir=tmp_path / "tls")
    fp = a.fingerprint
    a.server_close()
    b = make_server(db, host="127.0.0.1", port=0, tls_dir=tmp_path / "tls")
    assert b.fingerprint == fp
    b.server_close()
    key = tmp_path / "tls" / "server-key.pem"
    import os
    import sys
    if sys.platform != "win32":
        assert os.stat(key).st_mode & 0o077 == 0   # la clave privada solo la lee el usuario


@pytest.mark.parametrize("header,size,expected", [
    ("bytes=0-9", 100, (0, 9)), ("bytes=90-", 100, (90, 99)), ("bytes=-10", 100, (90, 99)),
    ("bytes=0-999", 100, (0, 99)), ("bytes=100-", 100, None), ("bytes=5-2", 100, None),
    ("bytes=-0", 100, None), ("items=0-1", 100, None), ("bytes=0-1,5-6", 100, None), ("bytes=0-1", 0, None),
])
def test_parse_range(header, size, expected):
    assert _parse_range(header, size) == expected
