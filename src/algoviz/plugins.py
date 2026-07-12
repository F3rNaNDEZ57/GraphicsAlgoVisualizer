"""Loads canvas type plugins from two sources, neither requiring any edit
to algoviz's own source:

1. Pip-installed packages that publish a CanvasType via the
   "algoviz.canvases" entry point group.
2. Drop-in scripts in ~/.algoviz/plugins/*.py, each exposing a
   module-level CANVAS_TYPE -- a power-user door that runs arbitrary
   local Python at the same trust level as installing a package.

Both loaders never raise on a single bad plugin; they collect human-
readable error strings instead, same philosophy as preset_loader.py's
"skip and report" handling of malformed preset files.
"""

from __future__ import annotations

import importlib.metadata
import importlib.util
from pathlib import Path

from algoviz.canvas.registry import register

ENTRY_POINT_GROUP = "algoviz.canvases"
DEFAULT_PLUGINS_DIR = Path.home() / ".algoviz" / "plugins"


def load_entry_point_plugins(group: str = ENTRY_POINT_GROUP) -> list[str]:
    errors: list[str] = []
    for entry_point in importlib.metadata.entry_points(group=group):
        try:
            canvas_type = entry_point.load()
            register(canvas_type)
        except Exception as exc:  # noqa: BLE001 -- a bad plugin must not take down startup
            errors.append(f"plugin '{entry_point.name}': {exc}")
    return errors


def load_drop_in_plugins(directory: Path = DEFAULT_PLUGINS_DIR) -> list[str]:
    errors: list[str] = []
    if not directory.is_dir():
        return errors

    for path in sorted(directory.glob("*.py")):
        try:
            spec = importlib.util.spec_from_file_location(f"algoviz_plugin_{path.stem}", path)
            if spec is None or spec.loader is None:
                errors.append(f"plugin '{path.name}': could not load module spec")
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            canvas_type = getattr(module, "CANVAS_TYPE", None)
            if canvas_type is None:
                errors.append(f"plugin '{path.name}': no module-level CANVAS_TYPE found")
                continue
            register(canvas_type)
        except Exception as exc:  # noqa: BLE001 -- a bad plugin must not take down startup
            errors.append(f"plugin '{path.name}': {exc}")
    return errors


def load_all_plugins(drop_in_dir: Path = DEFAULT_PLUGINS_DIR) -> list[str]:
    return load_entry_point_plugins() + load_drop_in_plugins(drop_in_dir)
