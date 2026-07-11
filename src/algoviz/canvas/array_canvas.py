"""Array/bars visualization model for sorting-family algorithms. No
rendering/GUI dependency. The canvas owns the values being visualized —
pseudocode reads/mutates them only through builtins (Value, SetValue, Swap,
Compare), never through a raw Python list variable.
"""

from __future__ import annotations

from typing import Callable


class ArrayCanvas:
    def __init__(self, values: list[int]):
        self._initial_values = list(values)
        self.values: list[int] = list(values)
        self._change_listeners: list[Callable[[], None]] = []
        self._highlight_listeners: list[Callable[[list[int], str], None]] = []

    def on_change(self, listener: Callable[[], None]) -> None:
        self._change_listeners.append(listener)

    def on_highlight(self, listener: Callable[[list[int], str], None]) -> None:
        self._highlight_listeners.append(listener)

    def get(self, i: int) -> int:
        return self.values[int(i)]

    def length(self) -> int:
        return len(self.values)

    def set_value(self, i: int, value: int) -> None:
        i = int(i)
        self.values[i] = value
        self._notify_change()
        self._notify_highlight([i], "write")

    def swap(self, i: int, j: int) -> None:
        i, j = int(i), int(j)
        self.values[i], self.values[j] = self.values[j], self.values[i]
        self._notify_change()
        self._notify_highlight([i, j], "swap")

    def compare(self, i: int, j: int) -> None:
        self._notify_highlight([int(i), int(j)], "compare")

    def clear(self) -> None:
        self.values = list(self._initial_values)
        self._notify_change()
        self._notify_highlight([], "clear")

    def _notify_change(self) -> None:
        for listener in self._change_listeners:
            listener()

    def _notify_highlight(self, indices: list[int], kind: str) -> None:
        for listener in self._highlight_listeners:
            listener(indices, kind)
