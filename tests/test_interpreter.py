import pytest

from algoviz.pseudocode.errors import PseudocodeError
from algoviz.pseudocode.interpreter import Interpreter


def run_all(source: str, canvas):
    interp = Interpreter(source, canvas)
    list(interp.run())
    return interp


def test_assignment_and_plot_pixel(recording_canvas):
    run_all("x = 3\ny = 4\nPlotPixel(x, y)\n", recording_canvas)
    assert recording_canvas.calls == [("plot_pixel", (3, 4), {})]


def test_plot_pixel_yields_one_step_per_call(recording_canvas):
    interp = Interpreter("PlotPixel(0, 0)\nPlotPixel(1, 1)\n", recording_canvas)
    steps = list(interp.run())
    assert len(steps) == 2
    assert recording_canvas.calls == [
        ("plot_pixel", (0, 0), {}),
        ("plot_pixel", (1, 1), {}),
    ]


def test_if_else_branches(recording_canvas):
    run_all("x = 5\nif x > 3:\n    PlotPixel(1, 1)\nelse:\n    PlotPixel(2, 2)\n", recording_canvas)
    assert recording_canvas.calls == [("plot_pixel", (1, 1), {})]

    canvas2 = recording_canvas.__class__()
    run_all("x = 1\nif x > 3:\n    PlotPixel(1, 1)\nelse:\n    PlotPixel(2, 2)\n", canvas2)
    assert canvas2.calls == [("plot_pixel", (2, 2), {})]


def test_while_loop(recording_canvas):
    source = "i = 0\nwhile i < 3:\n    PlotPixel(i, 0)\n    i = i + 1\n"
    run_all(source, recording_canvas)
    assert recording_canvas.calls == [
        ("plot_pixel", (0, 0), {}),
        ("plot_pixel", (1, 0), {}),
        ("plot_pixel", (2, 0), {}),
    ]


def test_for_range_loop(recording_canvas):
    source = "for i in range(3):\n    PlotPixel(i, i)\n"
    run_all(source, recording_canvas)
    assert recording_canvas.calls == [
        ("plot_pixel", (0, 0), {}),
        ("plot_pixel", (1, 1), {}),
        ("plot_pixel", (2, 2), {}),
    ]


def test_list_subscript_get_and_set(recording_canvas):
    source = "arr = [10, 20, 30]\narr[1] = 99\nPlotPixel(arr[1], arr[0])\n"
    run_all(source, recording_canvas)
    assert recording_canvas.calls == [("plot_pixel", (99, 10), {})]


def test_aug_assign(recording_canvas):
    source = "x = 1\nx += 2\nx *= 3\nPlotPixel(x, 0)\n"
    run_all(source, recording_canvas)
    assert recording_canvas.calls == [("plot_pixel", (9, 0), {})]


def test_round_and_abs_plain_builtins(recording_canvas):
    source = "x = round(2.7)\ny = abs(-5)\nPlotPixel(x, y)\n"
    run_all(source, recording_canvas)
    assert recording_canvas.calls == [("plot_pixel", (3, 5), {})]


def test_undefined_variable_raises(recording_canvas):
    with pytest.raises(PseudocodeError, match="undefined variable"):
        run_all("PlotPixel(x, 0)\n", recording_canvas)


def test_unknown_function_raises(recording_canvas):
    with pytest.raises(PseudocodeError, match="unknown function"):
        run_all("Frobnicate(1, 2)\n", recording_canvas)


def test_unsupported_syntax_raises(recording_canvas):
    with pytest.raises(PseudocodeError, match="unsupported syntax"):
        run_all("import os\n", recording_canvas)


def test_function_def_rejected(recording_canvas):
    with pytest.raises(PseudocodeError, match="unsupported syntax"):
        run_all("def f():\n    pass\n", recording_canvas)


def test_for_loop_over_list_literal(recording_canvas):
    run_all("for i in [5, 7, 9]:\n    PlotPixel(i, 0)\n", recording_canvas)
    assert recording_canvas.calls == [
        ("plot_pixel", (5, 0), {}),
        ("plot_pixel", (7, 0), {}),
        ("plot_pixel", (9, 0), {}),
    ]


def test_for_loop_over_non_iterable_raises(recording_canvas):
    with pytest.raises(PseudocodeError, match="range\\(\\.\\.\\.\\) or a list"):
        run_all("for i in 5:\n    PlotPixel(i, 0)\n", recording_canvas)


def test_viz_builtin_inside_expression_rejected(recording_canvas):
    with pytest.raises(PseudocodeError, match="cannot be used inside an expression"):
        run_all("x = PlotPixel(0, 0)\n", recording_canvas)


def test_syntax_error_surfaces_as_pseudocode_error(recording_canvas):
    with pytest.raises(PseudocodeError, match="syntax error"):
        run_all("x = (\n", recording_canvas)


def test_canvas_missing_method_raises_clear_error():
    class BareCanvas:
        pass

    with pytest.raises(PseudocodeError, match="not supported by this canvas"):
        run_all("PlotPixel(0, 0)\n", BareCanvas())
