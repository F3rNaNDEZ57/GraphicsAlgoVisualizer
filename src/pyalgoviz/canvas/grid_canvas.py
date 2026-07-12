"""Pixel-grid visualization model. No rendering/GUI dependency — a renderer
subscribes via on_pixel/on_clear to reflect state changes on screen.
"""

from __future__ import annotations

from typing import Callable

DEFAULT_COLOR = "red"


class GridCanvas:
    def __init__(self, width: int, height: int, background: str = "white"):
        self.width = width
        self.height = height
        self.background = background
        self._cells: dict[tuple[int, int], str] = {}
        self._pixel_listeners: list[Callable[[int, int, str], None]] = []
        self._clear_listeners: list[Callable[[], None]] = []

    def on_pixel(self, listener: Callable[[int, int, str], None]) -> None:
        self._pixel_listeners.append(listener)

    def on_clear(self, listener: Callable[[], None]) -> None:
        self._clear_listeners.append(listener)

    def detach_listeners(self) -> None:
        """Drops every registered listener -- used when a renderer bound to
        this canvas is being replaced (e.g. presentation-mode zoom), so the
        old renderer's now-destroyed Tk widget doesn't keep getting notified
        alongside the new one."""
        self._pixel_listeners.clear()
        self._clear_listeners.clear()

    def plot_pixel(self, x: int, y: int, color: str | None = None) -> None:
        x, y = int(x), int(y)
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise ValueError(f"pixel ({x}, {y}) is outside the {self.width}x{self.height} grid")
        c = color or DEFAULT_COLOR
        self._cells[(x, y)] = c
        for listener in self._pixel_listeners:
            listener(x, y, c)

    def clear(self) -> None:
        self._cells.clear()
        for listener in self._clear_listeners:
            listener()

    def color_at(self, x: int, y: int) -> str:
        return self._cells.get((x, y), self.background)

    def plotted_pixels(self) -> dict[tuple[int, int], str]:
        return dict(self._cells)
