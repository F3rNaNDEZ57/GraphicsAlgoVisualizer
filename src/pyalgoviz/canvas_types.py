"""Import this module to populate the canvas type registry with all
built-in canvas types (grid/array/graph). Kept separate from
canvas/__init__.py (which stays empty) so that importing an individual
canvas model for headless testing never pulls in tkinter as a side
effect of importing the pyalgoviz.canvas package.
"""

from pyalgoviz.canvas import array_type, graph_type, grid_type  # noqa: F401
