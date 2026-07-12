"""Theme tokens shared by every renderer, so colors live in one place
instead of being module-level constants scattered across
tk_grid_renderer.py/tk_array_renderer.py/tk_graph_renderer.py. No GUI
dependency here -- renderers import this, not the other way around.
"""

from __future__ import annotations

import tomllib
from dataclasses import asdict, dataclass, fields
from pathlib import Path

USER_THEME_PATH = Path.home() / ".pyalgoviz" / "theme.toml"


@dataclass(frozen=True)
class ThemeTokens:
    name: str

    # shell chrome
    bg: str
    fg: str
    panel_bg: str
    accent: str

    # grid canvas
    grid_background: str
    grid_line: str

    # array canvas
    array_background: str
    array_bar: str
    array_compare: str
    array_swap: str
    array_write: str

    # graph canvas (state -> color)
    graph_background: str
    graph_edge: str
    graph_default: str
    graph_start: str
    graph_goal: str
    graph_visited: str
    graph_path: str


DARK = ThemeTokens(
    name="dark",
    bg="#1e1e1e",
    fg="#e6e6e6",
    panel_bg="#2a2a2a",
    accent="#4da3ff",
    grid_background="#0d0d0d",
    grid_line="#232323",
    array_background="#1e1e1e",
    array_bar="#4da3ff",
    array_compare="#ffd23f",
    array_swap="#ff5d5d",
    array_write="#4caf50",
    graph_background="#1e1e1e",
    graph_edge="#3a3a3a",
    graph_default="#4a4a4a",
    graph_start="#4da3ff",
    graph_goal="#4caf50",
    graph_visited="#ffd23f",
    graph_path="#ff5d5d",
)

LIGHT = ThemeTokens(
    name="light",
    bg="#f5f5f5",
    fg="#1a1a1a",
    panel_bg="#ffffff",
    accent="#2563eb",
    grid_background="#ffffff",
    grid_line="#e2e2e2",
    array_background="#f5f5f5",
    array_bar="#2563eb",
    array_compare="#d97706",
    array_swap="#dc2626",
    array_write="#16a34a",
    graph_background="#f5f5f5",
    graph_edge="#d4d4d4",
    graph_default="#c9c9c9",
    graph_start="#2563eb",
    graph_goal="#16a34a",
    graph_visited="#d97706",
    graph_path="#dc2626",
)

BUILTIN_THEMES: dict[str, ThemeTokens] = {"dark": DARK, "light": LIGHT}

GRAPH_STATE_TOKEN = {
    "default": "graph_default",
    "start": "graph_start",
    "goal": "graph_goal",
    "visited": "graph_visited",
    "path": "graph_path",
}


def graph_state_color(theme: ThemeTokens, state: str) -> str:
    return getattr(theme, GRAPH_STATE_TOKEN.get(state, "graph_default"))


ARRAY_KIND_TOKEN = {
    "compare": "array_compare",
    "swap": "array_swap",
    "write": "array_write",
}


def array_kind_color(theme: ThemeTokens, kind: str) -> str:
    return getattr(theme, ARRAY_KIND_TOKEN.get(kind, "array_bar"), theme.array_bar)


def load_theme(name: str = "dark", path: Path = USER_THEME_PATH) -> ThemeTokens:
    """Starts from a builtin theme, then applies a shallow field-by-field
    override from `[theme]` in `path` if it exists and parses. A missing
    or malformed override file silently falls back to the builtin --
    never crashes the app over a theme file."""
    base = BUILTIN_THEMES.get(name, DARK)
    if not path.is_file():
        return base
    try:
        with path.open("rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError:
        return base

    overrides = data.get("theme", {})
    valid_fields = {f.name for f in fields(ThemeTokens)} - {"name"}
    merged = asdict(base)
    for key, value in overrides.items():
        if key in valid_fields:
            merged[key] = value
    return ThemeTokens(**merged)
