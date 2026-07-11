import pytest

from algoviz.canvas.grid_canvas import GridCanvas
from algoviz.pseudocode.interpreter import Interpreter

from conftest import bundled_preset

SOURCE = bundled_preset("Bresenham Line").source


def reference_bresenham(xl, yl, xr, yr):
    """Independent Bresenham implementation to check the pseudocode against."""
    dx = abs(xr - xl)
    dy = -abs(yr - yl)
    sx = 1 if xl < xr else -1
    sy = 1 if yl < yr else -1
    err = dx + dy
    x, y = xl, yl
    pixels = []
    while True:
        pixels.append((x, y))
        if x == xr and y == yr:
            break
        e2 = 2 * err
        if e2 >= dy and x != xr:
            err += dy
            x += sx
        if e2 <= dx and y != yr:
            err += dx
            y += sy
    return pixels


def run_line(xl, yl, xr, yr, size=64):
    grid = GridCanvas(size, size, background="black")
    interp = Interpreter(SOURCE, grid)
    interp.env.update({"xl": xl, "yl": yl, "xr": xr, "yr": yr})
    list(interp.run())
    return grid


@pytest.mark.parametrize(
    "xl, yl, xr, yr",
    [
        (2, 2, 24, 11),  # shallow positive slope
        (2, 2, 2, 20),  # vertical
        (2, 2, 30, 2),  # horizontal
        (2, 2, 10, 10),  # 45 degrees
        (24, 11, 2, 2),  # reversed direction
        (10, 20, 2, 2),  # steep negative slope
        (5, 5, 5, 5),  # single point
    ],
)
def test_matches_reference_bresenham(xl, yl, xr, yr):
    grid = run_line(xl, yl, xr, yr)
    expected = set(reference_bresenham(xl, yl, xr, yr))
    assert set(grid.plotted_pixels().keys()) == expected


def test_plots_step_count_equals_pixel_count():
    grid = GridCanvas(64, 64)
    interp = Interpreter(SOURCE, grid)
    interp.env.update({"xl": 2, "yl": 2, "xr": 24, "yr": 11})
    steps = list(interp.run())
    assert len(steps) == len(grid.plotted_pixels())
