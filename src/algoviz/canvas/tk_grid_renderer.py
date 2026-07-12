"""Tkinter rendering of a GridCanvas. This is the only module allowed to
import tkinter for the grid visualization path.
"""

from __future__ import annotations

import tkinter as tk

from algoviz.theme import DARK, ThemeTokens

from .grid_canvas import GridCanvas


class TkGridRenderer:
    def __init__(
        self,
        master: tk.Misc,
        grid: GridCanvas,
        cell_size: int = 18,
        theme: ThemeTokens = DARK,
        scale: float = 1.0,
    ):
        self.grid = grid
        self.cell_size = max(1, round(cell_size * scale))
        self.theme = theme
        self.widget = tk.Canvas(
            master,
            width=grid.width * self.cell_size,
            height=grid.height * self.cell_size,
            background=grid.background,
            highlightthickness=0,
        )
        self._rects: dict[tuple[int, int], int] = {}
        self._draw_grid_lines()
        # Reflects any pixels already plotted before this renderer existed
        # (e.g. a renderer rebuilt mid-run for presentation-mode zoom) --
        # mirrors how the array/graph renderers redraw full current state
        # on construction instead of only listening for future changes.
        for (x, y), color in grid.plotted_pixels().items():
            self._draw_pixel(x, y, color)
        grid.on_pixel(self._draw_pixel)
        grid.on_clear(self._redraw_all)

    def _draw_grid_lines(self) -> None:
        width = self.grid.width * self.cell_size
        height = self.grid.height * self.cell_size
        for x in range(0, width + 1, self.cell_size):
            self.widget.create_line(x, 0, x, height, fill=self.theme.grid_line)
        for y in range(0, height + 1, self.cell_size):
            self.widget.create_line(0, y, width, y, fill=self.theme.grid_line)

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
        self._draw_grid_lines()
