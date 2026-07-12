from collections import deque

from pyalgoviz.canvas.graph_canvas import PATH_STATE, GraphCanvas
from pyalgoviz.canvas.graph_type import GRAPH_CANVAS_TYPE, parse_maze
from pyalgoviz.pseudocode.interpreter import Interpreter
from pyalgoviz.pseudocode.step_event import StepEvent

from conftest import bundled_preset

_PRESET = bundled_preset("BFS Pathfinding")
SOURCE = _PRESET.source
POSITIONS, EDGES, START, GOAL = parse_maze(_PRESET.canvas_params["maze"])


def reference_shortest_path(edges, start, goal):
    parent = {start: None}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        if node == goal:
            break
        for nb in edges[node]:
            if nb not in parent:
                parent[nb] = node
                queue.append(nb)
    path = [goal]
    while path[-1] != start:
        path.append(parent[path[-1]])
    path.reverse()
    return path


def run_bfs():
    graph = GraphCanvas(POSITIONS, EDGES, START, GOAL)
    interp = Interpreter(SOURCE, graph, GRAPH_CANVAS_TYPE.viz_builtins, GRAPH_CANVAS_TYPE.plain_builtins)
    steps = list(interp.run())
    return graph, steps


def test_bfs_reaches_goal_and_highlights_shortest_path():
    graph, _ = run_bfs()

    expected_path = reference_shortest_path(EDGES, START, GOAL)
    intermediate_nodes = set(expected_path) - {START, GOAL}

    for node in intermediate_nodes:
        assert graph.state_of(node) == PATH_STATE, f"node {node} on shortest path not highlighted"


def test_bfs_terminates_and_produces_steps():
    _, steps = run_bfs()
    assert len(steps) > 0


def test_bfs_shows_the_answer():
    _, steps = run_bfs()
    expected_hops = len(reference_shortest_path(EDGES, START, GOAL)) - 1
    answer_steps = [s for s in steps if s.action == "ShowAnswer"]
    assert answer_steps == [
        StepEvent(action="ShowAnswer", args=("Path length (hops)", expected_hops), lineno=answer_steps[0].lineno)
    ]
