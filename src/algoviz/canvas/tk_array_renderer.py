"""Tkinter rendering of an ArrayCanvas as vertical bars."""

from __future__ import annotations

import tkinter as tk

from algoviz.theme import DARK, ThemeTokens, array_kind_color

from .array_canvas import ArrayCanvas


class TkArrayRenderer:
    def __init__(
        self,
        master: tk.Misc,
        array: ArrayCanvas,
        width: int = 640,
        height: int = 320,
        bar_gap: int = 6,
        theme: ThemeTokens = DARK,
        scale: float = 1.0,
    ):
        self.array = array
        self.width = int(width * scale)
        self.height = int(height * scale)
        self.bar_gap = int(bar_gap * scale)
        self.theme = theme
        self._font_size = max(8, round(9 * scale))
        self.widget = tk.Canvas(
            master, width=self.width, height=self.height, background=theme.array_background, highlightthickness=0
        )
        self._bar_ids: list[int] = []
        self._label_ids: list[int] = []
        array.on_change(self._redraw_all)
        array.on_highlight(self._apply_highlight)
        self._redraw_all()

    def _redraw_all(self) -> None:
        self.widget.delete("all")
        self._bar_ids.clear()
        self._label_ids.clear()
        values = self.array.values
        n = len(values)
        if n == 0:
            return
        bar_w = max(1.0, (self.width - self.bar_gap * (n + 1)) / n)
        max_v = max(values) or 1
        label_space = 18
        for i, v in enumerate(values):
            x0 = self.bar_gap + i * (bar_w + self.bar_gap)
            bar_h = (v / max_v) * (self.height - 20 - label_space)
            y1 = self.height
            y0 = y1 - bar_h
            rect = self.widget.create_rectangle(
                x0, y0, x0 + bar_w, y1, fill=self.theme.array_bar, outline=self.theme.array_background, width=1
            )
            self._bar_ids.append(rect)
            if bar_w >= 14:
                label = self.widget.create_text(
                    x0 + bar_w / 2,
                    max(y0 - 10, label_space / 2),
                    text=str(v),
                    fill=self.theme.fg,
                    font=("", self._font_size),
                )
                self._label_ids.append(label)

    def _apply_highlight(self, indices: list[int], kind: str) -> None:
        self._redraw_all()
        if kind == "clear" or not indices:
            return
        color = array_kind_color(self.theme, kind)
        for i in indices:
            if 0 <= i < len(self._bar_ids):
                self.widget.itemconfigure(self._bar_ids[i], fill=color)
