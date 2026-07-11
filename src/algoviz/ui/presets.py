"""Registry of algorithm presets the UI can switch between. Each preset
knows how to build its own canvas + renderer pair and initial env, so the
window can mount whichever visualization domain (grid/array/graph) the
selected algorithm needs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from algoviz.algorithms import bfs_pathfinding, bresenham_line, bubble_sort
from algoviz.canvas.array_canvas import ArrayCanvas
from algoviz.canvas.graph_canvas import GraphCanvas
from algoviz.canvas.grid_canvas import GridCanvas
from algoviz.canvas.tk_array_renderer import TkArrayRenderer
from algoviz.canvas.tk_graph_renderer import TkGraphRenderer
from algoviz.canvas.tk_grid_renderer import TkGridRenderer


@dataclass
class AlgorithmPreset:
    name: str
    source: str
    build: Callable[[], tuple[object, type]]
    initial_env: Callable[[], dict]
    input_fields: list[str] = field(default_factory=list)


def _grid_build():
    return GridCanvas(40, 30, background="black"), TkGridRenderer


def _array_build():
    return ArrayCanvas(bubble_sort.DEFAULT_VALUES), TkArrayRenderer


def _graph_build():
    graph = GraphCanvas(bfs_pathfinding.POSITIONS, bfs_pathfinding.EDGES, bfs_pathfinding.START, bfs_pathfinding.GOAL)
    return graph, TkGraphRenderer


PRESETS: dict[str, AlgorithmPreset] = {
    bresenham_line.NAME: AlgorithmPreset(
        name=bresenham_line.NAME,
        source=bresenham_line.SOURCE,
        build=_grid_build,
        initial_env=lambda: dict(bresenham_line.DEFAULT_INPUTS),
        input_fields=["xl", "yl", "xr", "yr"],
    ),
    bubble_sort.NAME: AlgorithmPreset(
        name=bubble_sort.NAME,
        source=bubble_sort.SOURCE,
        build=_array_build,
        initial_env=lambda: {},
        input_fields=[],
    ),
    bfs_pathfinding.NAME: AlgorithmPreset(
        name=bfs_pathfinding.NAME,
        source=bfs_pathfinding.SOURCE,
        build=_graph_build,
        initial_env=lambda: dict(bfs_pathfinding.DEFAULT_INPUTS),
        input_fields=[],
    ),
}
