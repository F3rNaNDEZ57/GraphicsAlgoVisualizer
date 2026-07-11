"""Registers the "graph" canvas type. Also owns the maze-as-strings codec
(S=start, G=goal, #=wall, .=open) -- this replaces the old
bfs_pathfinding.py's hardcoded _build_grid_graph() as a canvas-type param
codec, editable by anyone who can type '#'.
"""

from __future__ import annotations

from typing import Any

from .graph_canvas import GraphCanvas
from .registry import CanvasType, ParamSpec, register
from .tk_graph_renderer import TkGraphRenderer

DEFAULT_MAZE = [
    "S....#..",
    "...#.#..",
    "...#.#..",
    "...#....",
    "...#.#..",
    ".....#.G",
]


def parse_maze(maze: list[str]) -> tuple[dict[int, tuple[int, int]], dict[int, list[int]], int, int]:
    positions: dict[int, tuple[int, int]] = {}
    node_id: dict[tuple[int, int], int] = {}
    next_id = 0
    start = goal = None

    for y, row in enumerate(maze):
        for x, ch in enumerate(row):
            if ch == "#":
                continue
            node_id[(x, y)] = next_id
            positions[next_id] = (x, y)
            if ch == "S":
                start = next_id
            elif ch == "G":
                goal = next_id
            next_id += 1

    if start is None or goal is None:
        raise ValueError("maze must contain exactly one 'S' (start) and one 'G' (goal)")

    edges: dict[int, list[int]] = {n: [] for n in positions}
    for (x, y), n in node_id.items():
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            neighbor = (x + dx, y + dy)
            if neighbor in node_id:
                edges[n].append(node_id[neighbor])

    return positions, edges, start, goal


def _make_canvas(params: dict[str, Any]) -> GraphCanvas:
    maze = params.get("maze", DEFAULT_MAZE)
    positions, edges, start, goal = parse_maze(maze)
    return GraphCanvas(positions, edges, start, goal)


GRAPH_CANVAS_TYPE = CanvasType(
    id="graph",
    canvas_params=[ParamSpec("maze", "str_list", default=DEFAULT_MAZE, label="Maze")],
    make_canvas=_make_canvas,
    viz_builtins={"Visit": "visit", "Highlight": "highlight"},
    plain_builtins={
        "Neighbors": "neighbors",
        "NodeCount": "node_count",
        "Start": "get_start",
        "Goal": "get_goal",
    },
    renderers={"tk": TkGraphRenderer},
)

register(GRAPH_CANVAS_TYPE)
