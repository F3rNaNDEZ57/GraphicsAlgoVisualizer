"""Registers the "graph" canvas type. Owns two codecs that both produce the
same GraphCanvas shape: the maze-as-strings codec (S=start, G=goal, #=wall,
.=open) for grid pathfinding, and the nodes/edges/weights codec for
arbitrary custom networks (hand-written TOML or the in-app graph editor).

GraphCanvas.positions is always final pixel coordinates -- parse_maze scales
its grid cells up so a maze-derived graph and a network-derived graph can
share one renderer with no per-source-format branching there.
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

MAZE_CELL_SIZE = 60


def parse_maze(
    maze: list[str], cell_size: int = MAZE_CELL_SIZE
) -> tuple[dict[int, tuple[int, int]], dict[int, list[int]], int, int]:
    positions: dict[int, tuple[int, int]] = {}
    node_id: dict[tuple[int, int], int] = {}
    next_id = 0
    start = goal = None

    for y, row in enumerate(maze):
        for x, ch in enumerate(row):
            if ch == "#":
                continue
            node_id[(x, y)] = next_id
            positions[next_id] = (x * cell_size + cell_size / 2, y * cell_size + cell_size / 2)
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


def parse_network(
    nodes: list[dict[str, Any]], edges: list[dict[str, Any]]
) -> tuple[dict[int, tuple[int, int]], dict[int, list[int]], dict[tuple[int, int], float], dict[int, str]]:
    """Decodes the explicit-network `[canvas]` format:

        nodes = [{id = 0, x = 80, y = 60, label = "A"}, ...]
        edges = [{from = 0, to = 1, weight = 4}, ...]

    Positions are pixel coordinates as-authored (by hand or by the in-app
    editor) -- no scaling, unlike the maze codec. Edges are undirected:
    each one populates both directions of the adjacency list and both
    orderings of the weight lookup. `label` is optional per node.
    """
    positions: dict[int, tuple[int, int]] = {}
    adjacency: dict[int, list[int]] = {}
    weights: dict[tuple[int, int], float] = {}
    labels: dict[int, str] = {}

    for node in nodes:
        node_id = int(node["id"])
        positions[node_id] = (node["x"], node["y"])
        adjacency.setdefault(node_id, [])
        if "label" in node:
            labels[node_id] = node["label"]

    for edge in edges:
        a, b = int(edge["from"]), int(edge["to"])
        w = float(edge.get("weight", 1))
        adjacency.setdefault(a, []).append(b)
        adjacency.setdefault(b, []).append(a)
        weights[(a, b)] = w
        weights[(b, a)] = w

    return positions, adjacency, weights, labels


def _make_canvas(params: dict[str, Any]) -> GraphCanvas:
    if "nodes" in params:
        positions, edges, weights, labels = parse_network(params["nodes"], params.get("edges", []))
        start, goal = int(params["start"]), int(params["goal"])
        return GraphCanvas(positions, edges, start, goal, weights=weights, labels=labels)

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
        "Weight": "weight",
    },
    renderers={"tk": TkGraphRenderer},
)

register(GRAPH_CANVAS_TYPE)
