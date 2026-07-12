"""Tkinter rendering of a GraphCanvas as circles connected by lines.
GraphCanvas.positions are already final pixel coordinates (both the maze
codec and the network codec produce them that way), so this renderer does
no per-node scaling of its own beyond the optional `scale` factor used by
presentation mode to zoom the whole drawing up."""

from __future__ import annotations

import tkinter as tk

from algoviz.theme import DARK, ThemeTokens, graph_state_color

from .graph_canvas import GraphCanvas

NODE_RADIUS = 15
MARGIN = 40


class TkGraphRenderer:
    def __init__(self, master: tk.Misc, graph: GraphCanvas, theme: ThemeTokens = DARK, scale: float = 1.0):
        self.graph = graph
        self.theme = theme
        self.scale = scale
        self._node_items: dict[int, int] = {}

        max_x = max(x for x, _ in graph.positions.values())
        max_y = max(y for _, y in graph.positions.values())
        width = (max_x + MARGIN) * scale
        height = (max_y + MARGIN) * scale
        self.widget = tk.Canvas(
            master, width=width, height=height, background=theme.graph_background, highlightthickness=0
        )

        self._draw_edges()
        self._draw_nodes()
        graph.on_node(self._update_node)
        graph.on_clear(self._redraw_all)

    def _center(self, node: int) -> tuple[float, float]:
        x, y = self.graph.positions[node]
        return x * self.scale, y * self.scale

    def _draw_edges(self) -> None:
        seen: set[tuple[int, int]] = set()
        for node, neighbors in self.graph.edges.items():
            cx0, cy0 = self._center(node)
            for nb in neighbors:
                key = (min(node, nb), max(node, nb))
                if key in seen:
                    continue
                seen.add(key)
                cx1, cy1 = self._center(nb)
                self.widget.create_line(cx0, cy0, cx1, cy1, fill=self.theme.graph_edge, width=2)
                if self.graph.show_weights:
                    mx, my = (cx0 + cx1) / 2, (cy0 + cy1) / 2
                    label = _format_weight(self.graph.weight(node, nb))
                    self.widget.create_rectangle(
                        mx - 12, my - 9, mx + 12, my + 9, fill=self.theme.panel_bg, outline=""
                    )
                    self.widget.create_text(mx, my, text=label, fill=self.theme.fg, font=("TkDefaultFont", 9))

    def _draw_nodes(self) -> None:
        radius = NODE_RADIUS * self.scale
        for node in self.graph.positions:
            cx, cy = self._center(node)
            color = graph_state_color(self.theme, self.graph.state_of(node))
            item = self.widget.create_oval(
                cx - radius,
                cy - radius,
                cx + radius,
                cy + radius,
                fill=color,
                outline=self.theme.graph_background,
                width=2,
            )
            self._node_items[node] = item
            label = self.graph.labels.get(node)
            if label:
                self.widget.create_text(
                    cx, cy + radius + 10, text=label, fill=self.theme.fg, font=("TkDefaultFont", 9)
                )

    def _update_node(self, node: int, state: str) -> None:
        item = self._node_items.get(node)
        if item is not None:
            self.widget.itemconfigure(item, fill=graph_state_color(self.theme, state))

    def _redraw_all(self) -> None:
        self.widget.delete("all")
        self._node_items.clear()
        self._draw_edges()
        self._draw_nodes()


def _format_weight(value: float) -> str:
    return str(int(value)) if value == int(value) else str(value)
