"""Registers the "heap" canvas type. This is what's published via the
algoviz.canvases entry point -- the only thing algoviz core needs to
discover this plugin is this one CanvasType instance.
"""

from __future__ import annotations

from typing import Any

from algoviz.canvas.registry import CanvasType, ParamSpec

from .canvas import HeapCanvas
from .renderer import TkHeapRenderer

DEFAULT_VALUES = [9, 4, 7, 1, 8, 3, 6, 2, 5]


def _make_canvas(params: dict[str, Any]) -> HeapCanvas:
    values = params.get("values", DEFAULT_VALUES)
    return HeapCanvas([int(v) for v in values])


HEAP_CANVAS_TYPE = CanvasType(
    id="heap",
    canvas_params=[ParamSpec("values", "int_list", default=DEFAULT_VALUES, label="Values")],
    make_canvas=_make_canvas,
    viz_builtins={"SetValue": "set_value", "Swap": "swap", "Compare": "compare"},
    plain_builtins={
        "Value": "get",
        "Length": "length",
        "Parent": "parent",
        "LeftChild": "left_child",
        "RightChild": "right_child",
    },
    renderers={"tk": TkHeapRenderer},
)
