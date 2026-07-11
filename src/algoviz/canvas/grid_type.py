"""Registers the "grid" canvas type. This is the one place allowed to
import both a canvas model and its Tk renderer together -- the model
itself (grid_canvas.py) stays GUI-free."""

from __future__ import annotations

from typing import Any

from .grid_canvas import GridCanvas
from .registry import CanvasType, ParamSpec, register
from .tk_grid_renderer import TkGridRenderer


def _make_canvas(params: dict[str, Any]) -> GridCanvas:
    return GridCanvas(
        width=int(params.get("width", 40)),
        height=int(params.get("height", 30)),
        background=str(params.get("background", "white")),
    )


GRID_CANVAS_TYPE = CanvasType(
    id="grid",
    canvas_params=[
        ParamSpec("width", "int", default=40, min=1, label="Width"),
        ParamSpec("height", "int", default=30, min=1, label="Height"),
        ParamSpec("background", "color", default="white", label="Background"),
    ],
    make_canvas=_make_canvas,
    viz_builtins={"PlotPixel": "plot_pixel"},
    plain_builtins={},
    renderers={"tk": TkGridRenderer},
)

register(GRID_CANVAS_TYPE)
