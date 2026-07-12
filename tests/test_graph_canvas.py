from algoviz.canvas.graph_canvas import DEFAULT_STATE, GOAL_STATE, PATH_STATE, START_STATE, VISITED_STATE, GraphCanvas


def make_graph():
    positions = {0: (0, 0), 1: (1, 0), 2: (2, 0)}
    edges = {0: [1], 1: [0, 2], 2: [1]}
    return GraphCanvas(positions, edges, start=0, goal=2)


def test_start_and_goal_states_on_construction():
    graph = make_graph()
    assert graph.state_of(0) == START_STATE
    assert graph.state_of(2) == GOAL_STATE
    assert graph.state_of(1) == DEFAULT_STATE


def test_neighbors():
    graph = make_graph()
    assert graph.neighbors(1) == [0, 2]
    assert graph.node_count() == 3


def test_get_start_and_get_goal():
    graph = make_graph()
    assert graph.get_start() == 0
    assert graph.get_goal() == 2


def test_visit_sets_state_but_not_start_or_goal():
    graph = make_graph()
    events = []
    graph.on_node(lambda n, s: events.append((n, s)))

    graph.visit(1)
    graph.visit(0)  # visiting start should be a no-op visually

    assert graph.state_of(1) == VISITED_STATE
    assert graph.state_of(0) == START_STATE
    assert events == [(1, VISITED_STATE)]


def test_highlight_marks_path():
    graph = make_graph()
    graph.highlight(1)
    assert graph.state_of(1) == PATH_STATE


def test_clear_resets_states():
    graph = make_graph()
    graph.visit(1)
    graph.clear()
    assert graph.state_of(1) == DEFAULT_STATE
    assert graph.state_of(0) == START_STATE
    assert graph.state_of(2) == GOAL_STATE


def test_weight_defaults_to_one_when_no_weights_given():
    graph = make_graph()
    assert graph.weight(0, 1) == 1.0
    assert graph.weight(1, 0) == 1.0
    assert graph.show_weights is False


def test_weight_looks_up_explicit_weights_either_direction():
    positions = {0: (0, 0), 1: (1, 0), 2: (2, 0)}
    edges = {0: [1], 1: [0, 2], 2: [1]}
    weights = {(0, 1): 4.0, (1, 0): 4.0, (1, 2): 7.0, (2, 1): 7.0}
    graph = GraphCanvas(positions, edges, start=0, goal=2, weights=weights)
    assert graph.weight(0, 1) == 4.0
    assert graph.weight(1, 0) == 4.0
    assert graph.weight(2, 1) == 7.0
    assert graph.show_weights is True


def test_labels_default_empty():
    graph = make_graph()
    assert graph.labels == {}


def test_detach_listeners_stops_further_notifications():
    graph = make_graph()
    node_events = []
    clear_events = []
    graph.on_node(lambda n, s: node_events.append((n, s)))
    graph.on_clear(lambda: clear_events.append(True))

    graph.detach_listeners()
    graph.visit(1)
    graph.clear()

    assert node_events == []
    assert clear_events == []
