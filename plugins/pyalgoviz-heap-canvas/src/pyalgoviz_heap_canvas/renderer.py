"""Tkinter rendering of a HeapCanvas as a binary tree -- a rendering
shape none of pyalgoviz's built-in canvases have (linear pixels/bars vs.
free-form graph), which is part of what this plugin proves.
"""

from __future__ import annotations

import tkinter as tk

from pyalgoviz.theme import DARK, ThemeTokens, array_kind_color

from .canvas import HeapCanvas

NODE_RADIUS = 16


def _node_position(index: int, width: int, level_height: int) -> tuple[float, float]:
    depth = (index + 1).bit_length() - 1
    level_start = 2**depth - 1
    pos_in_level = index - level_start
    slots = 2**depth
    x = (pos_in_level + 0.5) / slots * width
    y = depth * level_height + level_height / 2
    return x, y


class TkHeapRenderer:
    def __init__(
        self,
        master: tk.Misc,
        heap: HeapCanvas,
        width: int = 560,
        level_height: int = 70,
        theme: ThemeTokens = DARK,
    ):
        self.heap = heap
        self.width = width
        self.level_height = level_height
        self.theme = theme
        self._node_items: dict[int, int] = {}

        self.widget = tk.Canvas(
            master, width=width, height=self._height(), background=theme.array_background, highlightthickness=0
        )
        self._redraw_all()
        heap.on_change(self._redraw_all)
        heap.on_highlight(self._apply_highlight)

    def _height(self) -> int:
        n = len(self.heap.values)
        depth = max(1, n.bit_length()) if n else 1
        return depth * self.level_height + 20

    def _redraw_all(self) -> None:
        self.widget.delete("all")
        self._node_items.clear()
        values = self.heap.values
        n = len(values)

        for i in range(1, n):
            parent = (i - 1) // 2
            x0, y0 = _node_position(parent, self.width, self.level_height)
            x1, y1 = _node_position(i, self.width, self.level_height)
            self.widget.create_line(x0, y0, x1, y1, fill=self.theme.graph_edge, width=2)

        for i, v in enumerate(values):
            x, y = _node_position(i, self.width, self.level_height)
            item = self.widget.create_oval(
                x - NODE_RADIUS,
                y - NODE_RADIUS,
                x + NODE_RADIUS,
                y + NODE_RADIUS,
                fill=self.theme.array_bar,
                outline=self.theme.array_background,
                width=2,
            )
            self.widget.create_text(x, y, text=str(v), fill=self.theme.fg, font=("", 10))
            self._node_items[i] = item

    def _apply_highlight(self, indices: list[int], kind: str) -> None:
        self._redraw_all()
        if kind == "clear" or not indices:
            return
        color = array_kind_color(self.theme, kind)
        for i in indices:
            item = self._node_items.get(i)
            if item is not None:
                self.widget.itemconfigure(item, fill=color)
