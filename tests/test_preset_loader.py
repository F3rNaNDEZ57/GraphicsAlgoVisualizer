import tomllib

import pytest

from algoviz.canvas.registry import ParamSpec
from algoviz.preset_loader import (
    LoadedPreset,
    PresetError,
    load_all_presets,
    load_preset_file,
    parse_preset_toml,
    write_preset_file,
)

MINIMAL_TOML = """
[preset]
name = "Test Preset"
canvas = "array"
source = '''
PlotPixel(0, 0)
'''

[canvas]
values = [1, 2, 3]

[inputs.x]
type = "int"
default = 5
min = 0
max = 10
label = "X value"
"""


def test_parse_preset_toml_minimal_fields():
    data = tomllib.loads(MINIMAL_TOML)
    preset = parse_preset_toml(data)
    assert preset.name == "Test Preset"
    assert preset.canvas_type_id == "array"
    assert preset.canvas_params == {"values": [1, 2, 3]}
    assert preset.inputs["x"] == ParamSpec("x", "int", default=5, min=0, max=10, label="X value")
    assert "PlotPixel(0, 0)" in preset.source


def test_parse_preset_toml_missing_preset_table_raises():
    with pytest.raises(PresetError, match="preset"):
        parse_preset_toml({})


def test_parse_preset_toml_missing_source_raises():
    data = tomllib.loads('[preset]\nname = "X"\ncanvas = "grid"\n')
    with pytest.raises(PresetError, match="source"):
        parse_preset_toml(data)


def test_load_preset_file_invalid_toml_raises_preset_error(tmp_path):
    bad = tmp_path / "broken.toml"
    bad.write_text("this is not [valid toml", encoding="utf-8")
    with pytest.raises(PresetError, match="invalid TOML"):
        load_preset_file(bad)


def test_load_all_presets_user_dir_overrides_bundled_on_name_collision(tmp_path):
    bundled = tmp_path / "bundled"
    user = tmp_path / "user"
    bundled.mkdir()
    user.mkdir()

    (bundled / "a.toml").write_text(MINIMAL_TOML, encoding="utf-8")
    overriding = MINIMAL_TOML.replace("values = [1, 2, 3]", "values = [9, 9, 9]")
    (user / "a.toml").write_text(overriding, encoding="utf-8")

    presets, errors = load_all_presets(bundled_dir=bundled, user_dir=user)
    assert errors == []
    assert presets["Test Preset"].canvas_params["values"] == [9, 9, 9]


def test_load_all_presets_skips_malformed_file_and_reports_error(tmp_path):
    directory = tmp_path / "presets"
    directory.mkdir()
    (directory / "good.toml").write_text(MINIMAL_TOML, encoding="utf-8")
    (directory / "bad.toml").write_text("not valid toml [[[", encoding="utf-8")

    presets, errors = load_all_presets(bundled_dir=directory, user_dir=tmp_path / "empty")
    assert "Test Preset" in presets
    assert len(errors) == 1
    assert "bad.toml" in errors[0]


def test_load_all_presets_missing_directories_returns_empty(tmp_path):
    presets, errors = load_all_presets(bundled_dir=tmp_path / "nope", user_dir=tmp_path / "also-nope")
    assert presets == {}
    assert errors == []


def test_write_preset_file_roundtrip(tmp_path):
    original = LoadedPreset(
        name="My Custom Sort",
        canvas_type_id="array",
        description="A test preset",
        canvas_params={"values": [4, 2, 7]},
        inputs={"k": ParamSpec("k", "int", default=3, min=1, max=9, label="K")},
        source="Compare(0, 1)\nSwap(0, 1)\n",
    )

    path = write_preset_file(original, directory=tmp_path)
    assert path.name == "my-custom-sort.toml"

    reloaded = load_preset_file(path)
    assert reloaded.name == original.name
    assert reloaded.canvas_type_id == original.canvas_type_id
    assert reloaded.description == original.description
    assert reloaded.canvas_params == original.canvas_params
    assert reloaded.inputs == original.inputs
    assert reloaded.source.strip() == original.source.strip()


def test_write_preset_file_slug_handles_special_characters(tmp_path):
    preset = LoadedPreset(name="Foo & Bar!!  Baz", canvas_type_id="grid", description="", source="PlotPixel(0,0)\n")
    path = write_preset_file(preset, directory=tmp_path)
    assert path.name == "foo-bar-baz.toml"


def test_write_preset_file_roundtrips_network_graph_with_inline_tables(tmp_path):
    original = LoadedPreset(
        name="Custom Network",
        canvas_type_id="graph",
        description="",
        canvas_params={
            "start": 0,
            "goal": 2,
            "nodes": [
                {"id": 0, "x": 10, "y": 20, "label": "A"},
                {"id": 1, "x": 100, "y": 20},
                {"id": 2, "x": 200, "y": 20, "label": "C"},
            ],
            "edges": [
                {"from": 0, "to": 1, "weight": 4},
                {"from": 1, "to": 2, "weight": 7.5},
            ],
        },
        source="Visit(0)\n",
    )

    path = write_preset_file(original, directory=tmp_path)
    reloaded = load_preset_file(path)

    assert reloaded.canvas_params == original.canvas_params
