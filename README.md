# GraphicsAlgoVisualizer

A pseudocode-driven 2D algorithm visualizer built with Python and CustomTkinter. Write algorithms in a simple DSL, pick a canvas type, and watch them execute step-by-step with animated visuals, speed control, and presentation mode.

---

## ✨ Features

- **Pseudocode DSL** — Write algorithms in a clean, Python-like subset with `for`, `while`, `if/elif/else`, variables, expressions, and built-in functions. No Python knowledge required.
- **Multiple Canvas Types** — Grid, Array, and Graph canvases with dedicated renderers and built-in operations.
- **Bundled Algorithm Presets** — Bresenham line drawing, Bubble sort, BFS pathfinding, and Dijkstra's shortest path ship out of the box as TOML presets.
- **In-App Graph Editor** — Click to add nodes, drag between nodes to create edges, set weights — build custom networks visually.
- **Step-by-Step Playback** — Play, pause, step forward, adjust speed, and see line-by-line highlighting of the executing pseudocode.
- **Presentation Mode** — A distraction-free, canvas-only view for demos and classroom walkthroughs.
- **Theme System** — Centralized theme tokens drive all canvas and UI colors for a consistent look.
- **Plugin Architecture** — Drop-in and entry-point based plugin loading. Extend the visualizer with custom canvas types (see the bundled `pyalgoviz-heap-canvas` example).
- **User Presets** — Save your own algorithms as `.toml` preset files and load them from a user presets directory.

---

## 📋 Prerequisites

- **Python 3.11+**
- **Tkinter** (usually ships with Python; see platform notes below)
- **Git** (to clone the repo)

---

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/F3rNaNDEZ57/GraphicsAlgoVisualizer.git
cd GraphicsAlgoVisualizer
```

### 2. Create a Virtual Environment

#### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

#### Windows (Command Prompt)

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

### 3. Install the Package

Install in editable (development) mode so changes take effect immediately:

```bash
pip install -e ".[dev]"
```

> **Note:** The `[dev]` extra includes `pytest` for running tests.

### 4. Run the Visualizer

```bash
pyalgoviz
```

Or run directly as a module:

```bash
python -m pyalgoviz.app
```

---

## 🖥️ Platform-Specific Notes

### macOS

Tkinter is included with the official Python installer from [python.org](https://www.python.org). If you installed Python via Homebrew, you may need to install it separately:

```bash
brew install python-tk@3.11
```

### Linux (Debian / Ubuntu)

```bash
sudo apt update
sudo apt install python3-tk
```

### Linux (Fedora)

```bash
sudo dnf install python3-tkinter
```

### Linux (Arch)

```bash
sudo pacman -S tk
```

### Windows

Tkinter is bundled with the standard Python installer from [python.org](https://www.python.org). No extra steps needed — just make sure to check **"tcl/tk and IDLE"** during installation if using the custom installer.

---

## 🏗️ Project Structure

```
GraphicsAlgoVisualizer/
├── src/pyalgoviz/
│   ├── app.py                  # Entry point
│   ├── theme.py                # Centralized theme tokens
│   ├── canvas_types.py         # Side-effect import to register canvas types
│   ├── plugins.py              # Plugin discovery and loading
│   ├── preset_loader.py        # TOML preset loader
│   ├── canvas/                 # Canvas types, renderers, and registry
│   │   ├── base.py             # Abstract base canvas
│   │   ├── registry.py         # Canvas type registry
│   │   ├── grid_canvas.py      # Grid canvas (e.g., Bresenham)
│   │   ├── array_canvas.py     # Array canvas (e.g., Bubble sort)
│   │   ├── graph_canvas.py     # Graph canvas (e.g., BFS, Dijkstra)
│   │   └── tk_*_renderer.py    # Tkinter renderers for each canvas
│   ├── engine/                 # Step engine and playback state
│   │   ├── runner.py           # Runs pseudocode on a canvas
│   │   └── playback.py         # Play/pause/step state machine
│   ├── pseudocode/             # DSL interpreter
│   │   ├── interpreter.py      # Pseudocode interpreter
│   │   ├── builtins_registry.py# Built-in functions (SetCell, Enqueue, etc.)
│   │   ├── step_event.py       # Step event payloads
│   │   └── errors.py           # Error types
│   ├── presets/                 # Bundled TOML algorithm presets
│   │   ├── bresenham-line.toml
│   │   ├── bubble-sort.toml
│   │   ├── bfs-pathfinding.toml
│   │   └── dijkstra-shortest-path.toml
│   └── ui/                     # CustomTkinter UI layer
│       ├── main_window.py      # Main application window
│       ├── graph_editor_model.py  # Headless graph editor model
│       └── graph_editor_view.py   # Visual graph editor widget
├── plugins/                    # Drop-in plugin directory
│   └── pyalgoviz-heap-canvas/    # Example plugin
├── tests/                      # Test suite (pytest)
├── pyproject.toml              # Project metadata and build config
└── .gitignore
```

---

## 🧪 Running Tests

```bash
pytest
```

Run with verbose output:

```bash
pytest -v
```

Run a specific test file:

```bash
pytest tests/test_interpreter.py
```

---

## 📝 Writing a Custom Preset

Presets are `.toml` files that define an algorithm's pseudocode, canvas type, and parameters. Place them in the bundled `src/pyalgoviz/presets/` directory or the user presets directory.

**Example — a simple grid algorithm:**

```toml
[meta]
name = "My Algorithm"
canvas = "grid"

[params]
width = 20
height = 20

[source]
code = """
for x in Range(0, 10):
    SetCell(x, x, "visited")
"""
```

### Supported Canvas Types

| Canvas  | Use Case                        | Key Builtins                          |
|---------|---------------------------------|---------------------------------------|
| `grid`  | 2D grid algorithms              | `SetCell`, `GetCell`, `Mark`          |
| `array` | Sorting / linear data           | `Swap`, `Compare`, `SetIndex`         |
| `graph` | Graph traversal / shortest path | `Enqueue`, `Dequeue`, `MarkEdge`      |

---

## 🔌 Plugins

The visualizer supports two plugin mechanisms:

1. **Drop-in plugins** — Place a Python package in the `plugins/` directory. It will be auto-discovered on startup.
2. **Entry-point plugins** — Register a `pyalgoviz.canvases` entry point in your package's `pyproject.toml`. Installed packages with this entry point are loaded automatically.

See [`plugins/pyalgoviz-heap-canvas/`](plugins/pyalgoviz-heap-canvas/) for a working example.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Run the tests (`pytest`)
5. Commit with a descriptive message (`git commit -m "Add my feature"`)
6. Push to your fork (`git push origin feature/my-feature`)
7. Open a Pull Request

---

## 📄 License

MIT — see [LICENSE](LICENSE) for details.
