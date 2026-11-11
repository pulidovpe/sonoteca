import json

from sonoteca.core import session
from sonoteca.player.queue import PlayQueue, RepeatMode


def _queue():
    q = PlayQueue()
    q.consume_played = True
    q.shuffle = True
    q.set_items([10, 20, 30, 40, 50], 2)
    q.repeat = RepeatMode.ALL
    return q


PATHS = {i: f"/m/{i}.mp3" for i in (10, 20, 30, 40, 50)}
IDS = {v: k for k, v in PATHS.items()}


def test_queue_snapshot_roundtrip_keeps_exact_shuffled_order():
    q = _queue()
    state = session.build_state(q.snapshot(), PATHS, volume=0.3, muted=True, position_ms=4321)
    json.dumps(state)
    r = session.parse_state(state, IDS)
    q2 = PlayQueue()
    q2.restore(r["items"], r["order"], r["pos"], r["shuffle"], r["repeat"], r["history"])
    assert q2.order_ids() == q.order_ids() and q2.current == q.current == 30
    assert q2.shuffle and q2.repeat is RepeatMode.ALL
    assert (r["volume"], r["muted"], r["position_ms"], r["current_missing"]) == (0.3, True, 4321, False)


def test_missing_tracks_are_skipped_and_current_missing_is_reported():
    state = session.build_state(_queue().snapshot(), PATHS, volume=0.8, muted=False, position_ms=900)
    r = session.parse_state(state, {v: k for k, v in PATHS.items() if k != 30})
    q = PlayQueue()
    q.restore(r["items"], r["order"], r["pos"], r["shuffle"], r["repeat"])
    assert r["current_missing"] and r["position_ms"] == 0 and len(q) == 4 and 30 not in q.order_ids()
    empty = session.parse_state(state, {})
    assert empty["items"] == [] and empty["pos"] == -1


def test_garbage_is_tolerated(tmp_path):
    state = session.build_state(_queue().snapshot(), PATHS, volume=0.8, muted=False, position_ms=0)
    assert session.parse_state({"version": 99}, {}) is None and session.parse_state([], {}) is None
    bad = {**state, "queue": {**state["queue"], "order": [0, 0, 1]}, "volume": "x", "repeat": "zzz"}
    r = session.parse_state(bad, IDS)
    assert r["order"] == list(range(5)) and r["volume"] == 0.8 and r["repeat"] == "off"
    f = tmp_path / "d" / "session.json"
    assert session.save(f, state) and session.load(f) == state
    f.write_text("{no json")
    assert session.load(f) is None and session.load(tmp_path / "nada") is None
