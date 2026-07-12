# AlgoViz pseudocode DSL and preset format

This documents what you can actually write, for two audiences: someone
adding a new algorithm to an existing canvas type (grid/array/graph), and
someone adding a whole new canvas type as a plugin.

## The pseudocode language

Pseudocode is a **restricted Python subset**, parsed with `ast.parse` and
walked by a hand-written interpreter (not `exec`) — see
`src/algoviz/pseudocode/interpreter.py`. That means familiar Python syntax
and semantics for the parts that exist, and a clear error for the parts
that don't.

### Supported

- Assignment: `x = 5`, augmented assignment: `x += 1`, `x *= 2`
- `if` / `elif` / `else`
- `while` loops
- `for x in range(...):` and `for x in <any list-valued expression>:`
  (including a builtin call that returns a list, e.g. `for nb in
  Neighbors(node):`)
- Arithmetic: `+ - * / // % **`, unary `-`/`+`
- Comparisons: `== != < <= > >=`, chained (`0 <= i < n`)
- Boolean `and` / `or` / `not` — these **short-circuit** like real Python
  (`i < len(arr) and arr[i] > 0` will not evaluate `arr[i]` once `i <
  len(arr)` is false)
- Lists: literals (`[1, 2, 3]`), indexing (`arr[i]`), indexed assignment
  (`arr[i] = 5`), and list repetition (`[0] * n`)
- Calling a whitelisted builtin function (see below)

### Not supported

- **No `break` / `continue`.** Use a flag variable instead:
  ```
  done = 0
  while done == 0:
      ...
      if some_condition:
          done = 1
  ```
  This is a real limitation, not an oversight — see the "why no functions
  or break" note below.
- **No function definitions** (`def`), no recursion. Every built-in
  algorithm is written iteratively for this reason (see
  `bresenham-line.toml`'s `done` flag, or `bfs-pathfinding.toml`'s
  array-backed queue instead of recursive traversal).
- No imports, no classes, no attribute access (`x.y`), no method calls
  (`arr.append(...)` — use builtins or list literals/repetition instead)
- No tuples, dicts, sets, f-strings, comprehensions
- `for` loop targets must be a single variable name (no tuple unpacking)

### Why these limits

The DSL is a restricted Python subset specifically so parsing is free
(`ast.parse` does it) and so the interpreter can be a small, fully-tested,
generator-based tree-walker instead of a general-purpose language runtime.
`break`/`continue`/functions are the main things that don't fit that
tradeoff cleanly yet — they're not planned unless a real algorithm turns
out to need them badly enough to justify the interpreter work.

### Builtins

Two kinds:

- **Viz builtins** — perform a visualization action and mark a step
  boundary. The interpreter yields once per call, which is what makes
  Play/Pause/Step work. Example: `PlotPixel(x, y)`, `Swap(i, j)`.
- **Plain builtins** — read-only, usable inside expressions, never yield.
  Example: `Value(i)`, `Length()`, `round(x)`.

Which names exist depends on the **canvas type** the preset mounts — see
`src/algoviz/canvas/registry.py`'s `CanvasType.viz_builtins` /
`plain_builtins`. The three built-in canvas types:

| Canvas | Viz builtins | Plain builtins |
|---|---|---|
| `grid` | `PlotPixel(x, y, color=None)` | — |
| `array` | `Swap(i, j)`, `SetValue(i, val)`, `Compare(i, j)` | `Value(i)`, `Length()` |
| `graph` | `Visit(node)`, `Highlight(node, state=None)` | `Neighbors(node)`, `NodeCount()`, `Start()`, `Goal()`, `Weight(a, b)` |

Plus five always-available plain builtins regardless of canvas type:
`round`, `abs`, `len`, `int`, `range`.

Calling a name that isn't registered for the active canvas type raises a
`PseudocodeError` naming what's missing, before anything runs.

## Preset file format (TOML)

An algorithm is one `.toml` file. Bundled ones live in
`src/algoviz/presets/`; drop your own into `~/.algoviz/presets/` and they
show up in the picker next time you launch — no reinstall, no Python.

```toml
[preset]
name = "My Algorithm"        # shown in the picker
canvas = "array"             # which canvas type to mount
description = "..."          # optional, shown as a tooltip/log line
source = '''
...your pseudocode here...
'''

[canvas]                     # params passed to the canvas type's factory
values = [8, 3, 9, 1, 6, 4, 7, 2, 5]

[inputs.k]                   # zero or more; each generates one input widget
type = "int"                 # "int" | "float" | "str" | "color" | "int_list" | "str_list"
default = 3
min = 0                      # optional
max = 10                     # optional
label = "K"                  # optional, defaults to the key name
```

Two TOML gotchas worth knowing if you hand-write one:

- **`source` must live inside `[preset]`** (or appear before any `[table]`
  header in the file). A bare key written *after* `[canvas]` or
  `[inputs.x]` belongs to that table in TOML's grammar, not to the
  document root — it'll silently end up nested somewhere you didn't
  intend instead of raising an error.
- Use `'''...'''` (a TOML *literal* multi-line string) for `source`, not
  `"""..."""` — the literal form doesn't process escape sequences, so your
  pseudocode's `\` and quotes pass through untouched.

A malformed preset file is skipped and logged as a warning — it never
crashes the app or the picker.

### Example: grid canvas with input fields

See `src/algoviz/presets/bresenham-line.toml` for a full example with
four `[inputs.*]` entries (`xl`, `yl`, `xr`, `yr`) that generate the
labeled fields above the canvas.

### Example: graph canvas maze format

`graph` canvases take a `[canvas] maze = [...]` — a list of equal-length
strings using `S` (start), `G` (goal), `#` (wall), `.` (open). See
`src/algoviz/presets/bfs-pathfinding.toml`. Every maze edge costs `1` via
`Weight()`'s default, so BFS-style algorithms can ignore weights entirely.

### Example: graph canvas custom weighted network format

For an arbitrary network (not a grid maze) — the shape Dijkstra/A*/Prim's/
Kruskal's need — a `graph` canvas can instead take explicit `nodes`/`edges`:

```toml
[canvas]
start = 0
goal = 2
nodes = [
  {id = 0, x = 80, y = 200, label = "A"},   # label is optional
  {id = 1, x = 220, y = 80, label = "B"},
  {id = 2, x = 380, y = 200, label = "C"},
]
edges = [
  {from = 0, to = 1, weight = 4},           # weight defaults to 1 if omitted
  {from = 1, to = 2, weight = 7},
]
```

`x`/`y` are pixel coordinates (not grid cells) — place nodes wherever reads
best for your layout. Edges are undirected: `weight` applies to `Weight(a,
b)` regardless of query direction. A graph built this way renders weight
labels on its edges; a maze-built graph doesn't (weights are all `1` and
would just be visual noise). See `src/algoviz/presets/dijkstra-shortest-path.toml`
for a complete example, including the array-backed O(V²) Dijkstra pseudocode
(no heap builtin needed — a linear scan for the minimum unvisited distance
is enough for a presentation-sized network).

This is also the format the in-app graph editor writes when you save a
hand-built network as a preset.

## Writing a plugin canvas type

If no built-in canvas type fits (you need a new *shape* of visualization,
not just a new algorithm), you can ship your own — as a real pip package
or as a drop-in script. Either way, algoviz core needs zero edits.

### What you're building

A `CanvasType` (`src/algoviz/canvas/registry.py`) bundles:

- `id` — the string a preset's `canvas = "..."` references
- `make_canvas(params) -> VizCanvas` — builds your model from a preset's
  `[canvas]` table
- `viz_builtins` / `plain_builtins` — `{DSL name: your canvas's method
  name}`, resolved via `getattr` at call time — this is what lets you add
  a verb like `SetChild` without touching `pseudocode/builtins_registry.py`
  at all
- `renderers` — `{"tk": YourRenderer}`, keeping your renderer import out
  of algoviz's own preset/registry code

The canvas *model* should stay GUI-free (no `tkinter` import) so it can be
unit tested headlessly; put the `tkinter` import only in the renderer.

### Option A: a pip-installable plugin (recommended)

Publish a `CanvasType` instance via the `algoviz.canvases` entry point
group:

```toml
# your plugin's pyproject.toml
[project.entry-points."algoviz.canvases"]
heap = "algoviz_heap_canvas:HEAP_CANVAS_TYPE"
```

algoviz discovers and registers every such entry point at startup
(`src/algoviz/plugins.py`'s `load_entry_point_plugins()`). See
`plugins/algoviz-heap-canvas/` in this repo for a complete, working
example — a binary min-heap canvas (tree-shaped rendering, `Parent`/
`LeftChild`/`RightChild` builtins) that lives entirely outside the
`algoviz` package and was installed with a plain `pip install -e .`, no
core edits.

### Option B: a drop-in script

Put a `.py` file in `~/.algoviz/plugins/` exposing a module-level
`CANVAS_TYPE`:

```python
# ~/.algoviz/plugins/my_canvas.py
from algoviz.canvas.registry import CanvasType, ParamSpec

CANVAS_TYPE = CanvasType(
    id="my_canvas",
    canvas_params=[...],
    make_canvas=lambda params: ...,
    viz_builtins={...},
    plain_builtins={...},
    renderers={"tk": MyRenderer},
)
```

This is a power-user door: it executes arbitrary local Python at startup,
same trust level as installing a package. A broken drop-in script is
logged as a warning and skipped, never crashes the app.

### If a plugin goes missing

A preset whose `canvas` id isn't registered (plugin uninstalled, typo) is
skipped from the picker with a logged warning, not a crash.
