"""Pure state machine behind the in-app graph editor. Every mutation a
user's click/drag eventually triggers goes through one of these methods, and
nothing here imports tkinter -- so the whole editor is unit-testable without
a display, the same way GraphCanvas is. GraphEditorView (Tk) is a thin
wrapper: it turns canvas mouse events into calls here and redraws from
current state, but owns no state-mutation logic of its own.
"""

from __future__ import annotations

from dataclasses import dataclass

from pyalgoviz.preset_loader import LoadedPreset

# Fallback only -- used if the bundled Dijkstra preset can't be loaded for
# some reason. The real starting point is _default_network_source() below,
# which reads presets/dijkstra-shortest-path.toml directly so the two never
# drift out of sync (e.g. if that preset gains a ShowAnswer() call, every
# network the editor saves gets it too, with no second copy to remember).
_FALLBACK_NETWORK_SOURCE = """n = NodeCount()
dist = [999999] * n
visited = [0] * n
parent = [-1] * n
dist[Start()] = 0
done = 0
while done == 0:
    u = -1
    best = 999999
    k = 0
    while k < n:
        if visited[k] == 0 and dist[k] < best:
            best = dist[k]
            u = k
        k = k + 1
    if u == -1:
        done = 1
    else:
        visited[u] = 1
        Visit(u)
        if u == Goal():
            done = 1
        else:
            for nb in Neighbors(u):
                if visited[nb] == 0:
                    w = Weight(u, nb)
                    new_dist = dist[u] + w
                    if new_dist < dist[nb]:
                        dist[nb] = new_dist
                        parent[nb] = u

if visited[Goal()] == 1:
    node = Goal()
    while node != Start():
        Highlight(node)
        node = parent[node]
    ShowAnswer("Shortest path cost", dist[Goal()])
else:
    ShowAnswer("No path found")
"""


def _default_network_source() -> str:
    try:
        from pyalgoviz.preset_loader import BUNDLED_PRESETS_DIR, load_preset_file

        return load_preset_file(BUNDLED_PRESETS_DIR / "dijkstra-shortest-path.toml").source
    except Exception:
        return _FALLBACK_NETWORK_SOURCE


@dataclass
class EditorNode:
    id: int
    x: float
    y: float
    label: str = ""


@dataclass
class EditorEdge:
    a: int
    b: int
    weight: float = 1.0


class GraphEditorModel:
    def __init__(self) -> None:
        self.nodes: dict[int, EditorNode] = {}
        self.edges: list[EditorEdge] = []
        self.start: int | None = None
        self.goal: int | None = None
        self._next_id = 0

    def add_node(self, x: float, y: float, label: str = "") -> int:
        node_id = self._next_id
        self._next_id += 1
        self.nodes[node_id] = EditorNode(node_id, x, y, label)
        return node_id

    def remove_node(self, node_id: int) -> None:
        if node_id not in self.nodes:
            return
        del self.nodes[node_id]
        self.edges = [e for e in self.edges if node_id not in (e.a, e.b)]
        if self.start == node_id:
            self.start = None
        if self.goal == node_id:
            self.goal = None

    def connect(self, a: int, b: int, weight: float = 1.0) -> None:
        if a == b:
            raise ValueError("cannot connect a node to itself")
        if a not in self.nodes or b not in self.nodes:
            raise ValueError(f"unknown node id ({a} or {b})")
        self.disconnect(a, b)
        self.edges.append(EditorEdge(a, b, weight))

    def disconnect(self, a: int, b: int) -> None:
        self.edges = [e for e in self.edges if {e.a, e.b} != {a, b}]

    def edge_between(self, a: int, b: int) -> EditorEdge | None:
        for e in self.edges:
            if {e.a, e.b} == {a, b}:
                return e
        return None

    def set_start(self, node_id: int) -> None:
        if node_id not in self.nodes:
            raise ValueError(f"unknown node {node_id}")
        self.start = node_id

    def set_goal(self, node_id: int) -> None:
        if node_id not in self.nodes:
            raise ValueError(f"unknown node {node_id}")
        self.goal = node_id

    def rename_node(self, node_id: int, label: str) -> None:
        if node_id not in self.nodes:
            raise ValueError(f"unknown node {node_id}")
        self.nodes[node_id].label = label

    def load_network(self, nodes: list[dict], edges: list[dict], start: int | None, goal: int | None) -> None:
        """Hydrates this model from an existing network preset's
        canvas_params -- the nodes/edges/start/goal shape graph_type.py's
        parse_network reads, i.e. exactly what to_preset() below produces.
        Used to re-open a previously saved network for further editing
        (renaming a node, adding an edge, moving start/goal) instead of
        only ever being able to build one from scratch."""
        self.nodes = {}
        self.edges = []
        for n in nodes:
            node_id = int(n["id"])
            self.nodes[node_id] = EditorNode(node_id, n["x"], n["y"], n.get("label", ""))
        for e in edges:
            self.edges.append(EditorEdge(int(e["from"]), int(e["to"]), float(e.get("weight", 1))))
        self.start = int(start) if start is not None else None
        self.goal = int(goal) if goal is not None else None
        # Must continue from the highest existing id, or the next add_node()
        # collides with an id already in use and corrupts the graph.
        self._next_id = (max(self.nodes) + 1) if self.nodes else 0

    @classmethod
    def from_preset(cls, preset: LoadedPreset) -> "GraphEditorModel":
        model = cls()
        model.load_network(
            preset.canvas_params.get("nodes", []),
            preset.canvas_params.get("edges", []),
            preset.canvas_params.get("start"),
            preset.canvas_params.get("goal"),
        )
        return model

    def node_near(self, x: float, y: float, radius: float = 18) -> int | None:
        """Hit-test used by click handling: id of the nearest node within
        `radius`, or None if empty space was clicked."""
        best: int | None = None
        best_dist = radius
        for node in self.nodes.values():
            dist = ((node.x - x) ** 2 + (node.y - y) ** 2) ** 0.5
            if dist <= best_dist:
                best = node.id
                best_dist = dist
        return best

    def edge_near(self, x: float, y: float, radius: float = 10) -> EditorEdge | None:
        """Hit-test used by edge deletion: the edge whose midpoint is
        nearest `(x, y)` within `radius`, or None."""
        best: EditorEdge | None = None
        best_dist = radius
        for e in self.edges:
            na, nb = self.nodes[e.a], self.nodes[e.b]
            mx, my = (na.x + nb.x) / 2, (na.y + nb.y) / 2
            dist = ((mx - x) ** 2 + (my - y) ** 2) ** 0.5
            if dist <= best_dist:
                best = e
                best_dist = dist
        return best

    def validate(self) -> tuple[bool, str]:
        if len(self.nodes) < 2:
            return False, "need at least 2 nodes"
        if not self.edges:
            return False, "need at least 1 edge"
        if self.start is None or self.goal is None:
            return False, "must mark both a start and a goal node"
        if self.start == self.goal:
            return False, "start and goal must be different nodes"
        return True, ""

    def to_preset(self, name: str, description: str = "") -> LoadedPreset:
        ok, reason = self.validate()
        if not ok:
            raise ValueError(f"cannot save network: {reason}")

        nodes_param = [
            {"id": n.id, "x": n.x, "y": n.y, **({"label": n.label} if n.label else {})}
            for n in self.nodes.values()
        ]
        edges_param = [{"from": e.a, "to": e.b, "weight": e.weight} for e in self.edges]

        return LoadedPreset(
            name=name,
            canvas_type_id="graph",
            description=description,
            canvas_params={
                "start": self.start,
                "goal": self.goal,
                "nodes": nodes_param,
                "edges": edges_param,
            },
            source=_default_network_source(),
        )
