import importlib.metadata

from pyalgoviz.canvas import registry
from pyalgoviz.canvas.registry import CanvasType, ParamSpec
from pyalgoviz.plugins import load_drop_in_plugins, load_entry_point_plugins

FAKE_CANVAS_TYPE = CanvasType(
    id="__test_plugin_canvas__",
    canvas_params=[ParamSpec("n", "int", default=1)],
    make_canvas=lambda params: object(),
    viz_builtins={"Poke": "poke"},
    plain_builtins={},
    renderers={},
)


def _cleanup(canvas_type_id: str) -> None:
    registry._REGISTRY.pop(canvas_type_id, None)


class FakeEntryPoint:
    def __init__(self, name, loader):
        self.name = name
        self._loader = loader

    def load(self):
        return self._loader()


def test_load_entry_point_plugins_registers_valid_ones(monkeypatch):
    def fake_entry_points(*, group):
        assert group == "pyalgoviz.canvases"
        return [FakeEntryPoint("test_plugin", lambda: FAKE_CANVAS_TYPE)]

    monkeypatch.setattr(importlib.metadata, "entry_points", fake_entry_points)
    try:
        errors = load_entry_point_plugins()
        assert errors == []
        assert registry.get("__test_plugin_canvas__") is FAKE_CANVAS_TYPE
    finally:
        _cleanup("__test_plugin_canvas__")


def test_load_entry_point_plugins_collects_errors_without_raising(monkeypatch):
    def boom():
        raise RuntimeError("plugin is broken")

    def fake_entry_points(*, group):
        return [FakeEntryPoint("broken_plugin", boom)]

    monkeypatch.setattr(importlib.metadata, "entry_points", fake_entry_points)
    errors = load_entry_point_plugins()
    assert len(errors) == 1
    assert "broken_plugin" in errors[0]
    assert "plugin is broken" in errors[0]


def test_load_drop_in_plugins_registers_valid_module(tmp_path):
    plugin_file = tmp_path / "my_plugin.py"
    plugin_file.write_text(
        "from pyalgoviz.canvas.registry import CanvasType, ParamSpec\n"
        "CANVAS_TYPE = CanvasType(\n"
        "    id='__test_dropin_canvas__',\n"
        "    canvas_params=[],\n"
        "    make_canvas=lambda params: object(),\n"
        "    viz_builtins={},\n"
        "    plain_builtins={},\n"
        "    renderers={},\n"
        ")\n",
        encoding="utf-8",
    )
    try:
        errors = load_drop_in_plugins(tmp_path)
        assert errors == []
        assert registry.get("__test_dropin_canvas__").id == "__test_dropin_canvas__"
    finally:
        _cleanup("__test_dropin_canvas__")


def test_load_drop_in_plugins_missing_canvas_type_reports_error(tmp_path):
    (tmp_path / "no_canvas_type.py").write_text("x = 1\n", encoding="utf-8")
    errors = load_drop_in_plugins(tmp_path)
    assert len(errors) == 1
    assert "no module-level CANVAS_TYPE" in errors[0]


def test_load_drop_in_plugins_syntax_error_reports_error_not_raises(tmp_path):
    (tmp_path / "broken.py").write_text("def bad(:\n", encoding="utf-8")
    errors = load_drop_in_plugins(tmp_path)
    assert len(errors) == 1
    assert "broken.py" in errors[0]


def test_load_drop_in_plugins_missing_directory_returns_empty(tmp_path):
    errors = load_drop_in_plugins(tmp_path / "does-not-exist")
    assert errors == []
