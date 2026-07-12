import pytest

from algoviz.canvas.graph_type import parse_network
from algoviz.preset_loader import load_preset_file, write_preset_file
from algoviz.ui.graph_editor_model import GraphEditorModel


def test_add_node_assigns_incrementing_ids():
    model = GraphEditorModel()
    a = model.add_node(10, 20, label="A")
    b = model.add_node(30, 40)
    assert a == 0
    assert b == 1
    assert model.nodes[a].x == 10 and model.nodes[a].y == 20 and model.nodes[a].label == "A"
    assert model.nodes[b].label == ""


def test_connect_and_disconnect():
    model = GraphEditorModel()
    a, b = model.add_node(0, 0), model.add_node(10, 0)
    model.connect(a, b, weight=5)
    assert model.edge_between(a, b).weight == 5
    assert model.edge_between(b, a) is model.edge_between(a, b)  # order-independent lookup

    model.disconnect(b, a)  # reversed order still removes it
    assert model.edge_between(a, b) is None


def test_connect_replaces_existing_edge_weight():
    model = GraphEditorModel()
    a, b = model.add_node(0, 0), model.add_node(10, 0)
    model.connect(a, b, weight=5)
    model.connect(a, b, weight=9)
    assert len(model.edges) == 1
    assert model.edge_between(a, b).weight == 9


def test_connect_rejects_self_loop_and_unknown_node():
    model = GraphEditorModel()
    a = model.add_node(0, 0)
    with pytest.raises(ValueError, match="itself"):
        model.connect(a, a)
    with pytest.raises(ValueError, match="unknown"):
        model.connect(a, 999)


def test_remove_node_cascades_to_incident_edges_and_clears_start_goal():
    model = GraphEditorModel()
    a, b, c = model.add_node(0, 0), model.add_node(10, 0), model.add_node(20, 0)
    model.connect(a, b)
    model.connect(b, c)
    model.set_start(a)
    model.set_goal(c)

    model.remove_node(b)

    assert b not in model.nodes
    assert model.edges == []
    assert model.start == a
    assert model.goal == c

    model.remove_node(a)
    assert model.start is None


def test_set_start_and_goal_reject_unknown_node():
    model = GraphEditorModel()
    with pytest.raises(ValueError):
        model.set_start(42)


def test_node_near_hit_test():
    model = GraphEditorModel()
    a = model.add_node(100, 100)
    assert model.node_near(105, 100) == a  # within default radius
    assert model.node_near(500, 500) is None


def test_edge_near_hit_test():
    model = GraphEditorModel()
    a, b = model.add_node(0, 0), model.add_node(100, 0)
    model.connect(a, b)
    hit = model.edge_near(50, 2)  # near the midpoint
    assert hit is not None and hit.a == a and hit.b == b
    assert model.edge_near(500, 500) is None


def test_validate_reports_missing_requirements():
    model = GraphEditorModel()
    ok, reason = model.validate()
    assert not ok and "2 nodes" in reason

    a, b = model.add_node(0, 0), model.add_node(10, 0)
    ok, reason = model.validate()
    assert not ok and "edge" in reason

    model.connect(a, b)
    ok, reason = model.validate()
    assert not ok and "start" in reason

    model.set_start(a)
    model.set_goal(a)
    ok, reason = model.validate()
    assert not ok and "different" in reason

    model.set_goal(b)
    ok, reason = model.validate()
    assert ok and reason == ""


def test_to_preset_raises_when_invalid():
    model = GraphEditorModel()
    with pytest.raises(ValueError, match="cannot save network"):
        model.to_preset("Broken")


def test_to_preset_roundtrips_through_graph_canvas_network_format():
    model = GraphEditorModel()
    a = model.add_node(80, 200, label="A")
    b = model.add_node(220, 80, label="B")
    c = model.add_node(380, 200)
    model.connect(a, b, weight=4)
    model.connect(b, c, weight=7)
    model.set_start(a)
    model.set_goal(c)

    preset = model.to_preset("My Network", description="hand-built")

    assert preset.canvas_type_id == "graph"
    assert preset.canvas_params["start"] == a
    assert preset.canvas_params["goal"] == c
    assert "Weight" in preset.source and "NodeCount" in preset.source

    positions, adjacency, weights, labels = parse_network(
        preset.canvas_params["nodes"], preset.canvas_params["edges"]
    )
    assert positions[a] == (80, 200)
    assert weights[(a, b)] == 4.0
    assert weights[(b, c)] == 7.0
    assert labels == {a: "A", b: "B"}


def test_to_preset_saved_file_reloads_with_same_shape(tmp_path):
    model = GraphEditorModel()
    a, b = model.add_node(0, 0), model.add_node(100, 0)
    model.connect(a, b, weight=3)
    model.set_start(a)
    model.set_goal(b)

    preset = model.to_preset("Saved Network")
    path = write_preset_file(preset, directory=tmp_path)
    reloaded = load_preset_file(path)

    assert reloaded.canvas_params == preset.canvas_params
    assert reloaded.canvas_type_id == "graph"
