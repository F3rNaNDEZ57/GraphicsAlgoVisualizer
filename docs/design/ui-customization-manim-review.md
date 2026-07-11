# AlgoViz — UI/UX, Customization, and Manim Feasibility Review

*Design analysis, 2026-07-12. Companion to the original build plan
(`~/.claude/plans/generic-scribbling-salamander.md`). No code changes were
made as part of this review; all 53 tests pass on `main` (8157cf3).*

---

## Executive Summary

**1. UI/UX — reskin with CustomTkinter, don't replatform.** The GUI-agnostic
layering claimed in the plan doc genuinely holds: `pseudocode/`, `engine/`,
and the three canvas models are tkinter-free, and only ~320 lines
(`ui/main_window.py` plus the three `tk_*_renderer.py` files) touch Tk.
That makes the cheapest option also the best one right now: keep the Tk
widget tree, swap the shell widgets for CustomTkinter equivalents, and do a
deliberate visual-polish pass on the three renderers (padding, rounded
bars, anti-aliased-looking colors, a shared theme token set). PySide6 is the
right *second* platform if the project outgrows Tk (syntax-highlighted
editor, GPU canvas), and the architecture already supports it via the
structural `Scheduler` protocol in `engine/runner.py` — but it is a
~200 MB dependency for a visual delta most of which CustomTkinter + renderer
polish already delivers. A web frontend is the most powerful and the most
disruptive option; not recommended at this stage.

**2. Customization — TOML preset files + per-canvas parameter schemas +
entry-point plugins.** Today every axis of customization requires editing
Python source: algorithms are modules hand-registered in `ui/presets.py`,
input fields are a hardcoded `["xl","yl","xr","yr"]` list coerced with a
blanket `int()`, bubble sort's array and BFS's maze are module constants,
and the builtin whitelist is a global dict in
`pseudocode/builtins_registry.py`. The proposal: (a) a TOML preset file
format (multi-line literal strings hold pseudocode cleanly) loadable from
both bundled package data and a user directory, (b) a declarative parameter
schema per canvas type so input widgets generate themselves, (c) "Save
preset…" in the UI writing that same format, and (d) a `CanvasPlugin`
registration object + `algoviz.canvases` entry point so a fourth canvas
type (tree/heap) ships without touching core source. Two internal refactors
unblock this: split the preset registry from renderer binding (presets.py
currently imports Tk renderer classes), and make the builtin name→method
maps per-canvas-type instead of global.

**3. Manim — do not adopt for the live surface (infeasible); defer the
export feature (feasible but poor near-term value).** Manim is
architecturally a batch compiler: a `Scene.construct()` defines the whole
animation, then ffmpeg/pyav renders it. Neither Manim CE's OpenGL
interactive mode nor ManimGL's `self.embed()` offers an embeddable widget
or an API for injecting external live state mid-scene — they are IPython
authoring REPLs. So Manim cannot replace the Tk canvas for Play/Pause/Step.
The middle path (record the step-event stream, replay it into a generated
Scene, render a polished MP4) is technically clean — but the honest verdict
is **not now**: for grids, bars, and circles, Manim's marquee strengths
(smooth transforms, LaTeX math, camera moves) go mostly unused, while its
install footprint is large. Recommendation: build the cheap prerequisite (a
structured step-event log, which the UI wants anyway for line highlighting),
ship GIF/MP4 export via Pillow/imageio first if users ask for export at
all, and keep Manim as a possible future opt-in extra.

---

## Current State Assessment

### Architecture (verified against source, not the plan doc)

The layering promised in the plan doc is real and clean:

| Layer | Files | GUI dependency |
|---|---|---|
| DSL interpreter | `src/algoviz/pseudocode/interpreter.py` (269 lines), `builtins_registry.py`, `errors.py` | none |
| Step engine | `src/algoviz/engine/runner.py`, `playback.py` | none — `Runner` depends on a structural `Scheduler` protocol (`after`/`after_cancel`), not on tkinter |
| Canvas models | `src/algoviz/canvas/grid_canvas.py`, `array_canvas.py`, `graph_canvas.py`, `base.py` | none — renderers subscribe via listener callbacks (`on_pixel`, `on_change`, `on_node`, …) |
| Renderers | `src/algoviz/canvas/tk_grid_renderer.py` (39 ln), `tk_array_renderer.py` (54 ln), `tk_graph_renderer.py` (65 ln) | tkinter |
| Shell | `src/algoviz/ui/main_window.py` (157 ln), `ui/presets.py`, `app.py` | tkinter (presets.py indirectly — see below) |

Key mechanics that any redesign must preserve:

- **Generator stepping.** `Interpreter.run()` yields once per visualization
  builtin call (`interpreter.py:163-170`); `Runner._advance_once()` calls
  `next()` on it, scheduled via `scheduler.after(delay_ms, …)`
  (`runner.py:55-76`). Play/Pause/Step are just schedule/cancel/advance.
  Any UI that has a timer-on-the-event-loop primitive can host this.
- **Listener-based rendering.** Canvas models broadcast semantic events;
  renderers translate them to Tk canvas items. A new frontend only needs
  new listener implementations.
- **Zero runtime dependencies.** `pyproject.toml` declares
  `dependencies = []`, Python ≥3.10, one console script. This is a genuine
  distribution asset; every option below is scored partly on what it costs.
- **Tests are headless.** 53 tests, all green, none import tkinter
  (`tests/conftest.py` uses a `RecordingCanvas` double). The UI layer has
  no automated coverage, which cuts both ways: a UI rewrite regresses
  nothing tested, and nothing catches UI regressions.

### What's hardcoded (the customization inventory)

1. **Preset registration** — `ui/presets.py:43-65` is a hand-written dict
   of three `AlgorithmPreset` entries. Adding a fourth algorithm means
   editing this file plus adding a module under `src/algoviz/algorithms/`.
2. **Renderer coupling inside the preset layer** — each preset's `build()`
   returns `(canvas, renderer_class)` and `presets.py` imports all three
   `Tk*Renderer` classes (`presets.py:16-18`). The preset registry is
   therefore *not* GUI-free even though everything it describes (name,
   source, env, input fields) is. This is the one place the "only
   `tk_*_renderer.py` imports tkinter" rule is bent in spirit, and it's the
   first thing to fix for both the UI migration and the plugin story.
3. **Input fields** — only Bresenham has them (`input_fields=["xl","yl","xr","yr"]`,
   `presets.py:49`); `MainWindow._read_inputs()` coerces every field with
   `int(entry.get())` (`main_window.py:98-106`) — no types, no ranges, no
   labels, no non-integer inputs possible.
4. **Fixed data** — bubble sort's array is `DEFAULT_VALUES = [8,3,9,1,6,4,7,2,5]`
   (`bubble_sort.py:3`); BFS's maze is the `WALLS` constant + generated grid
   graph (`bfs_pathfinding.py:3-31`). Neither is editable from the UI.
5. **No user scripts** — the pseudocode pane is editable and Run respects
   edits, but there is no save/name/load/share; edits die with the session.
6. **No visual customization** — colors are module constants in the
   renderers (`BAR_COLOR = "#4da3ff"`, `tk_array_renderer.py:9-12`); cell
   sizes are constructor defaults nothing overrides; there is no theme
   concept. Notably `PlaybackState.delay_ms` exists but **no speed slider
   was ever wired** (plan doc Phase 5 lists one; `main_window.py:49-56` has
   only Run/Play/Pause/Step/Reset/Quit).
7. **Global builtin whitelist** — `VIZ_BUILTIN_METHODS` and
   `PLAIN_CANVAS_METHODS` in `builtins_registry.py:15-30` are module-level
   dicts. A new canvas type that needs a new verb (e.g. `SetChild` for a
   tree view) requires editing core interpreter-adjacent source, which
   breaks any plugin story.

### Smaller findings worth recording

- **Model/view leak in GraphCanvas**: `graph_canvas.py:11-15` bakes
  presentation colors (`VISITED_COLOR = "#ffd23f"`, etc.) into the
  GUI-free model, and `visit()` stores a color, not a state. `ArrayCanvas`
  does it right — it broadcasts semantic *kinds* (`"compare"`, `"swap"`)
  and the renderer maps kind→color (`tk_array_renderer.py:14`). Theming
  requires GraphCanvas to adopt the ArrayCanvas pattern.
- **Steps carry no payload**: the interpreter yields bare `None`
  (`interpreter.py:170`). There is no line number, no description of what
  happened. This blocks three desirable features at once: highlighting the
  current pseudocode line in the editor, a human-readable step log, and any
  export/replay feature (Manim or otherwise).
- **No infinite-loop guard**: a user-typed `while` that never calls a viz
  builtin never yields, so `next()` never returns and the Tk event loop
  freezes (`runner.py:68` would block forever). Fine for three vetted
  presets; not fine once non-programmers write and share scripts.
- **DSL has no `break`/`continue`** — visible in `bresenham_line.py:23-24`
  where a `done = 0` flag emulates `break`. Livable, but worth a line in
  any user-facing pseudocode documentation.
- Strings *are* supported constants (`ast.Constant`), so
  `PlotPixel(x, y, "blue")` already works even though no preset uses it.

---

## UI/UX Redesign Options

### The invariant to protect

Whatever wins must host the existing animation model: a generator advanced
by an event-loop timer. Concretely, a frontend needs (a) an
`after(ms, cb)`-shaped scheduler for `Runner`, and (b) listener
implementations for the three canvas models' callbacks. That's the whole
contract; everything else is cosmetics.

### Comparison

| Option | Effort | What survives unchanged | What changes | Step/play/pause fit | Packaging |
|---|---|---|---|---|---|
| **A. CustomTkinter** (or ttkbootstrap) reskin + renderer polish | ~2–4 days | `pseudocode/`, `engine/`, all 3 canvas models, all 3 Tk renderers (still `tk.Canvas` inside a CTk frame), `Runner` wiring (`root.after` unchanged) | `main_window.py` widget classes (`tk.Button`→`CTkButton`, `ScrolledText`→`CTkTextbox`, …); a theme-token module; renderer color/padding pass | Perfect — same Tk event loop, zero adapter | Adds 2–3 small pure-Python pip deps; PyInstaller-friendly; still light |
| **B. PySide6 / Qt** | ~2–3 weeks | `pseudocode/`, `engine/` (via a ~10-line `QtScheduler` adapter wrapping `QTimer`), all 3 canvas models, all tests | All 3 renderers rewritten against `QGraphicsScene` (or `QPainter`); `main_window.py` and `app.py` rewritten; presets decoupled from renderer classes (needed anyway) | Very good — `QTimer.singleShot(ms, cb)` satisfies `Scheduler` structurally; `QGraphicsScene` item updates mirror the Tk item-id pattern | ~200 MB wheel set; LGPL; PyInstaller output ~100 MB+ |
| **C. Web frontend** (pywebview / Eel / local Flask+JS) | ~4–6 weeks | `pseudocode/`, `engine/` core logic, canvas *models* (state + semantics) | Renderers become JS (SVG/`<canvas>`); a Python↔JS event bridge (each listener event serialized over RPC/websocket); scheduler re-hosted on the webview/asyncio loop; input forms, editor (could gain CodeMirror), controls all rebuilt in HTML/JS | Workable but the trickiest: step events must cross a process/language boundary; latency and ordering need care; two codebases to keep in sync | pywebview itself is small (WebView2 ships with Win11) but you now distribute a hybrid app; dev loop needs JS tooling |

*(ttkbootstrap is a near-equivalent to option A — it themes `ttk` widgets
with Bootstrap styles. Since `main_window.py` uses mostly classic `tk.*`
widgets and only one `ttk.Combobox`, either library implies the same
widget-swap pass. CustomTkinter's dark mode, rounded controls, and
`CTkTextbox`/`CTkSlider` map more directly onto what this app needs, so it
edges out ttkbootstrap; treat them as interchangeable in the roadmap.)*

### One honest caveat on option A

Reskinning the *shell* does not by itself make the *visualization* pretty —
the bars/pixels/circles live on a plain `tk.Canvas` under every Tk-family
option. Most of the perceived quality gain will come from the renderer
polish pass (a shared dark theme, gaps and rounded-corner bars via
`create_polygon`, value labels on bars, a subtle grid, larger default cell
sizes, highlight fade via a two-tone palette) — which is toolkit-neutral
work you'd want under Qt too. Budget it explicitly; don't expect the
widget library to do it.

### Recommendation (ranked)

1. **CustomTkinter reskin + renderer polish pass — do this now.** It is
   days of work, preserves 100% of the tested code, keeps packaging
   trivial, and the step engine runs unmodified. It also forces the two
   refactors (theme tokens, presets↔renderer decoupling) that every other
   future option needs anyway, so nothing is throwaway.
2. **PySide6 — the designated "if we outgrow Tk" path, not now.** The
   trigger conditions that would justify it: needing a real code editor
   (syntax highlighting, error underlines — Qt has `QSyntaxHighlighter`;
   Tk text tags can fake ~70% of it), needing >60fps or thousands of canvas
   items, or needing docking/multi-pane layouts. The `Scheduler` protocol
   and listener pattern mean the migration cost is bounded and known
   (renderers + shell only). Do the presets decoupling now so this door
   stays open cheaply.
3. **Web frontend — not recommended at this stage.** It buys the best
   ceiling (CSS transitions, D3-quality visuals, shareable in-browser
   version eventually) but at the cost of splitting the codebase across two
   languages and moving the app's core interaction loop across an RPC
   boundary. That's a rewrite-shaped decision, and nothing in the current
   goals (nicer look, customization) requires it. Revisit only if
   "runs in a browser / share a link" becomes a product goal — in which
   case Pyodide (the interpreter is pure stdlib and would run in-browser
   as-is) is worth evaluating alongside pywebview.

---

## Customization Architecture Proposal

### Design goals

- A non-programmer can add an algorithm by **dropping one text file** in a
  folder — no Python, no reinstall.
- Input fields, canvas setup, and initial data come from that file; the UI
  **generates its widgets from a schema** instead of hand-coded per preset.
- The UI can **save** the current editor contents + inputs back to that
  same format ("Save preset…"), which makes sharing = sending a file.
- A programmer can add a **new canvas type** (tree/heap, stack, matrix)
  as a separate pip package or dropped-in module, registering its own
  builtins, without editing `algoviz` source.

### 1. Preset file format: TOML

TOML wins over JSON and YAML for this specific job: JSON cannot hold a
12-line pseudocode block readably (every line becomes a `\n`-escaped string
fragment), and YAML adds a dependency plus its usual footguns. TOML's
multi-line literal strings (`'''…'''`) hold pseudocode verbatim, it's
comment-friendly for non-programmers, and `tomllib` is stdlib from Python
3.11 (bump `requires-python` to `>=3.11`, or add the ~15 KB `tomli`
backport for 3.10 — see Open Questions).

What the three existing presets look like migrated (grid example shown in
full; this file is the complete spec a user would write):

```toml
# ~/.algoviz/presets/bresenham-line.toml
[preset]
name = "Bresenham Line"
canvas = "grid"                 # which canvas type to mount
description = "Classic integer line rasterization."

[canvas]                        # params for the canvas factory — schema owned by the canvas type
width = 40
height = 30
background = "black"

[inputs.xl]                     # each entry auto-generates one input widget
type = "int"
default = 2
min = 0
max = 39
label = "Start X"

[inputs.yl]
type = "int"
default = 2
min = 0
max = 29
label = "Start Y"

[inputs.xr]
type = "int"
default = 24
label = "End X"

[inputs.yr]
type = "int"
default = 11
label = "End Y"

source = '''
dx = abs(xr - xl)
dy = -abs(yr - yl)
...   # (verbatim pseudocode, exactly as in bresenham_line.py today)
'''
```

The array and graph presets show why `[canvas]` params must be
schema-per-canvas-type, not one shared shape:

```toml
[preset]
name = "Bubble Sort"
canvas = "array"

[canvas]
values = [8, 3, 9, 1, 6, 4, 7, 2, 5]   # finally user-editable
```

```toml
[preset]
name = "BFS Pathfinding"
canvas = "graph"

[canvas]                        # human-drawable maze: S=start, G=goal, #=wall
maze = [
  "S..#.#..",
  "...#.#..",
  "...#.#..",
  "...#....",
  ".....#..",
  "...#.#.G",
]
```

The maze-as-strings encoding replaces `_build_grid_graph()`
(`bfs_pathfinding.py:7-28`) as a *graph-canvas param codec* — the same
wall/grid logic, moved behind the canvas type's param schema, editable by
anyone who can type `#`.

**Loading order**: bundled presets ship as package data
(`src/algoviz/presets/*.toml`, replacing the three `.py` algorithm modules'
role as preset carriers), then `~/.algoviz/presets/*.toml` is scanned at
startup and merged into the picker (user files win on name collision). A
malformed file surfaces as a status-panel warning, never a crash.

### 2. Parameter schema per canvas type

Each canvas type declares its parameters once; both the TOML loader
(validation) and the UI (widget generation) consume the same declaration.
This replaces the blanket `int(entry.get())` in
`main_window.py:98-106` and the hand-maintained `input_fields` list.

```python
@dataclass(frozen=True)
class ParamSpec:
    name: str
    type: Literal["int", "float", "str", "color", "int_list", "str_list"]
    default: Any = None
    min: int | float | None = None
    max: int | float | None = None
    label: str | None = None

@dataclass(frozen=True)
class CanvasType:
    id: str                                  # "grid" | "array" | "graph" | plugin-provided
    canvas_params: list[ParamSpec]           # validates a preset's [canvas] table
    make_canvas: Callable[[dict], VizCanvas] # params -> model instance
    viz_builtins: dict[str, str]             # e.g. {"PlotPixel": "plot_pixel"}
    plain_builtins: dict[str, str]           # e.g. {"Neighbors": "neighbors"}
    renderers: dict[str, Callable]           # frontend id -> renderer factory, e.g. {"tk": TkGridRenderer}
```

Note the two structural fixes bundled in here:

- **`viz_builtins`/`plain_builtins` move from the global dicts in
  `builtins_registry.py` onto the canvas type.** `resolve_builtin()`
  already takes the canvas and probes it with `getattr`
  (`builtins_registry.py:48-67`), so the runtime change is small: resolve
  against the active canvas type's maps + the shared `PLAIN_BUILTINS`
  (`round`, `abs`, `len`, `int`, `range` stay global). The interpreter
  itself doesn't change at all.
- **`renderers` is a frontend-keyed dict**, which removes the
  `presets.py → tk_*_renderer` import coupling (`presets.py:16-18`). The
  Tk shell asks for `renderers["tk"]`; a future Qt shell asks for
  `renderers["qt"]`. Core preset/canvas code stops importing tkinter-adjacent
  modules entirely.

The `inputs` table (per-preset, seeded into the interpreter env) uses the
same `ParamSpec` shape, so one widget-generation function serves both
canvas params and algorithm inputs.

### 3. Saving and sharing from the UI

"Save preset…" serializes the current state — selected canvas type, its
current `[canvas]` params, the `inputs` specs with current values as
defaults, and the editor text as `source` — into
`~/.algoviz/presets/<slug>.toml`, then refreshes the picker. Sharing is
"send the file". No format versioning ceremony needed yet beyond a
`format = 1` key in `[preset]` for future-proofing.

Two safety items become mandatory once arbitrary user scripts are normal:

- **Step budget**: give `Interpreter` a configurable max instruction count
  (or max wall-clock per `next()` slice) so a viz-free `while 1:` raises
  `PseudocodeError("step budget exceeded")` instead of freezing the UI
  (today it would hang in `runner.py:68`).
- The DSL's existing safety story (no `exec`, whitelisted calls only,
  no attribute access) already makes shared preset files safe to *run*;
  the budget closes the only remaining hole (non-termination).

### 4. Visual customization and theming

- Extract every color/size constant from the renderers into a
  `ThemeTokens` dataclass (one built-in dark + one light theme to start),
  loaded from an optional `~/.algoviz/theme.toml` with the same shape.
- Fix the GraphCanvas model/view leak first: `visit()`/`highlight()` should
  record semantic states (`"visited"`, `"path"`) and broadcast those;
  the renderer maps state→theme color, exactly as `TkArrayRenderer`
  already maps `"compare"`/`"swap"`/`"write"` kinds
  (`tk_array_renderer.py:14`). This is a small, test-covered change
  (`test_graph_canvas.py` asserts colors today and would assert states
  instead).
- Add the missing **speed slider** bound to `PlaybackState.delay_ms` —
  the model support has existed since Phase 2; it's a ~5-line UI addition.

### 5. Plugin mechanism for new canvas types

Two tiers, same registration object:

1. **Pip-installable plugins** via entry points — the standard, robust path:

   ```toml
   # in the plugin package's pyproject.toml
   [project.entry-points."algoviz.canvases"]
   tree = "algoviz_tree:TREE_CANVAS_TYPE"    # a CanvasType instance
   ```

   At startup algoviz iterates
   `importlib.metadata.entry_points(group="algoviz.canvases")` and
   registers each `CanvasType`. A tree/heap plugin ships its model, its Tk
   renderer, its builtins (`SetNode`, `SwapNodes`, `Parent`, `LeftChild`,
   …), its param schema, and typically a few bundled `.toml` presets that
   reference `canvas = "tree"`.

2. **Drop-in local plugins** (`~/.algoviz/plugins/*.py`, each exposing a
   module-level `CANVAS_TYPE`) for people who won't publish a package.
   This is deliberately a power-user door — it executes arbitrary local
   Python, which is the same trust level as installing a package, but it
   should be documented as such.

The deliberately-thin `VizCanvas` protocol (`canvas/base.py` — just
`clear()`) survives unchanged; it was the right call and the plugin model
leans on it: the *interpreter* never needs to know a canvas's surface,
because builtin resolution already goes through per-name `getattr` probing.

### Migration path from today's hardcoded presets

1. Introduce `ParamSpec`/`CanvasType` and register the three existing
   canvas types with them; rewrite `resolve_builtin` to consult the active
   `CanvasType`. All existing tests keep passing (the interpreter contract
   is untouched).
2. Convert `bresenham_line.py`/`bubble_sort.py`/`bfs_pathfinding.py` into
   three bundled `.toml` files; keep the `.py` modules for one release as
   thin loaders (their `SOURCE`/`DEFAULT_*` constants read from the TOML)
   so `test_algorithms_*.py` needs only import-path edits.
3. Replace `PRESETS` in `ui/presets.py` with the loader
   (bundled dir + `~/.algoviz/presets/`); `MainWindow._load_algorithm()`
   switches to schema-driven widget generation.
4. Add Save preset…, speed slider, step budget.
5. Add entry-point scanning; publish the tree/heap canvas as the first
   plugin *outside* the core package to prove the seam is real.

---

## Manim Feasibility Study

### Verdict

**Do not adopt Manim as the interactive rendering surface — that path is
infeasible, not merely hard. Do not build the export feature yet either —
it's feasible but the payoff doesn't justify the footprint today. Do add
the structured step-event log now (cheap, needed by the UI anyway), which
keeps a future Manim exporter a bounded, optional add-on.**

### Why live interaction is a dead end

Manim's execution model is compile-then-render: `Scene.construct()` runs to
completion building an animation timeline, which the renderer (Cairo
frames → pyav/ffmpeg encode in Manim CE) then writes to a video file. There
is no frame-by-frame external control surface in that model at all.

The interactive modes that exist are authoring aids, not embedding APIs:

- **Manim CE, OpenGL renderer** (`--renderer=opengl`,
  `Scene.interactive_embed()`): opens a preview window and drops the
  *developer* into an IPython REPL to try animations. The window belongs to
  Manim's own loop; there is no supported way to mount it inside a Tk/Qt
  app, and "input" means typing Python at the REPL, not receiving events
  from a host application. The CE OpenGL renderer has also been
  half-supported for years (long-standing known gaps vs. the Cairo
  renderer).
- **ManimGL** (3b1b's fork, `self.embed()` + checkpoint_paste): the same
  idea, tuned for Grant's video-authoring workflow. It's a moving target
  with sparse docs, and again the interaction contract is "a human in an
  IPython shell", not "a host app injecting state".

Wiring Play/Pause/Step from a Tk toolbar into a running Manim scene would
mean fighting the tool's core assumption from inside a private event loop.
Every hour spent there is better spent on the renderer polish pass.

### The middle path, assessed honestly

The replay-export idea is architecturally sound *because of work worth
doing anyway*. Today the interpreter yields bare `None`
(`interpreter.py:170`) and canvases broadcast listener events that die in
the renderer. Add a `StepEvent` (action name, args, source line — emitted
either as the yield value or via a recording listener tap, the same trick
`tests/conftest.py`'s `RecordingCanvas` already uses), and one live run
produces a complete, serializable event log. An exporter is then a pure
function: `list[StepEvent] × canvas params → Scene subclass → mp4`. Mapping
is direct — `Square`s in a `VGroup` for the grid, `Rectangle`s for bars,
`Circle`/`Line` for the graph, `Transform`/`Indicate` per event, roughly
150–300 lines per canvas type. No re-execution, no determinism worries, no
interpreter changes beyond the event payload.

Costs, current as of Manim CE v0.19+: the external ffmpeg binary is no
longer required (CE moved to bundled PyAV bindings), and LaTeX (the
1–2 GB MiKTeX/TeX Live install) is only needed for `Tex`/`MathTex`, which
this exporter wouldn't use (`Text` renders via Pango). So the footprint is
"heavy pip install" (numpy, pycairo, ManimPango, pyav, …) rather than
"system dependencies nightmare" — real but manageable as an optional
`algoviz[export]` extra that core users never pay for.

The reason the verdict is still "not yet" is payoff, not feasibility: this
app's visuals are axis-aligned rectangles and circles. A Manim render of
bubble sort looks maybe 20% better than a well-themed Tk canvas capture,
and Manim's actual differentiators — LaTeX-typeset math, smooth
morphs/camera work, 3Blue1Brown-style annotation — have nothing to attach
to in the current feature set. If/when export demand materializes,
**ship GIF/MP4 export from the canvas model via Pillow or imageio first**
(same `StepEvent` log, ~a day of work, tiny deps, good-enough output for
sharing a run); graduate to a Manim exporter only if users specifically
want presentation-quality video with captions/annotations. The event log
makes that a plugin-sized decision later instead of an architecture
decision now.

---

## Recommended Roadmap

Phased in the same vertical-slice spirit as the original plan — each phase
ships something visible and none requires a rewrite. The current
architecture supports all of it; the only structural debts to pay are the
presets↔renderer decoupling and the global builtin maps, both scheduled
early because everything else leans on them.

**Phase 6 — Event payloads + small UX debts** *(small)*
Interpreter yields `StepEvent(action, args, lineno)`; `MainWindow`
highlights the current line in the editor (Tk text tags) and logs readable
steps in the status pane. Add the speed slider (binds to
`PlaybackState.delay_ms`) and the interpreter step budget. Pure additive;
tests extend `test_interpreter.py` to assert event payloads.

**Phase 7 — Customization core** *(medium; the load-bearing phase)*
`ParamSpec`/`CanvasType` registry; per-canvas builtins; migrate the three
algorithms to bundled TOML; TOML loader + `~/.algoviz/presets/`;
schema-generated input widgets; Save preset…. Exit criterion: a
non-programmer adds insertion sort with a custom array by writing one TOML
file, zero Python edits.

**Phase 8 — Visual overhaul** *(medium)*
CustomTkinter shell; `ThemeTokens` + dark/light themes +
`~/.algoviz/theme.toml`; fix the GraphCanvas color→state refactor;
renderer polish pass (this is where "looks good" actually lands).
Done after Phase 7 so widget generation is built once, against the schema,
in the new widget set — not built twice.

**Phase 9 — Plugin seam** *(medium)*
Entry-point + drop-in plugin loading; build the tree/heap canvas as an
external package to prove it; document the DSL + preset format for users
(including the no-`break` limitation).

**Phase 10 (optional, demand-driven) — Export** *(small→large)*
GIF/MP4 via Pillow/imageio replaying the `StepEvent` log. Manim exporter
as `algoviz[export]` only if presentation-quality output is explicitly
requested.

---

## Open Questions

1. **Python floor**: bump `requires-python` to `>=3.11` for stdlib
   `tomllib`, or stay on 3.10 and vendor/depend on `tomli`? (3.11 bump
   recommended — 3.10 hits end-of-life October 2026.)
2. **CustomTkinter vs ttkbootstrap**: functionally interchangeable for this
   app; CustomTkinter recommended for its dark mode and `CTkTextbox`/
   `CTkSlider`, but if you prefer staying closer to stock ttk (lighter,
   more conservative look), say so before Phase 8.
3. **Audience for plugins**: is the tree/heap canvas something *you* want
   to write, or should the plugin API be documented to teacher/student
   level? That decides how much Phase 9 invests in docs vs. seam.
4. **Distribution target**: is a PyInstaller single-file EXE a goal? It's
   easy under options A/B and materially affects how bundled presets and
   `~/.algoviz/` paths should be resolved — cheap to design for now, fiddly
   to retrofit.
5. **Editable canvas data in the UI**: Phase 7 makes arrays/mazes editable
   via preset files; do you also want in-app editing (e.g. click cells to
   toggle walls, type an array into a field)? That's a natural Phase 8.5
   but scoped out until asked.
6. **Export demand**: does anyone actually want video/GIF output today?
   If yes, Phase 10's GIF path can move up; if no, it stays parked and only
   the (free) event log lands.
