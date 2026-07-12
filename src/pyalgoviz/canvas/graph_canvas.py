"""Node/edge visualization model for graph algorithms (pathfinding, etc).
No rendering/GUI dependency. Positions and edges are fixed at construction;
pseudocode reads adjacency through Neighbors()/NodeCount() and marks
visited/path nodes through Visit()/Highlight().

Broadcasts semantic *states* ("default"/"start"/"goal"/"visited"/"path"),
not colors -- the renderer maps state to a theme color. This mirrors
ArrayCanvas's "compare"/"swap"/"write" kinds; GraphCanvas used to bake hex
colors straight into the model, which meant it couldn't be themed.
"""

from __future__ import annotations

from typing import Callable

DEFAULT_STATE = "default"
START_STATE = "start"
GOAL_STATE = "goal"
VISITED_STATE = "visited"
PATH_STATE = "path"


class GraphCanvas:
    def __init__(
        self,
        positions: dict[int, tuple[int, int]],
        edges: dict[int, list[int]],
        start: int,
        goal: int,
        weights: dict[tuple[int, int], float] | None = None,
        labels: dict[int, str] | None = None,
    ):
        self.positions = positions
        self.edges = edges
        self.start = start
        self.goal = goal
        self.weights = weights or {}
        self.labels = labels or {}
        # Only graphs built with real weight data (the network editor/TOML
        # format) show weight labels -- a maze's uniform 1.0 fallback would
        # just clutter an unweighted BFS visualization with "1" everywhere.
        self.show_weights = bool(weights)
        self._states: dict[int, str] = {n: DEFAULT_STATE for n in positions}
        self._states[start] = START_STATE
        self._states[goal] = GOAL_STATE
        self._node_listeners: list[Callable[[int, str], None]] = []
        self._clear_listeners: list[Callable[[], None]] = []

    def on_node(self, listener: Callable[[int, str], None]) -> None:
        self._node_listeners.append(listener)

    def on_clear(self, listener: Callable[[], None]) -> None:
        self._clear_listeners.append(listener)

    def detach_listeners(self) -> None:
        """Drops every registered listener -- used when a renderer bound to
        this canvas is being replaced (e.g. presentation-mode zoom), so the
        old renderer's now-destroyed Tk widget doesn't keep getting notified
        alongside the new one."""
        self._node_listeners.clear()
        self._clear_listeners.clear()

    def neighbors(self, node: int) -> list[int]:
        return list(self.edges.get(int(node), []))

    def weight(self, a: int, b: int) -> float:
        """Edge weight between a and b, undirected. Graphs built without
        explicit weight data (e.g. a maze, where every step costs the same)
        default every edge to 1.0."""
        a, b = int(a), int(b)
        if (a, b) in self.weights:
            return self.weights[(a, b)]
        if (b, a) in self.weights:
            return self.weights[(b, a)]
        return 1.0

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
        self._states[node] = VISITED_STATE
        self._notify(node)

    def highlight(self, node: int, state: str | None = None) -> None:
        node = int(node)
        if node in (self.start, self.goal):
            return
        self._states[node] = state or PATH_STATE
        self._notify(node)

    def state_of(self, node: int) -> str:
        return self._states[node]

    def clear(self) -> None:
        for n in self.positions:
            if n == self.start:
                self._states[n] = START_STATE
            elif n == self.goal:
                self._states[n] = GOAL_STATE
            else:
                self._states[n] = DEFAULT_STATE
        for listener in self._clear_listeners:
            listener()

    def _notify(self, node: int) -> None:
        for listener in self._node_listeners:
            listener(node, self._states[node])
