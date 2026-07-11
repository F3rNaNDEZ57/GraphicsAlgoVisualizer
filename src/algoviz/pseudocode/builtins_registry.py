"""Whitelisted functions callable from pseudocode.

Viz builtins map to a method on the active Canvas and mark a step boundary
(the interpreter yields after invoking one). Plain builtins are ordinary
Python functions usable inside expressions and never yield.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .errors import PseudocodeError

VIZ_BUILTIN_METHODS: dict[str, str] = {
    "PlotPixel": "plot_pixel",
    "Swap": "swap",
    "SetValue": "set_value",
    "Compare": "compare",
    "Visit": "visit",
    "Highlight": "highlight",
}

# Canvas methods callable inside expressions: read-only, never yield a step.
PLAIN_CANVAS_METHODS: dict[str, str] = {
    "Value": "get",
    "Length": "length",
    "Neighbors": "neighbors",
    "NodeCount": "node_count",
}

PLAIN_BUILTINS: dict[str, Callable[..., Any]] = {
    "round": round,
    "abs": abs,
    "len": len,
    "int": int,
    "range": range,
}


@dataclass(frozen=True)
class ResolvedBuiltin:
    name: str
    invoke: Callable[..., Any]
    is_viz: bool


def resolve_builtin(name: str, canvas: Any) -> ResolvedBuiltin:
    if name in VIZ_BUILTIN_METHODS:
        method_name = VIZ_BUILTIN_METHODS[name]
        method = getattr(canvas, method_name, None)
        if method is None:
            raise PseudocodeError(
                f"'{name}' is not supported by this canvas (missing '{method_name}')"
            )
        return ResolvedBuiltin(name, method, is_viz=True)
    if name in PLAIN_CANVAS_METHODS:
        method_name = PLAIN_CANVAS_METHODS[name]
        method = getattr(canvas, method_name, None)
        if method is None:
            raise PseudocodeError(
                f"'{name}' is not supported by this canvas (missing '{method_name}')"
            )
        return ResolvedBuiltin(name, method, is_viz=False)
    if name in PLAIN_BUILTINS:
        return ResolvedBuiltin(name, PLAIN_BUILTINS[name], is_viz=False)
    raise PseudocodeError(f"unknown function '{name}'")
