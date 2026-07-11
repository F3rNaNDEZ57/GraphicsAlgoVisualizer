"""Tkinter shell: algorithm picker + pseudocode editor + canvas + playback
controls. Algorithms are loaded from TOML presets (see preset_loader.py)
instead of hardcoded Python modules; canvas/renderer/builtins for the
selected preset come from the canvas type registry (see
canvas/registry.py), populated by importing canvas_types at startup.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import scrolledtext, simpledialog, ttk

import algoviz.canvas_types  # noqa: F401 -- side effect: registers grid/array/graph canvas types
from algoviz.canvas.registry import ParamSpec, get as get_canvas_type
from algoviz.engine.playback import PlaybackState
from algoviz.engine.runner import Runner
from algoviz.preset_loader import (
    BUNDLED_PRESETS_DIR,
    USER_PRESETS_DIR,
    LoadedPreset,
    load_all_presets,
    write_preset_file,
)
from algoviz.pseudocode.errors import PseudocodeError
from algoviz.pseudocode.interpreter import Interpreter
from algoviz.pseudocode.step_event import StepEvent

CURRENT_LINE_TAG = "current_line"
CURRENT_LINE_BG = "#444444"
CURRENT_LINE_FG = "#ffffff"


def _coerce_input(spec: ParamSpec, raw: str):
    if spec.type == "int":
        value: object = int(raw)
    elif spec.type == "float":
        value = float(raw)
    else:
        value = raw
    if spec.min is not None and value < spec.min:
        raise ValueError(f"{spec.label} must be >= {spec.min}")
    if spec.max is not None and value > spec.max:
        raise ValueError(f"{spec.label} must be <= {spec.max}")
    return value


class MainWindow:
    def __init__(
        self,
        root: tk.Tk,
        bundled_dir: Path = BUNDLED_PRESETS_DIR,
        user_dir: Path = USER_PRESETS_DIR,
    ):
        self.root = root
        self.bundled_dir = bundled_dir
        self.user_dir = user_dir
        self.playback = PlaybackState(delay_ms=40)
        self.runner: Runner | None = None
        self.canvas = None
        self.renderer = None
        self.canvas_type = None
        self.preset: LoadedPreset | None = None
        self.input_widgets: dict[str, tk.Entry] = {}

        self._build_static_widgets()
        self._reload_preset_list()

    def _build_static_widgets(self) -> None:
        top = tk.Frame(self.root)
        top.pack(fill="x")
        tk.Label(top, text="Algorithm:").pack(side="left")
        self.algo_var = tk.StringVar()
        self.algo_menu = ttk.Combobox(top, textvariable=self.algo_var, state="readonly", width=20)
        self.algo_menu.pack(side="left")
        self.algo_menu.bind("<<ComboboxSelected>>", lambda _event: self._load_algorithm())
        tk.Button(top, text="Save preset…", command=self.save_preset).pack(side="left", padx=(8, 0))

        self.input_frame = tk.Frame(self.root)
        self.input_frame.pack(fill="x")

        self.code_input = scrolledtext.ScrolledText(self.root, width=70, height=16)
        self.code_input.tag_config(CURRENT_LINE_TAG, background=CURRENT_LINE_BG, foreground=CURRENT_LINE_FG)
        self.code_input.pack()

        controls = tk.Frame(self.root)
        controls.pack(fill="x")
        tk.Button(controls, text="Run", command=self.run_code).pack(side="left")
        tk.Button(controls, text="Play", command=self.play).pack(side="left")
        tk.Button(controls, text="Pause", command=self.pause).pack(side="left")
        tk.Button(controls, text="Step", command=self.step).pack(side="left")
        tk.Button(controls, text="Reset", command=self.reset).pack(side="left")
        tk.Button(controls, text="Quit", command=self.root.destroy).pack(side="left")

        tk.Label(controls, text="Delay (ms/step):").pack(side="left", padx=(12, 0))
        self.speed_var = tk.IntVar(value=self.playback.delay_ms)
        tk.Scale(
            controls,
            from_=10,
            to=500,
            orient="horizontal",
            variable=self.speed_var,
            length=140,
            command=self._on_speed_change,
        ).pack(side="left")

        self.canvas_frame = tk.Frame(self.root)
        self.canvas_frame.pack()

        self.status = scrolledtext.ScrolledText(self.root, width=70, height=6)
        self.status.pack()

    def _reload_preset_list(self, select: str | None = None) -> None:
        self.presets, errors = load_all_presets(self.bundled_dir, self.user_dir)
        for err in errors:
            self._log(f"Preset load warning: {err}")
        self.algo_menu["values"] = list(self.presets)

        if not self.presets:
            self._log("No presets found.")
            return
        target = select if select in self.presets else next(iter(self.presets))
        self.algo_var.set(target)
        self._load_algorithm()

    def _load_algorithm(self) -> None:
        if self.runner is not None:
            self.runner.pause()
        self.runner = None

        self.preset = self.presets[self.algo_var.get()]
        self.canvas_type = get_canvas_type(self.preset.canvas_type_id)
        self.root.title(f"AlgoViz — {self.preset.name}")

        for widget in self.canvas_frame.winfo_children():
            widget.destroy()
        for widget in self.input_frame.winfo_children():
            widget.destroy()
        self.input_widgets.clear()

        self.canvas = self.canvas_type.make_canvas(self.preset.canvas_params)
        renderer_cls = self.canvas_type.renderers["tk"]
        self.renderer = renderer_cls(self.canvas_frame, self.canvas)
        self.renderer.widget.pack()

        for key, spec in self.preset.inputs.items():
            tk.Label(self.input_frame, text=f"{spec.label}:").pack(side="left")
            entry = tk.Entry(self.input_frame, width=8)
            entry.insert(0, str(spec.default))
            entry.pack(side="left")
            self.input_widgets[key] = entry

        self.code_input.delete("1.0", tk.END)
        self.code_input.insert("1.0", self.preset.source)
        self._clear_line_highlight()
        self._log(f"Loaded {self.preset.name}.")

    def _log(self, message: str) -> None:
        self.status.insert(tk.END, message + "\n")
        self.status.see(tk.END)

    def _on_speed_change(self, value: str) -> None:
        self.playback.delay_ms = int(float(value))

    def _on_step(self, event: StepEvent) -> None:
        self._highlight_line(event.lineno)
        args_repr = ", ".join(repr(a) for a in event.args)
        self._log(f"line {event.lineno}: {event.action}({args_repr})")

    def _highlight_line(self, lineno: int | None) -> None:
        self._clear_line_highlight()
        if lineno is not None:
            self.code_input.tag_add(CURRENT_LINE_TAG, f"{lineno}.0", f"{lineno}.end+1c")
            self.code_input.see(f"{lineno}.0")

    def _clear_line_highlight(self) -> None:
        self.code_input.tag_remove(CURRENT_LINE_TAG, "1.0", tk.END)

    def _read_inputs(self) -> dict | None:
        env: dict = {}
        try:
            for key, entry in self.input_widgets.items():
                spec = self.preset.inputs[key]
                env[key] = _coerce_input(spec, entry.get())
        except ValueError as exc:
            self._log(f"Invalid input: {exc}")
            return None
        return env

    def run_code(self) -> None:
        if self.runner is not None:
            self.runner.pause()
        env = self._read_inputs()
        if env is None:
            return
        self.reset()

        source = self.code_input.get("1.0", tk.END)
        try:
            interpreter = Interpreter(source, self.canvas, self.canvas_type.viz_builtins, self.canvas_type.plain_builtins)
        except PseudocodeError as exc:
            self._log(f"Error: {exc}")
            return
        interpreter.env.update(env)

        self.runner = Runner(
            self.root,
            interpreter.run(),
            self.playback,
            on_finish=lambda: self._log("Done."),
            on_error=lambda exc: self._log(f"Error: {exc}"),
            on_step=self._on_step,
        )
        self._log("Running...")
        self.runner.play()

    def play(self) -> None:
        if self.runner:
            self.runner.play()

    def pause(self) -> None:
        if self.runner:
            self.runner.pause()

    def step(self) -> None:
        if self.runner:
            self.runner.step()

    def reset(self) -> None:
        if self.runner:
            self.runner.pause()
        if self.canvas:
            self.canvas.clear()
        self._clear_line_highlight()

    def save_preset(self) -> None:
        if self.preset is None:
            return
        name = simpledialog.askstring(
            "Save preset", "Preset name:", initialvalue=self.preset.name, parent=self.root
        )
        if not name:
            return
        self._do_save_preset(name)

    def _do_save_preset(self, name: str) -> Path | None:
        """The actual save logic, split out from save_preset() so it can be
        exercised without the blocking name-prompt dialog (e.g. in tests)."""
        inputs = self._read_inputs()
        if inputs is None:
            return None
        new_inputs = {
            key: ParamSpec(key, spec.type, default=inputs[key], min=spec.min, max=spec.max, label=spec.label)
            for key, spec in self.preset.inputs.items()
        }
        to_save = LoadedPreset(
            name=name,
            canvas_type_id=self.preset.canvas_type_id,
            description=self.preset.description,
            canvas_params=self.preset.canvas_params,
            inputs=new_inputs,
            source=self.code_input.get("1.0", tk.END),
        )
        path = write_preset_file(to_save, directory=self.user_dir)
        self._log(f"Saved preset '{name}' to {path}")
        self._reload_preset_list(select=name)
        return path


def launch() -> None:
    root = tk.Tk()
    MainWindow(root)
    root.mainloop()
