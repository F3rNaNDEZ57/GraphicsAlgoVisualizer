"""Extracted after three concrete canvases (grid, array, graph) existed.

GridCanvas, ArrayCanvas, and GraphCanvas have almost no method surface in
common by design -- each domain needs different builtins (PlotPixel vs.
Value/Swap vs. Visit/Neighbors) -- so this intentionally stays thin rather
than forcing an artificial shared interface. The one real commonality is
that every canvas can be reset to its start state between runs.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class VizCanvas(Protocol):
    def clear(self) -> None: ...
