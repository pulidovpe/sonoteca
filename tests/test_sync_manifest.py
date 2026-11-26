"""El manifiesto anuncia TODAS las pistas de audio, aunque su huella aún no esté calculada (así el móvil ve el catálogo completo)."""
from __future__ import annotations

import os

from sync_support import add_track

from sonoteca.core import content_hash
from sonoteca.core.db import connect
from sonoteca.sync.manifest import build_manifest


def _library(tmp_path):
    conn = connect(tmp_path / "lib.db")
    t1 = add_track(conn, tmp_path / "m", "uno")
    t2 = add_track(conn, tmp_path / "m", "dos", album="Otro", track_no=2)
    add_track(conn, tmp_path / "m", "clip", kind="video", ext=".mp4")
    return conn, t1, t2


def _file_of(conn, track):
    return conn.execute("SELECT file_id FROM tracks WHERE id = ?", (track,)).fetchone()[0]


def test_every_audio_track_is_listed_before_any_hash_exists(tmp_path):
    conn, _, _ = _library(tmp_path)
    manifest = build_manifest(conn)
    assert manifest["complete"] is True and manifest["pending_hash"] == 2
    assert [t["title"] for t in manifest["tracks"]] == ["uno", "dos"]     # el video no se sincroniza
    assert all(t["hash"] is None and t["size"] is None for t in manifest["tracks"])
    assert all(t["uuid"] for t in manifest["tracks"])


def test_hashes_appear_as_they_are_computed(tmp_path):
    conn, t1, t2 = _library(tmp_path)
    digest = content_hash.ensure_hash(conn, _file_of(conn, t1))
    tracks = {t["title"]: t for t in build_manifest(conn)["tracks"]}
    assert tracks["uno"]["hash"] == digest and tracks["uno"]["size"] > 0
    assert tracks["dos"]["hash"] is None
    assert build_manifest(conn)["pending_hash"] == 1


def test_a_track_whose_file_changed_stays_listed_without_a_hash(tmp_path):
    conn, t1, _ = _library(tmp_path)
    content_hash.hash_missing(conn)
    assert build_manifest(conn)["pending_hash"] == 0
    with conn:   # el escritorio reescribió el archivo (p. ej. editó sus tags): cambia su fecha
        conn.execute("UPDATE files SET mtime_ns = mtime_ns + 1 WHERE id = ?", (_file_of(conn, t1),))
    manifest = build_manifest(conn)
    tracks = {t["title"]: t for t in manifest["tracks"]}
    assert tracks["uno"]["hash"] is None and tracks["dos"]["hash"] is not None
    assert manifest["pending_hash"] == 1 and len(manifest["tracks"]) == 2


def test_a_track_removed_from_the_library_disappears_from_the_manifest(tmp_path):
    conn, t1, _ = _library(tmp_path)
    with conn:
        conn.execute("DELETE FROM tracks WHERE id = ?", (t1,))
    assert [t["title"] for t in build_manifest(conn)["tracks"]] == ["dos"]


def test_renamed_artist_shows_the_new_name_for_the_same_uuid(tmp_path):
    conn, t1, _ = _library(tmp_path)
    before = {t["uuid"]: t for t in build_manifest(conn)["tracks"]}
    uuid = conn.execute("SELECT uuid FROM tracks WHERE id = ?", (t1,)).fetchone()[0]
    with conn:
        new_artist = conn.execute("INSERT INTO artists (name, sort_name) VALUES ('Nuevo nombre', 'Nuevo nombre')").lastrowid
        album_id = conn.execute("SELECT album_id FROM tracks WHERE id = ?", (t1,)).fetchone()[0]
        conn.execute("UPDATE albums SET album_artist_id = ? WHERE id = ?", (new_artist, album_id))
        conn.execute("UPDATE tracks SET artist_id = ? WHERE id = ?", (new_artist, t1))
    after = {t["uuid"]: t for t in build_manifest(conn)["tracks"]}
    assert before[uuid]["album_artist"] == "Artista" and after[uuid]["album_artist"] == "Nuevo nombre" and after[uuid]["artist"] == "Nuevo nombre"


def test_a_track_whose_file_is_gone_is_listed_as_unavailable_and_not_pending(tmp_path):
    conn, t1, _ = _library(tmp_path)
    content_hash.hash_missing(conn)
    path = conn.execute("SELECT path FROM files WHERE id = ?", (_file_of(conn, t1),)).fetchone()[0]
    os.remove(path)
    manifest = build_manifest(conn)
    tracks = {t["title"]: t for t in manifest["tracks"]}
    assert tracks["uno"]["available"] is False and tracks["uno"]["hash"] is None and tracks["uno"]["size"] is None
    assert tracks["dos"]["available"] is True and tracks["dos"]["hash"] is not None
    assert manifest["missing_files"] == 1 and manifest["pending_hash"] == 0 and len(manifest["tracks"]) == 2


def test_a_missing_file_without_a_hash_does_not_stay_pending_forever(tmp_path):
    conn, t1, _ = _library(tmp_path)
    os.remove(conn.execute("SELECT path FROM files WHERE id = ?", (_file_of(conn, t1),)).fetchone()[0])
    manifest = build_manifest(conn)       # nunca llegó a tener huella y su archivo ya no existe
    assert manifest["missing_files"] == 1 and manifest["pending_hash"] == 1   # solo «dos», que sí existe y aún no tiene huella
    content_hash.hash_missing(conn)
    assert build_manifest(conn)["pending_hash"] == 0


def test_video_tracks_are_counted_but_not_listed(tmp_path):
    conn, _, _ = _library(tmp_path)
    manifest = build_manifest(conn)
    assert manifest["video_tracks"] == 1 and "clip" not in [t["title"] for t in manifest["tracks"]]
    assert manifest["missing_files"] == 0 and all(t["available"] for t in manifest["tracks"])

