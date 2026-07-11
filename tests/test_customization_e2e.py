"""Proves Phase 7's exit criterion: a non-programmer adds a new algorithm
by writing one TOML file, with zero Python edits -- reusing the existing
"array" canvas type's builtins (Value/SetValue/Length), no plugin needed.
"""

import algoviz.canvas_types  # noqa: F401 -- registers grid/array/graph canvas types
from algoviz.canvas.registry import get as get_canvas_type
from algoviz.pseudocode.interpreter import Interpreter
from algoviz.preset_loader import load_all_presets

INSERTION_SORT_TOML = """
[preset]
name = "Insertion Sort"
canvas = "array"
description = "User-authored preset, never referenced by any core module."
source = '''
n = Length()
i = 1
while i < n:
    key = Value(i)
    j = i - 1
    while j >= 0 and Value(j) > key:
        SetValue(j + 1, Value(j))
        j = j - 1
    SetValue(j + 1, key)
    i = i + 1
'''

[canvas]
values = [5, 2, 8, 1, 9, 3]
"""


def test_add_new_algorithm_via_toml_only(tmp_path):
    user_dir = tmp_path / "presets"
    user_dir.mkdir()
    (user_dir / "insertion-sort.toml").write_text(INSERTION_SORT_TOML, encoding="utf-8")

    # No bundled dir at all -- this preset exists *only* as a dropped-in file.
    presets, errors = load_all_presets(bundled_dir=tmp_path / "no-bundled", user_dir=user_dir)
    assert errors == []
    assert "Insertion Sort" in presets

    preset = presets["Insertion Sort"]
    canvas_type = get_canvas_type(preset.canvas_type_id)
    canvas = canvas_type.make_canvas(preset.canvas_params)

    interp = Interpreter(preset.source, canvas, canvas_type.viz_builtins, canvas_type.plain_builtins)
    steps = list(interp.run())

    assert canvas.values == sorted([5, 2, 8, 1, 9, 3])
    assert len(steps) > 0
