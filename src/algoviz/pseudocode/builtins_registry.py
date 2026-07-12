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


def _show_answer(*_args: Any, **_kwargs: Any) -> None:
    """No-op on purpose. ShowAnswer's only job is to mark a step boundary
    and carry its arguments in the yielded StepEvent -- a caller (e.g.
    MainWindow) reads event.args to display the result, rather than this
    function mutating anything. This is what lets it work identically
    against every canvas type, including third-party plugin canvases that
    have no shared "display a value" method to call."""
    return None


# Canvas-agnostic viz builtins: available regardless of canvas type, same
# as PLAIN_BUILTINS but is_viz=True (they still mark a step boundary and
# yield a StepEvent). ShowAnswer(value) or ShowAnswer(label, value) lets
# any algorithm's pseudocode explicitly narrate its final result -- total
# path cost, whether a search succeeded, etc -- not just imply it visually.
ALWAYS_AVAILABLE_VIZ_BUILTINS: dict[str, Callable[..., Any]] = {
    "ShowAnswer": _show_answer,
}


@dataclass(frozen=True)
class ResolvedBuiltin:
    name: str
    invoke: Callable[..., Any]
    is_viz: bool


def resolve_builtin(
    name: str,
    canvas: Any,
    viz_methods: dict[str, str] | None = None,
    plain_canvas_methods: dict[str, str] | None = None,
) -> ResolvedBuiltin:
    """Resolves a DSL name to a callable against `canvas`.

    `viz_methods`/`plain_canvas_methods` let a caller supply a specific
    canvas type's builtin maps (see canvas/registry.py's CanvasType) instead
    of the defaults below -- this is what lets a new canvas type add its
    own verbs (e.g. a tree canvas's SetChild) without editing this file.
    Defaults preserve the original behavior for callers that don't care.
    """
    viz_methods = VIZ_BUILTIN_METHODS if viz_methods is None else viz_methods
    plain_canvas_methods = PLAIN_CANVAS_METHODS if plain_canvas_methods is None else plain_canvas_methods

    if name in viz_methods:
        method_name = viz_methods[name]
        method = getattr(canvas, method_name, None)
        if method is None:
            raise PseudocodeError(
                f"'{name}' is not supported by this canvas (missing '{method_name}')"
            )
        return ResolvedBuiltin(name, method, is_viz=True)
    if name in plain_canvas_methods:
        method_name = plain_canvas_methods[name]
        method = getattr(canvas, method_name, None)
        if method is None:
            raise PseudocodeError(
                f"'{name}' is not supported by this canvas (missing '{method_name}')"
            )
        return ResolvedBuiltin(name, method, is_viz=False)
    if name in PLAIN_BUILTINS:
        return ResolvedBuiltin(name, PLAIN_BUILTINS[name], is_viz=False)
    if name in ALWAYS_AVAILABLE_VIZ_BUILTINS:
        return ResolvedBuiltin(name, ALWAYS_AVAILABLE_VIZ_BUILTINS[name], is_viz=True)
    raise PseudocodeError(f"unknown function '{name}'")
