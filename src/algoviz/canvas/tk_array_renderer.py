"""Tkinter rendering of an ArrayCanvas as vertical bars."""

from __future__ import annotations

import tkinter as tk

from .array_canvas import ArrayCanvas

BAR_COLOR = "#4da3ff"
COMPARE_COLOR = "#ffd23f"
SWAP_COLOR = "#ff5d5d"
WRITE_COLOR = "#4caf50"

_HIGHLIGHT_COLORS = {"compare": COMPARE_COLOR, "swap": SWAP_COLOR, "write": WRITE_COLOR}


class TkArrayRenderer:
    def __init__(self, master: tk.Misc, array: ArrayCanvas, width: int = 640, height: int = 300, bar_gap: int = 4):
        self.array = array
        self.width = width
        self.height = height
        self.bar_gap = bar_gap
        self.widget = tk.Canvas(master, width=width, height=height, background="white", highlightthickness=0)
        self._bar_ids: list[int] = []
        array.on_change(self._redraw_all)
        array.on_highlight(self._apply_highlight)
        self._redraw_all()

    def _redraw_all(self) -> None:
        self.widget.delete("all")
        self._bar_ids.clear()
        values = self.array.values
        n = len(values)
        if n == 0:
            return
        bar_w = max(1.0, (self.width - self.bar_gap * (n + 1)) / n)
        max_v = max(values) or 1
        for i, v in enumerate(values):
            x0 = self.bar_gap + i * (bar_w + self.bar_gap)
            bar_h = (v / max_v) * (self.height - 20)
            y1 = self.height
            y0 = y1 - bar_h
            rect = self.widget.create_rectangle(x0, y0, x0 + bar_w, y1, fill=BAR_COLOR, outline="")
            self._bar_ids.append(rect)

    def _apply_highlight(self, indices: list[int], kind: str) -> None:
        self._redraw_all()
        if kind == "clear" or not indices:
            return
        color = _HIGHLIGHT_COLORS.get(kind, BAR_COLOR)
        for i in indices:
            if 0 <= i < len(self._bar_ids):
                self.widget.itemconfigure(self._bar_ids[i], fill=color)
