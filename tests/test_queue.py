import random

import pytest

from sonoteca.player.queue import PlayQueue, RepeatMode


def make(n=4, **kw):
    q = PlayQueue(random.Random(1))
    q.set_items(list(range(10, 10 + n)), **kw)
    return q


def test_sequential_and_end():
    q = make()
    assert q.current == 10
    assert [q.next(), q.next(), q.next()] == [11, 12, 13]
    assert q.next() is None  # fin sin repetición
    assert q.current == 13  # la pista actual no cambia al llegar al final


def test_start_index_and_clamp():
    assert make(start=2).current == 12
    assert make(start=99).current == 13
    assert make(start=-5).current == 10


def test_empty():
    q = PlayQueue()
    assert q.set_items([]) is None
    assert q.current is None and q.next() is None and q.previous() is None


def test_previous():
    q = make(start=2)
    assert q.previous() == 11
    assert make().previous() == 10  # al inicio se queda
    q = make()
    q.repeat = RepeatMode.ALL
    assert q.previous() == 13  # repetir todo: da la vuelta


def test_repeat_all_wraps():
    q = make(2)
    q.repeat = RepeatMode.ALL
    assert [q.next(), q.next(), q.next()] == [11, 10, 11]


def test_repeat_one_only_on_auto_advance():
    q = make()
    q.repeat = RepeatMode.ONE
    assert q.next(auto=True) == 10  # al terminar la pista se repite
    assert q.next(auto=False) == 11  # pero el botón "siguiente" avanza


def test_cycle_repeat():
    q = PlayQueue()
    assert [q.cycle_repeat() for _ in range(4)] == [
        RepeatMode.ALL, RepeatMode.ONE, RepeatMode.OFF, RepeatMode.ALL]


def test_shuffle_keeps_current_first_and_plays_each_once():
    q = PlayQueue(random.Random(3))
    q.shuffle = True
    q.set_items(range(20), start=7)
    played = [q.current]
    while (nxt := q.next()) is not None:
        played.append(nxt)
    assert played[0] == 7
    assert sorted(played) == list(range(20))


def test_toggle_shuffle_keeps_current_track():
    q = make(6, start=3)
    assert q.current == 13
    q.set_shuffle(True)
    assert q.current == 13
    q.set_shuffle(False)
    assert q.current == 13
    assert q.next() == 14  # vuelve al orden original desde la pista actual


def test_repeat_all_with_shuffle_reshuffles_without_repeating_boundary():
    q = PlayQueue(random.Random(5))
    q.shuffle = True
    q.repeat = RepeatMode.ALL
    q.set_items(range(5))
    for _ in range(4):
        q.next()
    last = q.current
    assert q.next() != last  # tras la vuelta, no empieza con la misma que acaba de sonar


# ---------------- edición de la lista (cola temporal) ----------------
def test_append_and_insert_next_without_current():
    q = PlayQueue(random.Random(1))
    assert q.position == -1 and q.current is None
    q.append([1, 2])
    q.insert_next([9])  # sin pista actual: va al principio
    assert q.order_ids() == [9, 1, 2] and q.current is None
    assert q.next() == 9 and q.position == 0  # al pedir "siguiente" empieza por la primera


def test_append_and_insert_next_around_the_current_track():
    q = make(3)  # 10, 11, 12 ; actual = 10
    q.append([50])
    q.insert_next([60, 61])
    assert q.order_ids() == [10, 60, 61, 11, 12, 50]
    assert q.current == 10 and q.next() == 60 and q.next() == 61 and q.next() == 11


def test_duplicates_are_allowed_and_independent():
    q = make(2)
    q.append([10])
    assert q.order_ids() == [10, 11, 10]
    q.remove(2)
    assert q.order_ids() == [10, 11] and q.current == 10


def test_remove_before_at_and_after_the_current_track():
    q = make(5, start=2)  # 10 11 [12] 13 14
    q.remove(0)  # antes: la actual sigue siendo la 12
    assert q.order_ids() == [11, 12, 13, 14] and q.current == 12 and q.position == 1
    q.remove(3)  # después
    assert q.order_ids() == [11, 12, 13] and q.current == 12
    q.remove(1)  # la propia actual: pasa a señalar a la siguiente
    assert q.order_ids() == [11, 13] and q.current == 13
    q.remove(1)  # la última y actual: ya no hay pista actual
    assert q.order_ids() == [11] and q.current is None
    with pytest.raises(IndexError):
        q.remove(5)


def test_move_keeps_track_of_the_current_one():
    q = make(5, start=2)  # 10 11 [12] 13 14
    q.move(2, 0)  # mover la actual
    assert q.order_ids() == [12, 10, 11, 13, 14] and q.current == 12 and q.position == 0
    q.move(4, 1)  # de después a antes de... posiciones: la actual sigue siendo la 12
    assert q.order_ids() == [12, 14, 10, 11, 13] and q.current == 12
    q = make(5, start=2)
    q.move(0, 4)  # una de antes a después de la actual
    assert q.order_ids() == [11, 12, 13, 14, 10] and q.current == 12 and q.position == 1
    q.move(4, 0)  # y de vuelta
    assert q.order_ids() == [10, 11, 12, 13, 14] and q.current == 12 and q.position == 2
    with pytest.raises(IndexError):
        q.move(0, 9)


def test_jump_and_clear():
    q = make(4)
    assert q.jump_to(2) == 12 and q.position == 2
    q.clear(keep_current=True)
    assert q.order_ids() == [12] and q.current == 12 and q.position == 0
    q.clear()
    assert q.order_ids() == [] and q.current is None and q.position == -1
    q.clear(keep_current=True)  # sin actual: queda vacía
    assert len(q) == 0
    with pytest.raises(IndexError):
        q.jump_to(0)


def test_queue_edits_work_with_shuffle():
    q = PlayQueue(random.Random(2))
    q.shuffle = True
    q.set_items(range(6), start=3)
    first = q.current
    q.append([100])
    assert q.order_ids()[-1] == 100 and q.current == first
    q.insert_next([200])
    assert q.order_ids()[1] == 200
    q.remove(1)
    assert 200 not in q.order_ids() and q.current == first
    ids = q.order_ids()
    seen = [q.current]
    while (n := q.next()) is not None:
        seen.append(n)
    assert seen == ids  # suena en el orden mostrado


def test_shuffle_toggle_and_previous_without_a_current_track():
    q = PlayQueue(random.Random(3))
    q.append(range(5))
    q.set_shuffle(True)
    assert sorted(q.order_ids()) == [0, 1, 2, 3, 4] and q.current is None
    q.set_shuffle(False)
    assert q.order_ids() == [0, 1, 2, 3, 4]
    assert q.previous() is None


# ---- lo que ya sonó sale de la lista (consume_played) ----
def _consuming(ids, start=0):
    q = PlayQueue()
    q.consume_played = True
    q.set_items(ids, start)
    return q


def test_consume_removes_each_track_after_it_finishes():
    q = _consuming([1, 2, 3])
    assert q.next(auto=True) == 2 and q.order_ids() == [2, 3] and q.current == 2
    assert q.next(auto=True) == 3 and q.order_ids() == [3]
    assert q.next(auto=True) is None and q.order_ids() == []        # terminó la última: la lista queda vacía
    assert q.current is None


def test_manual_next_on_the_last_track_keeps_it_but_skipping_ahead_removes_the_previous():
    q = _consuming([1, 2])
    assert q.next() == 2 and q.order_ids() == [2]
    assert q.next() is None and q.order_ids() == [2]                # sin siguiente: no se pierde la que suena


def test_jump_removes_the_track_that_was_playing():
    q = _consuming([1, 2, 3, 4])                              # suena 1
    assert q.jump_to(2) == 3                                  # doble clic en la 3.ª fila
    assert q.order_ids() == [2, 3, 4] and q.current == 3 and q.position == 1
    assert q.jump_to(0) == 2 and q.order_ids() == [2, 4] and q.position == 0      # saltar hacia atrás: sale la 3
    assert q.jump_to(0) == 2 and q.order_ids() == [2, 4]            # la misma fila: no pasa nada


def test_double_click_with_play_next_inserted_track():
    q = _consuming([1, 2, 3])
    q.insert_next([9])
    q.jump_to(1)                                              # lo que hace «conservar la lista» al elegir una canción
    assert q.order_ids() == [9, 2, 3] and q.current == 9


def test_previous_brings_back_what_was_played():
    q = _consuming([1, 2, 3])
    q.next(auto=True)
    q.next(auto=True)                                         # sonaron 1 y 2; suena 3
    assert q.order_ids() == [3]
    assert q.previous() == 2 and q.order_ids() == [2, 3] and q.position == 0
    assert q.previous() == 1 and q.order_ids() == [1, 2, 3]
    assert q.previous() == 1                                  # sin más historial: reinicia la actual


def test_repeat_all_rotates_instead_of_emptying_and_repeat_one_keeps_the_track():
    q = _consuming([1, 2, 3])
    q.repeat = RepeatMode.ALL
    assert q.next(auto=True) == 2 and q.order_ids() == [2, 3, 1]
    assert q.next(auto=True) == 3 and q.next(auto=True) == 1 and len(q) == 3
    q.repeat = RepeatMode.ONE
    assert q.next(auto=True) == 1 and len(q) == 3             # repetir una: no sale de la lista


def test_consume_with_shuffle_never_loses_or_repeats_tracks():
    import random
    q = PlayQueue(random.Random(7))
    q.consume_played = True
    q.shuffle = True
    q.set_items([1, 2, 3, 4, 5], 2)
    played = [q.current]
    while (n := q.next(auto=True)) is not None:
        played.append(n)
    assert sorted(played) == [1, 2, 3, 4, 5] and q.order_ids() == []


def test_default_queue_does_not_consume():
    q = PlayQueue()
    q.set_items([1, 2, 3])
    q.next()
    q.jump_to(2)
    assert q.order_ids() == [1, 2, 3]
