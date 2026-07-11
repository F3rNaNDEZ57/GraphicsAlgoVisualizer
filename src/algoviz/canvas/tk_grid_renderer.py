"""Tkinter rendering of a GridCanvas. This is the only module allowed to
import tkinter for the grid visualization path.
"""

from __future__ import annotations

import tkinter as tk

from .grid_canvas import GridCanvas


class TkGridRenderer:
    def __init__(self, master: tk.Misc, grid: GridCanvas, cell_size: int = 16):
        self.grid = grid
        self.cell_size = cell_size
        self.widget = tk.Canvas(
            master,
            width=grid.width * cell_size,
            height=grid.height * cell_size,
            background=grid.background,
            highlightthickness=0,
        )
        self._rects: dict[tuple[int, int], int] = {}
        grid.on_pixel(self._draw_pixel)
        grid.on_clear(self._redraw_all)

    def _draw_pixel(self, x: int, y: int, color: str) -> None:
        x0, y0 = x * self.cell_size, y * self.cell_size
        x1, y1 = x0 + self.cell_size, y0 + self.cell_size
        rect_id = self._rects.get((x, y))
        if rect_id is None:
            self._rects[(x, y)] = self.widget.create_rectangle(x0, y0, x1, y1, fill=color, outline="")
        else:
            self.widget.itemconfigure(rect_id, fill=color)

    def _redraw_all(self) -> None:
        self.widget.delete("all")
        self._rects.clear()
