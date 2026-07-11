from algoviz.canvas.graph_canvas import DEFAULT_COLOR, GOAL_COLOR, PATH_COLOR, START_COLOR, VISITED_COLOR, GraphCanvas


def make_graph():
    positions = {0: (0, 0), 1: (1, 0), 2: (2, 0)}
    edges = {0: [1], 1: [0, 2], 2: [1]}
    return GraphCanvas(positions, edges, start=0, goal=2)


def test_start_and_goal_colored_on_construction():
    graph = make_graph()
    assert graph.color_of(0) == START_COLOR
    assert graph.color_of(2) == GOAL_COLOR
    assert graph.color_of(1) == DEFAULT_COLOR


def test_neighbors():
    graph = make_graph()
    assert graph.neighbors(1) == [0, 2]
    assert graph.node_count() == 3


def test_get_start_and_get_goal():
    graph = make_graph()
    assert graph.get_start() == 0
    assert graph.get_goal() == 2


def test_visit_colors_node_but_not_start_or_goal():
    graph = make_graph()
    events = []
    graph.on_node(lambda n, c: events.append((n, c)))

    graph.visit(1)
    graph.visit(0)  # visiting start should be a no-op visually

    assert graph.color_of(1) == VISITED_COLOR
    assert graph.color_of(0) == START_COLOR
    assert events == [(1, VISITED_COLOR)]


def test_highlight_marks_path():
    graph = make_graph()
    graph.highlight(1)
    assert graph.color_of(1) == PATH_COLOR


def test_clear_resets_colors():
    graph = make_graph()
    graph.visit(1)
    graph.clear()
    assert graph.color_of(1) == DEFAULT_COLOR
    assert graph.color_of(0) == START_COLOR
    assert graph.color_of(2) == GOAL_COLOR
