import pytest

from algoviz.canvas.grid_canvas import GridCanvas


def test_plot_pixel_records_color_and_notifies_listeners():
    grid = GridCanvas(10, 10)
    seen = []
    grid.on_pixel(lambda x, y, color: seen.append((x, y, color)))

    grid.plot_pixel(3, 4)
    grid.plot_pixel(1, 1, color="blue")

    assert grid.color_at(3, 4) == "red"
    assert grid.color_at(1, 1) == "blue"
    assert seen == [(3, 4, "red"), (1, 1, "blue")]


def test_plot_pixel_out_of_bounds_raises():
    grid = GridCanvas(5, 5)
    with pytest.raises(ValueError):
        grid.plot_pixel(5, 0)
    with pytest.raises(ValueError):
        grid.plot_pixel(-1, 0)


def test_clear_resets_cells_and_notifies_listeners():
    grid = GridCanvas(5, 5)
    grid.plot_pixel(0, 0)
    cleared = []
    grid.on_clear(lambda: cleared.append(True))

    grid.clear()

    assert grid.plotted_pixels() == {}
    assert cleared == [True]


def test_color_at_defaults_to_background():
    grid = GridCanvas(5, 5, background="black")
    assert grid.color_at(2, 2) == "black"
