from algoviz.canvas.graph_type import GRAPH_CANVAS_TYPE, parse_maze, parse_network

SIMPLE_MAZE = ["S.", ".G"]


def test_parse_maze_positions_are_pixel_space_and_centered():
    positions, edges, start, goal = parse_maze(SIMPLE_MAZE, cell_size=60)
    assert positions[start] == (30, 30)  # cell (0,0) -> centered pixel coords
    assert positions[goal] == (90, 90)  # cell (1,1)


def test_parse_maze_default_cell_size_matches_module_default():
    positions, _, start, _ = parse_maze(SIMPLE_MAZE)
    assert positions[start] == (30, 30)


def test_parse_network_builds_undirected_adjacency_and_symmetric_weights():
    nodes = [
        {"id": 0, "x": 0, "y": 0, "label": "A"},
        {"id": 1, "x": 100, "y": 0, "label": "B"},
        {"id": 2, "x": 200, "y": 0},
    ]
    edges = [{"from": 0, "to": 1, "weight": 4}, {"from": 1, "to": 2, "weight": 7}]

    positions, adjacency, weights, labels = parse_network(nodes, edges)

    assert positions == {0: (0, 0), 1: (100, 0), 2: (200, 0)}
    assert adjacency[0] == [1]
    assert adjacency[1] == [0, 2]
    assert adjacency[2] == [1]
    assert weights[(0, 1)] == 4.0
    assert weights[(1, 0)] == 4.0
    assert weights[(1, 2)] == 7.0
    assert labels == {0: "A", 1: "B"}


def test_parse_network_edge_weight_defaults_to_one():
    nodes = [{"id": 0, "x": 0, "y": 0}, {"id": 1, "x": 10, "y": 0}]
    edges = [{"from": 0, "to": 1}]
    _, _, weights, _ = parse_network(nodes, edges)
    assert weights[(0, 1)] == 1.0


def test_make_canvas_network_format_builds_weighted_graph_with_show_weights():
    params = {
        "start": 0,
        "goal": 2,
        "nodes": [{"id": 0, "x": 0, "y": 0}, {"id": 1, "x": 50, "y": 0}, {"id": 2, "x": 100, "y": 0}],
        "edges": [{"from": 0, "to": 1, "weight": 3}, {"from": 1, "to": 2, "weight": 5}],
    }
    graph = GRAPH_CANVAS_TYPE.make_canvas(params)
    assert graph.get_start() == 0
    assert graph.get_goal() == 2
    assert graph.weight(0, 1) == 3.0
    assert graph.show_weights is True


def test_make_canvas_maze_format_still_works():
    graph = GRAPH_CANVAS_TYPE.make_canvas({"maze": SIMPLE_MAZE})
    assert graph.node_count() == 4
    assert graph.show_weights is False
