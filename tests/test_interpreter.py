import pytest

from algoviz.pseudocode.errors import PseudocodeError
from algoviz.pseudocode.interpreter import Interpreter
from algoviz.pseudocode.step_event import StepEvent


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


def test_step_events_carry_action_args_and_lineno(recording_canvas):
    interp = Interpreter("x = 1\nPlotPixel(x, 2)\n", recording_canvas)
    steps = list(interp.run())
    assert steps == [StepEvent(action="PlotPixel", args=(1, 2), lineno=2)]


def test_step_budget_raises_on_viz_free_infinite_loop(recording_canvas):
    interp = Interpreter("i = 0\nwhile True:\n    i = i + 1\n", recording_canvas, step_budget=1000)
    with pytest.raises(PseudocodeError, match="step budget exceeded"):
        list(interp.run())


def test_step_budget_resets_after_each_yield(recording_canvas):
    # 5 loop iterations, each doing a handful of statements plus one viz
    # call that resets the budget counter -- should not raise even with a
    # tiny budget, since the budget only guards *between* yields.
    source = "i = 0\nwhile i < 5:\n    PlotPixel(i, 0)\n    i = i + 1\n"
    interp = Interpreter(source, recording_canvas, step_budget=10)
    steps = list(interp.run())
    assert len(steps) == 5


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


def test_and_short_circuits_and_does_not_evaluate_right_side(recording_canvas):
    # Guard-pattern: `i < len(arr) and arr[i] > 0` must not evaluate the
    # right side once the left side is false, or an out-of-bounds index
    # read blows up -- exactly the shape a heap/tree bounds check needs.
    source = "arr = [1, 2, 3]\ni = 5\nif i < 3 and arr[i] > 0:\n    PlotPixel(1, 1)\nelse:\n    PlotPixel(2, 2)\n"
    run_all(source, recording_canvas)
    assert recording_canvas.calls == [("plot_pixel", (2, 2), {})]


def test_or_short_circuits_and_does_not_evaluate_right_side(recording_canvas):
    source = "arr = [1, 2, 3]\ni = 5\nif i >= 3 or arr[i] > 0:\n    PlotPixel(1, 1)\nelse:\n    PlotPixel(2, 2)\n"
    run_all(source, recording_canvas)
    assert recording_canvas.calls == [("plot_pixel", (1, 1), {})]


@pytest.mark.parametrize(
    "a, b, expected",
    [(True, True, True), (True, False, False), (False, True, False), (False, False, False)],
)
def test_and_truth_table(recording_canvas, a, b, expected):
    source = f"a = {a}\nb = {b}\nif a and b:\n    PlotPixel(1, 1)\nelse:\n    PlotPixel(2, 2)\n"
    run_all(source, recording_canvas)
    expected_pixel = (1, 1) if expected else (2, 2)
    assert recording_canvas.calls == [("plot_pixel", expected_pixel, {})]


@pytest.mark.parametrize(
    "a, b, expected",
    [(True, True, True), (True, False, True), (False, True, True), (False, False, False)],
)
def test_or_truth_table(recording_canvas, a, b, expected):
    source = f"a = {a}\nb = {b}\nif a or b:\n    PlotPixel(1, 1)\nelse:\n    PlotPixel(2, 2)\n"
    run_all(source, recording_canvas)
    expected_pixel = (1, 1) if expected else (2, 2)
    assert recording_canvas.calls == [("plot_pixel", expected_pixel, {})]


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


def test_show_answer_is_canvas_agnostic_and_yields_a_step(recording_canvas):
    interp = Interpreter('ShowAnswer("cost", 5)\n', recording_canvas)
    steps = list(interp.run())
    assert steps == [StepEvent(action="ShowAnswer", args=("cost", 5), lineno=1)]


def test_show_answer_works_with_a_single_argument(recording_canvas):
    interp = Interpreter("ShowAnswer(42)\n", recording_canvas)
    steps = list(interp.run())
    assert steps == [StepEvent(action="ShowAnswer", args=(42,), lineno=1)]


def test_canvas_missing_method_raises_clear_error():
    class BareCanvas:
        pass

    with pytest.raises(PseudocodeError, match="not supported by this canvas"):
        run_all("PlotPixel(0, 0)\n", BareCanvas())
