"""Cola de reproducción: orden, aleatorio y repetición. Python puro, sin Qt."""
from __future__ import annotations

import random
from collections.abc import Iterable
from enum import Enum


class RepeatMode(str, Enum):
    OFF = "off"
    ALL = "all"
    ONE = "one"


class PlayQueue:
    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()
        self._items: list[int] = []
        self._order: list[int] = []  # índices de _items en el orden de reproducción
        self._pos = -1
        self.shuffle = False
        self.repeat = RepeatMode.OFF
        # Con `consume_played`, la pista que se deja atrás (porque terminó o porque se salta a otra) sale de la lista;
        # con repetir-todo pasa al final para que la lista siga girando. Se recuerda en `_history` para «anterior».
        self.consume_played = False
        self._history: list[int] = []

    def __len__(self) -> int:
        return len(self._items)

    @property
    def items(self) -> list[int]:
        return list(self._items)

    @property
    def current(self) -> int | None:
        if 0 <= self._pos < len(self._order):
            return self._items[self._order[self._pos]]
        return None

    def set_items(self, ids: Iterable[int], start: int = 0) -> int | None:
        """Reemplaza la cola y deja `start` como pista actual."""
        self._items = list(ids)
        self._history.clear()
        n = len(self._items)
        if n == 0:
            self._order, self._pos = [], -1
            return None
        start = max(0, min(start, n - 1))
        if self.shuffle:
            self._order = self._shuffled_with_first(start)
            self._pos = 0
        else:
            self._order = list(range(n))
            self._pos = start
        return self.current

    def _shuffled_with_first(self, first: int) -> list[int]:
        rest = [i for i in range(len(self._items)) if i != first]
        self._rng.shuffle(rest)
        return [first, *rest]

    def _retire_current(self) -> None:
        """Deja atrás la pista actual: sale de la lista (o pasa al final con repetir-todo). La posición queda señalando
        a la pista que ocupaba el lugar siguiente."""
        if not 0 <= self._pos < len(self._order):
            return
        index = self._order[self._pos]
        if self.repeat is RepeatMode.ALL:
            self._order.append(self._order.pop(self._pos))     # sigue en la lista, al final (no hace falta historial)
        else:
            self._history.append(self._items[index])
            del self._history[:-500]
            self.remove(self._pos)
            if not self._order:
                self._pos = -1

    def next(self, auto: bool = False) -> int | None:
        """Siguiente pista. `auto=True` es el avance al terminar una pista (respeta repetir-una).
        Devuelve None si se llegó al final sin repetición."""
        if not self._order:
            return None
        if auto and self.repeat is RepeatMode.ONE:
            return self.current
        if self._pos + 1 < len(self._order):
            if self.consume_played:
                self._retire_current()      # la posición ya señala a la siguiente
            else:
                self._pos += 1
            return self.current
        if self.repeat is RepeatMode.OFF:
            if self.consume_played and auto:
                self._retire_current()      # terminó la última: la lista queda vacía
            return None
        # repetir todo: volver al inicio (con un nuevo orden si hay aleatorio)
        if self.shuffle and len(self._order) > 1:
            last = self._order[self._pos]
            while True:
                order = list(range(len(self._items)))
                self._rng.shuffle(order)
                if order[0] != last:
                    break
            self._order = order
        self._pos = 0
        return self.current

    def previous(self) -> int | None:
        if not self._order or self._pos < 0:
            return None
        if self.consume_played and self._history and self.repeat is not RepeatMode.ALL:
            # lo último que sonó vuelve a la lista, justo antes de la pista actual
            track = self._history.pop()
            self._items.append(track)
            self._order.insert(self._pos, len(self._items) - 1)
            return self.current
        if self._pos > 0:
            self._pos -= 1
        elif self.repeat is RepeatMode.ALL:
            self._pos = len(self._order) - 1
        return self.current

    def set_shuffle(self, on: bool) -> None:
        if on == self.shuffle:
            return
        self.shuffle = on
        if not self._order:
            return
        if not 0 <= self._pos < len(self._order):  # nada sonando todavía: se reordena todo
            self._order = list(range(len(self._items)))
            if on:
                self._rng.shuffle(self._order)
            return
        current_index = self._order[self._pos]
        if on:
            self._order = self._shuffled_with_first(current_index)
            self._pos = 0
        else:
            self._order = list(range(len(self._items)))
            self._pos = current_index

    # ---- edición de la lista (cola temporal) ----
    @property
    def position(self) -> int:
        """Posición de la pista actual en el orden de reproducción (-1 si aún no se empezó)."""
        return self._pos

    def order_ids(self) -> list[int]:
        """Ids en el orden en que sonarán (con aleatorio, el orden aleatorio)."""
        return [self._items[i] for i in self._order]

    def append(self, ids: Iterable[int]) -> None:
        """Agrega al final de la lista."""
        new = list(ids)
        base = len(self._items)
        self._items.extend(new)
        self._order.extend(range(base, base + len(new)))

    def insert_next(self, ids: Iterable[int]) -> None:
        """Agrega justo después de la pista actual (o al principio si aún no suena nada)."""
        new = list(ids)
        base = len(self._items)
        self._items.extend(new)
        at = max(self._pos, -1) + 1
        self._order[at:at] = range(base, base + len(new))

    def remove(self, position: int) -> None:
        """Quita la pista que está en `position` del orden de reproducción. Si era la actual, la
        posición pasa a señalar a la siguiente (o a ninguna si era la última)."""
        if not 0 <= position < len(self._order):
            raise IndexError(position)
        index = self._order.pop(position)
        del self._items[index]
        self._order = [i - 1 if i > index else i for i in self._order]
        if position < self._pos:
            self._pos -= 1

    def move(self, src: int, dst: int) -> None:
        """Mueve una pista dentro del orden de reproducción, conservando cuál es la actual."""
        n = len(self._order)
        if not (0 <= src < n and 0 <= dst < n):
            raise IndexError((src, dst))
        self._order.insert(dst, self._order.pop(src))
        if self._pos == src:
            self._pos = dst
        elif src < self._pos <= dst:
            self._pos -= 1
        elif dst <= self._pos < src:
            self._pos += 1

    def jump_to(self, position: int) -> int | None:
        if not 0 <= position < len(self._order):
            raise IndexError(position)
        if self.consume_played and 0 <= self._pos < len(self._order) and position != self._pos:
            leaving = self._pos
            self._retire_current()          # la que sonaba sale de la lista
            if position > leaving:
                position -= 1               # las posiciones posteriores subieron un lugar
        self._pos = position
        return self.current

    def clear(self, keep_current: bool = False) -> None:
        """Vacía la lista; con `keep_current` conserva solo la pista que suena."""
        current = self.current
        self._history.clear()
        if keep_current and current is not None:
            self._items, self._order, self._pos = [current], [0], 0
        else:
            self._items, self._order, self._pos = [], [], -1

    def cycle_repeat(self) -> RepeatMode:
        order = [RepeatMode.OFF, RepeatMode.ALL, RepeatMode.ONE]
        self.repeat = order[(order.index(self.repeat) + 1) % 3]
        return self.repeat
