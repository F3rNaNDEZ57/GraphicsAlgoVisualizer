"""Loads algorithm presets from TOML files -- bundled with the package plus
a user directory -- instead of hardcoded Python modules. This is what lets
someone add a new algorithm by dropping one text file, no Python edits.

File shape:
    [preset]
    name = "..."
    canvas = "grid" | "array" | "graph" | ...
    description = "..."   (optional)

    [canvas]               # params for CanvasType.make_canvas()
    ...

    [inputs.<key>]          # zero or more; each becomes one input widget
    type = "int" | "float" | "str" | "color" | "int_list" | "str_list"
    default = ...
    min = ...                (optional)
    max = ...                (optional)
    label = "..."            (optional, defaults to the key)

    source = '''
    ...pseudocode...
    '''
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pyalgoviz.canvas.registry import ParamSpec

BUNDLED_PRESETS_DIR = Path(__file__).resolve().parent / "presets"
USER_PRESETS_DIR = Path.home() / ".pyalgoviz" / "presets"


class PresetError(Exception):
    """A preset file is missing a required field or is otherwise invalid."""


@dataclass
class LoadedPreset:
    name: str
    canvas_type_id: str
    description: str
    canvas_params: dict[str, Any] = field(default_factory=dict)
    inputs: dict[str, ParamSpec] = field(default_factory=dict)
    source: str = ""
    path: Path | None = None


def _parse_input_spec(key: str, table: dict[str, Any]) -> ParamSpec:
    try:
        ptype = table["type"]
        default = table["default"]
    except KeyError as exc:
        raise PresetError(f"input '{key}' missing required field {exc}") from exc
    return ParamSpec(
        name=key,
        type=ptype,
        default=default,
        min=table.get("min"),
        max=table.get("max"),
        label=table.get("label", key),
    )


def parse_preset_toml(data: dict[str, Any], path: Path | None = None) -> LoadedPreset:
    try:
        preset_table = data["preset"]
        name = preset_table["name"]
        canvas_type_id = preset_table["canvas"]
    except KeyError as exc:
        raise PresetError(f"[preset] missing required field {exc}") from exc

    try:
        source = preset_table["source"]
    except KeyError as exc:
        raise PresetError(f"[preset] missing required field {exc}") from exc

    inputs = {key: _parse_input_spec(key, table) for key, table in data.get("inputs", {}).items()}

    return LoadedPreset(
        name=name,
        canvas_type_id=canvas_type_id,
        description=preset_table.get("description", ""),
        canvas_params=data.get("canvas", {}),
        inputs=inputs,
        source=source,
        path=path,
    )


def load_preset_file(path: Path) -> LoadedPreset:
    try:
        with path.open("rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as exc:
        raise PresetError(f"{path.name}: invalid TOML — {exc}") from exc
    return parse_preset_toml(data, path=path)


def load_all_presets(
    bundled_dir: Path = BUNDLED_PRESETS_DIR, user_dir: Path = USER_PRESETS_DIR
) -> tuple[dict[str, LoadedPreset], list[str]]:
    """Returns (presets keyed by name, human-readable load errors). A
    malformed file is skipped and reported, never raised -- one bad user
    preset shouldn't take down the picker. User presets win on name
    collision with bundled ones."""
    errors: list[str] = []
    presets: dict[str, LoadedPreset] = {}
    for directory in (bundled_dir, user_dir):
        if not directory.is_dir():
            continue
        for toml_path in sorted(directory.glob("*.toml")):
            try:
                preset = load_preset_file(toml_path)
            except PresetError as exc:
                errors.append(str(exc))
                continue
            presets[preset.name] = preset
    return presets, errors


def _slugify(name: str) -> str:
    slug = "".join(c.lower() if c.isalnum() else "-" for c in name)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "preset"


def _format_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(value, list):
        return "[" + ", ".join(_format_scalar(v) for v in value) + "]"
    if isinstance(value, dict):
        # Inline table -- used for canvas.nodes/canvas.edges entries in the
        # graph network format. Simpler than tracking a table path to emit
        # `[[canvas.nodes]]` array-of-tables blocks, and tomllib reads it
        # identically.
        return "{" + ", ".join(f"{key} = {_format_scalar(v)}" for key, v in value.items()) + "}"
    raise PresetError(f"cannot serialize value of type {type(value).__name__} to TOML")


def write_preset_file(preset: LoadedPreset, directory: Path = USER_PRESETS_DIR) -> Path:
    """Serializes `preset` to TOML and writes it to `directory`. A minimal
    hand-rolled writer for our own known schema -- not a general TOML
    writer -- so this stays a zero-dependency operation."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{_slugify(preset.name)}.toml"

    lines = [
        "[preset]",
        f"name = {_format_scalar(preset.name)}",
        f"canvas = {_format_scalar(preset.canvas_type_id)}",
    ]
    if preset.description:
        lines.append(f"description = {_format_scalar(preset.description)}")
    # `source` must stay inside [preset] (or appear before any [table]
    # header) -- bare keys after a table header belong to that table in
    # TOML, so putting it later would silently nest it under [canvas] or
    # the last [inputs.*] table instead of the preset root.
    lines.append(f"source = '''\n{preset.source.rstrip(chr(10))}\n'''")
    lines.append("")

    if preset.canvas_params:
        lines.append("[canvas]")
        for key, value in preset.canvas_params.items():
            lines.append(f"{key} = {_format_scalar(value)}")
        lines.append("")

    for key, spec in preset.inputs.items():
        lines.append(f"[inputs.{key}]")
        lines.append(f"type = {_format_scalar(spec.type)}")
        lines.append(f"default = {_format_scalar(spec.default)}")
        if spec.min is not None:
            lines.append(f"min = {_format_scalar(spec.min)}")
        if spec.max is not None:
            lines.append(f"max = {_format_scalar(spec.max)}")
        if spec.label:
            lines.append(f"label = {_format_scalar(spec.label)}")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path
