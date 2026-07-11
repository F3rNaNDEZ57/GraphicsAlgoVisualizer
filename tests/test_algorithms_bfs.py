from collections import deque

from algoviz.algorithms.bfs_pathfinding import EDGES, GOAL, POSITIONS, SOURCE, START
from algoviz.canvas.graph_canvas import PATH_COLOR, GraphCanvas
from algoviz.pseudocode.interpreter import Interpreter


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


def test_bfs_reaches_goal_and_highlights_shortest_path():
    graph = GraphCanvas(POSITIONS, EDGES, START, GOAL)
    interp = Interpreter(SOURCE, graph)
    interp.env.update({"start": START, "goal": GOAL})
    list(interp.run())

    expected_path = reference_shortest_path(EDGES, START, GOAL)
    intermediate_nodes = set(expected_path) - {START, GOAL}

    for node in intermediate_nodes:
        assert graph.color_of(node) == PATH_COLOR, f"node {node} on shortest path not highlighted"


def test_bfs_terminates_and_produces_steps():
    graph = GraphCanvas(POSITIONS, EDGES, START, GOAL)
    interp = Interpreter(SOURCE, graph)
    interp.env.update({"start": START, "goal": GOAL})
    steps = list(interp.run())
    assert len(steps) > 0
