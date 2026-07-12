from pyalgoviz.canvas import registry
from pyalgoviz.canvas.registry import CanvasType, ParamSpec


def test_register_and_get_roundtrip():
    fake_type = CanvasType(
        id="__test_fake__",
        canvas_params=[ParamSpec("size", "int", default=5)],
        make_canvas=lambda params: object(),
        viz_builtins={"Poke": "poke"},
        plain_builtins={"Peek": "peek"},
        renderers={},
    )
    registry.register(fake_type)
    try:
        assert registry.get("__test_fake__") is fake_type
        assert "__test_fake__" in registry.all_types()
    finally:
        del registry._REGISTRY["__test_fake__"]


def test_get_unknown_type_raises_with_available_list():
    try:
        registry.get("__definitely_not_registered__")
        assert False, "expected KeyError"
    except KeyError as exc:
        assert "__definitely_not_registered__" in str(exc)


def test_builtin_canvas_types_are_registered_by_canvas_types_import():
    import pyalgoviz.canvas_types  # noqa: F401 -- triggers registration

    types = registry.all_types()
    assert set(types) == {"grid", "array", "graph"}
    assert types["grid"].viz_builtins == {"PlotPixel": "plot_pixel"}
    assert types["array"].plain_builtins == {"Value": "get", "Length": "length"}
    assert "Neighbors" in types["graph"].plain_builtins
    assert "tk" in types["grid"].renderers
