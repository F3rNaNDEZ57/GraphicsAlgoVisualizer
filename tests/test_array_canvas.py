from pyalgoviz.canvas.array_canvas import ArrayCanvas


def test_swap_mutates_values_and_notifies():
    array = ArrayCanvas([1, 2, 3])
    changes = []
    highlights = []
    array.on_change(lambda: changes.append(list(array.values)))
    array.on_highlight(lambda idx, kind: highlights.append((idx, kind)))

    array.swap(0, 2)

    assert array.values == [3, 2, 1]
    assert changes == [[3, 2, 1]]
    assert highlights == [([0, 2], "swap")]


def test_set_value_mutates_and_notifies():
    array = ArrayCanvas([1, 2, 3])
    array.set_value(1, 99)
    assert array.get(1) == 99


def test_compare_only_highlights_no_mutation():
    array = ArrayCanvas([1, 2, 3])
    highlights = []
    array.on_highlight(lambda idx, kind: highlights.append((idx, kind)))
    array.compare(0, 1)
    assert array.values == [1, 2, 3]
    assert highlights == [([0, 1], "compare")]


def test_length_and_get():
    array = ArrayCanvas([5, 6, 7, 8])
    assert array.length() == 4
    assert array.get(2) == 7


def test_clear_restores_initial_values():
    array = ArrayCanvas([3, 1, 2])
    array.swap(0, 1)
    assert array.values == [1, 3, 2]
    array.clear()
    assert array.values == [3, 1, 2]


def test_detach_listeners_stops_further_notifications():
    array = ArrayCanvas([1, 2, 3])
    changes = []
    highlights = []
    array.on_change(lambda: changes.append(list(array.values)))
    array.on_highlight(lambda idx, kind: highlights.append((idx, kind)))

    array.detach_listeners()
    array.swap(0, 1)

    assert changes == []
    assert highlights == []
