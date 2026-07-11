"""Tkinter rendering of a GraphCanvas as circles connected by lines."""

from __future__ import annotations

import tkinter as tk

from .graph_canvas import GraphCanvas

NODE_RADIUS = 14


class TkGraphRenderer:
    def __init__(self, master: tk.Misc, graph: GraphCanvas, cell_size: int = 40):
        self.graph = graph
        self.cell_size = cell_size
        self._node_items: dict[int, int] = {}

        max_x = max(x for x, _ in graph.positions.values())
        max_y = max(y for _, y in graph.positions.values())
        width = (max_x + 1) * cell_size
        height = (max_y + 1) * cell_size
        self.widget = tk.Canvas(master, width=width, height=height, background="white", highlightthickness=0)

        self._draw_edges()
        self._draw_nodes()
        graph.on_node(self._update_node)
        graph.on_clear(self._redraw_all)

    def _center(self, node: int) -> tuple[float, float]:
        x, y = self.graph.positions[node]
        return x * self.cell_size + self.cell_size / 2, y * self.cell_size + self.cell_size / 2

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
                self.widget.create_line(cx0, cy0, cx1, cy1, fill="#dddddd", width=2)

    def _draw_nodes(self) -> None:
        for node in self.graph.positions:
            cx, cy = self._center(node)
            color = self.graph.color_of(node)
            item = self.widget.create_oval(
                cx - NODE_RADIUS, cy - NODE_RADIUS, cx + NODE_RADIUS, cy + NODE_RADIUS,
                fill=color, outline="#333333",
            )
            self._node_items[node] = item

    def _update_node(self, node: int, color: str) -> None:
        item = self._node_items.get(node)
        if item is not None:
            self.widget.itemconfigure(item, fill=color)

    def _redraw_all(self) -> None:
        self.widget.delete("all")
        self._node_items.clear()
        self._draw_edges()
        self._draw_nodes()
