"""Node/edge visualization model for graph algorithms (pathfinding, etc).
No rendering/GUI dependency. Positions and edges are fixed at construction;
pseudocode reads adjacency through Neighbors()/NodeCount() and marks
visited/path nodes through Visit()/Highlight().
"""

from __future__ import annotations

from typing import Callable

DEFAULT_COLOR = "#cccccc"
START_COLOR = "#4da3ff"
GOAL_COLOR = "#4caf50"
VISITED_COLOR = "#ffd23f"
PATH_COLOR = "#ff5d5d"


class GraphCanvas:
    def __init__(
        self,
        positions: dict[int, tuple[int, int]],
        edges: dict[int, list[int]],
        start: int,
        goal: int,
    ):
        self.positions = positions
        self.edges = edges
        self.start = start
        self.goal = goal
        self._colors: dict[int, str] = {n: DEFAULT_COLOR for n in positions}
        self._colors[start] = START_COLOR
        self._colors[goal] = GOAL_COLOR
        self._node_listeners: list[Callable[[int, str], None]] = []
        self._clear_listeners: list[Callable[[], None]] = []

    def on_node(self, listener: Callable[[int, str], None]) -> None:
        self._node_listeners.append(listener)

    def on_clear(self, listener: Callable[[], None]) -> None:
        self._clear_listeners.append(listener)

    def neighbors(self, node: int) -> list[int]:
        return list(self.edges.get(int(node), []))

    def node_count(self) -> int:
        return len(self.positions)

    def get_start(self) -> int:
        return self.start

    def get_goal(self) -> int:
        return self.goal

    def visit(self, node: int) -> None:
        node = int(node)
        if node in (self.start, self.goal):
            return
        self._colors[node] = VISITED_COLOR
        self._notify(node)

    def highlight(self, node: int, color: str | None = None) -> None:
        node = int(node)
        if node in (self.start, self.goal):
            return
        self._colors[node] = color or PATH_COLOR
        self._notify(node)

    def color_of(self, node: int) -> str:
        return self._colors[node]

    def clear(self) -> None:
        for n in self.positions:
            if n == self.start:
                self._colors[n] = START_COLOR
            elif n == self.goal:
                self._colors[n] = GOAL_COLOR
            else:
                self._colors[n] = DEFAULT_COLOR
        for listener in self._clear_listeners:
            listener()

    def _notify(self, node: int) -> None:
        for listener in self._node_listeners:
            listener(node, self._colors[node])
