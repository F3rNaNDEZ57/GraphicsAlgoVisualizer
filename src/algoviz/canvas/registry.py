"""Registry of canvas types. A CanvasType bundles everything needed to
mount one visualization domain (grid/array/graph/...): how to build the
model from a preset's [canvas] table, which DSL verbs it exposes, and
which renderer to use per frontend. This is what lets a preset's builtin
whitelist come from the active canvas type instead of a global dict, and
lets ui/presets.py-style code stop importing renderer classes directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal

from .base import VizCanvas

ParamType = Literal["int", "float", "str", "color", "int_list", "str_list"]


@dataclass(frozen=True)
class ParamSpec:
    name: str
    type: ParamType
    default: Any = None
    min: int | float | None = None
    max: int | float | None = None
    label: str | None = None


@dataclass(frozen=True)
class CanvasType:
    id: str
    canvas_params: list[ParamSpec]
    make_canvas: Callable[[dict[str, Any]], VizCanvas]
    viz_builtins: dict[str, str] = field(default_factory=dict)
    plain_builtins: dict[str, str] = field(default_factory=dict)
    renderers: dict[str, Callable[..., Any]] = field(default_factory=dict)


_REGISTRY: dict[str, CanvasType] = {}


def register(canvas_type: CanvasType) -> None:
    _REGISTRY[canvas_type.id] = canvas_type


def get(canvas_type_id: str) -> CanvasType:
    try:
        return _REGISTRY[canvas_type_id]
    except KeyError:
        raise KeyError(
            f"unknown canvas type '{canvas_type_id}' (available: {sorted(_REGISTRY)})"
        ) from None


def all_types() -> dict[str, CanvasType]:
    return dict(_REGISTRY)
