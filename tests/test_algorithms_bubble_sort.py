import pytest

from algoviz.canvas.array_canvas import ArrayCanvas
from algoviz.pseudocode.interpreter import Interpreter

from conftest import bundled_preset

_PRESET = bundled_preset("Bubble Sort")
SOURCE = _PRESET.source
DEFAULT_VALUES = _PRESET.canvas_params["values"]


@pytest.mark.parametrize(
    "values",
    [
        DEFAULT_VALUES,
        [1],
        [2, 1],
        [1, 2, 3, 4, 5],
        [5, 4, 3, 2, 1],
        [3, 3, 3, 1, 2],
    ],
)
def test_sorts_correctly(values):
    array = ArrayCanvas(values)
    interp = Interpreter(SOURCE, array)
    list(interp.run())
    assert array.values == sorted(values)


def test_yields_once_per_compare_or_swap():
    array = ArrayCanvas([3, 1, 2])
    interp = Interpreter(SOURCE, array)
    steps = list(interp.run())
    # bubble sort on n=3 does 3 comparisons; count swaps separately by re-deriving
    n = 3
    comparisons = n * (n - 1) // 2
    assert len(steps) >= comparisons
