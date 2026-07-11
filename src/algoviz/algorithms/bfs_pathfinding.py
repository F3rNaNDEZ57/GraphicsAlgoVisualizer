NAME = "BFS Pathfinding"

GRID_W, GRID_H = 8, 6
WALLS = {(3, 1), (3, 2), (3, 3), (3, 4), (5, 0), (5, 1), (5, 2), (5, 4), (5, 5)}


def _build_grid_graph():
    positions: dict[int, tuple[int, int]] = {}
    node_id: dict[tuple[int, int], int] = {}
    next_id = 0
    for y in range(GRID_H):
        for x in range(GRID_W):
            if (x, y) in WALLS:
                continue
            node_id[(x, y)] = next_id
            positions[next_id] = (x, y)
            next_id += 1

    edges: dict[int, list[int]] = {n: [] for n in positions}
    for (x, y), n in node_id.items():
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            neighbor = (x + dx, y + dy)
            if neighbor in node_id:
                edges[n].append(node_id[neighbor])

    start = node_id[(0, 0)]
    goal = node_id[(GRID_W - 1, GRID_H - 1)]
    return positions, edges, start, goal


POSITIONS, EDGES, START, GOAL = _build_grid_graph()

# Kept as strings so pseudocode env can be seeded uniformly with int(entry.get()).
DEFAULT_INPUTS = {"start": START, "goal": GOAL}

SOURCE = """\
n = NodeCount()
visited = [0] * n
parent = [-1] * n
queue = [0] * n
head = 0
tail = 0
queue[tail] = start
tail = tail + 1
visited[start] = 1
found = 0
while head < tail and found == 0:
    current = queue[head]
    head = head + 1
    Visit(current)
    if current == goal:
        found = 1
    else:
        for nb in Neighbors(current):
            if visited[nb] == 0:
                visited[nb] = 1
                parent[nb] = current
                queue[tail] = nb
                tail = tail + 1

if found == 1:
    node = goal
    while node != start:
        Highlight(node)
        node = parent[node]
"""
