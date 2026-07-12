"""Registers the "array" canvas type."""

from __future__ import annotations

from typing import Any

from .array_canvas import ArrayCanvas
from .registry import CanvasType, ParamSpec, register
from .tk_array_renderer import TkArrayRenderer

DEFAULT_VALUES = [8, 3, 9, 1, 6, 4, 7, 2, 5]


def _make_canvas(params: dict[str, Any]) -> ArrayCanvas:
    values = params.get("values", DEFAULT_VALUES)
    return ArrayCanvas([int(v) for v in values])


ARRAY_CANVAS_TYPE = CanvasType(
    id="array",
    canvas_params=[ParamSpec("values", "int_list", default=DEFAULT_VALUES, label="Values")],
    make_canvas=_make_canvas,
    viz_builtins={"Swap": "swap", "SetValue": "set_value", "Compare": "compare"},
    plain_builtins={"Value": "get", "Length": "length"},
    renderers={"tk": TkArrayRenderer},
)

register(ARRAY_CANVAS_TYPE)
