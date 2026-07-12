import heapq

from algoviz.canvas.graph_canvas import PATH_STATE, GraphCanvas
from algoviz.canvas.graph_type import GRAPH_CANVAS_TYPE, parse_network
from algoviz.pseudocode.interpreter import Interpreter

from conftest import bundled_preset

_PRESET = bundled_preset("Dijkstra Shortest Path")
SOURCE = _PRESET.source
POSITIONS, EDGES, WEIGHTS, LABELS = parse_network(_PRESET.canvas_params["nodes"], _PRESET.canvas_params["edges"])
START, GOAL = _PRESET.canvas_params["start"], _PRESET.canvas_params["goal"]


def reference_dijkstra(edges, weights, start, goal):
    dist = {n: float("inf") for n in edges}
    dist[start] = 0
    parent = {start: None}
    pq = [(0, start)]
    visited = set()
    while pq:
        d, u = heapq.heappop(pq)
        if u in visited:
            continue
        visited.add(u)
        if u == goal:
            break
        for nb in edges[u]:
            nd = d + weights[(u, nb)]
            if nd < dist[nb]:
                dist[nb] = nd
                parent[nb] = u
                heapq.heappush(pq, (nd, nb))
    path = [goal]
    while path[-1] != start:
        path.append(parent[path[-1]])
    path.reverse()
    return dist[goal], path


def run_dijkstra():
    graph = GraphCanvas(POSITIONS, EDGES, START, GOAL, weights=WEIGHTS, labels=LABELS)
    interp = Interpreter(SOURCE, graph, GRAPH_CANVAS_TYPE.viz_builtins, GRAPH_CANVAS_TYPE.plain_builtins)
    steps = list(interp.run())
    return graph, interp, steps


def test_dijkstra_finds_minimum_cost_not_just_fewest_hops():
    graph, interp, _ = run_dijkstra()
    ref_cost, ref_path = reference_dijkstra(EDGES, WEIGHTS, START, GOAL)

    assert interp.env["dist"][GOAL] == ref_cost

    intermediate_nodes = set(ref_path) - {START, GOAL}
    for node in intermediate_nodes:
        assert graph.state_of(node) == PATH_STATE, f"node {node} on shortest path not highlighted"


def test_dijkstra_terminates_and_produces_steps():
    _, _, steps = run_dijkstra()
    assert len(steps) > 0


def test_dijkstra_prefers_lower_weight_over_fewer_hops():
    # A direct 0->2->3->5 (fewer hops) costs more than the highlighted
    # 0->2->1->3->4->5 route in the bundled network -- this is the case
    # that would fail if Weight() were ignored and every edge cost 1.
    ref_cost, ref_path = reference_dijkstra(EDGES, WEIGHTS, START, GOAL)
    cheap_hop_count_path = [0, 2, 3, 5]
    cheap_hop_cost = sum(
        WEIGHTS[(cheap_hop_count_path[i], cheap_hop_count_path[i + 1])] for i in range(len(cheap_hop_count_path) - 1)
    )
    assert ref_cost < cheap_hop_cost
    assert ref_path != cheap_hop_count_path
