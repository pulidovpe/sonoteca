"""Parte C con Qt: LibraryController.albumTrackIds()."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6.QtCore")

from conftest import needs_ffmpeg
from test_ui_edit import album_ids, lib  # noqa: F401  (fixture)

from sonoteca.ui.controller import LibraryController

pytestmark = needs_ffmpeg


def test_album_track_ids_lists_every_track_of_the_album_in_order(qapp, lib):  # noqa: F811
    db, _ = lib
    c = LibraryController(db)
    album, ids = album_ids(c)
    assert len(ids) >= 2 and c.albumTrackIds(album) == ids
    assert c.albumTrackIds(999999) == []


def test_artist_track_ids_and_whole_album_detection(qapp, lib):  # noqa: F811
    db, _ = lib
    c = LibraryController(db)
    album, ids = album_ids(c)
    assert c.wholeAlbumOf(ids) == album and c.wholeAlbumOf(list(reversed(ids))) == album
    assert c.wholeAlbumOf(ids[:-1]) == 0 and c.wholeAlbumOf(ids[:1]) == 0 and c.wholeAlbumOf([]) == 0
    assert set(ids) <= set(c.artistTrackIds(c.album(album)["artist_id"]))
