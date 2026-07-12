"""CustomTkinter shell: algorithm picker + pseudocode editor + canvas +
playback controls. Algorithms are loaded from TOML presets (see
preset_loader.py) instead of hardcoded Python modules; canvas/renderer/
builtins for the selected preset come from the canvas type registry (see
canvas/registry.py), populated by importing canvas_types at startup.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path

import customtkinter as ctk

import algoviz.canvas_types  # noqa: F401 -- side effect: registers grid/array/graph canvas types
from algoviz.canvas.registry import ParamSpec, all_types as all_canvas_types, get as get_canvas_type
from algoviz.engine.playback import PlaybackState
from algoviz.engine.runner import Runner
from algoviz.plugins import DEFAULT_PLUGINS_DIR, load_all_plugins
from algoviz.ui.graph_editor_view import GraphEditorView
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
from algoviz.theme import DARK, ThemeTokens, load_theme

CURRENT_LINE_TAG = "current_line"


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
        root: tk.Misc,
        bundled_dir: Path = BUNDLED_PRESETS_DIR,
        user_dir: Path = USER_PRESETS_DIR,
        theme: ThemeTokens = DARK,
        plugins_dir: Path = DEFAULT_PLUGINS_DIR,
        load_plugins: bool = True,
    ):
        self.root = root
        self.bundled_dir = bundled_dir
        self.user_dir = user_dir
        self.theme = theme
        self.playback = PlaybackState(delay_ms=40)
        self.runner: Runner | None = None
        self.canvas = None
        self.renderer = None
        self.canvas_type = None
        self.preset: LoadedPreset | None = None
        self.input_widgets: dict[str, ctk.CTkEntry] = {}

        if hasattr(self.root, "configure"):
            try:
                self.root.configure(fg_color=self.theme.bg)
            except tk.TclError:
                pass  # root isn't a CTk-aware widget (e.g. a bare tk.Tk in some tests)

        self._build_static_widgets()

        self._plugin_errors: list[str] = []
        if load_plugins:
            self._plugin_errors = load_all_plugins(plugins_dir)

        self._reload_preset_list()

        for err in self._plugin_errors:
            self._log(f"Plugin load warning: {err}")
        if any(t not in ("grid", "array", "graph") for t in all_canvas_types()):
            extra = sorted(set(all_canvas_types()) - {"grid", "array", "graph"})
            self._log(f"Loaded plugin canvas types: {', '.join(extra)}")

    def _build_static_widgets(self) -> None:
        theme = self.theme

        top = ctk.CTkFrame(self.root, fg_color=theme.panel_bg)
        top.pack(fill="x", padx=8, pady=(8, 4))
        ctk.CTkLabel(top, text="Algorithm:", text_color=theme.fg).pack(side="left", padx=(8, 4))
        self.algo_menu = ctk.CTkComboBox(
            top, values=[], state="readonly", width=220, command=self._on_algo_selected
        )
        self.algo_menu.pack(side="left")
        ctk.CTkButton(top, text="Save preset…", command=self.save_preset, width=110).pack(
            side="left", padx=(8, 4)
        )
        ctk.CTkButton(top, text="New Network…", command=self.open_graph_editor, width=120).pack(
            side="left", padx=(0, 8)
        )

        self.input_frame = ctk.CTkFrame(self.root, fg_color=theme.panel_bg)
        self.input_frame.pack(fill="x", padx=8, pady=4)

        self.code_input = ctk.CTkTextbox(self.root, width=680, height=280)
        self.code_input.tag_config(CURRENT_LINE_TAG, background="#444444", foreground="#ffffff")
        self.code_input.pack(padx=8, pady=4)

        controls = ctk.CTkFrame(self.root, fg_color=theme.panel_bg)
        controls.pack(fill="x", padx=8, pady=4)
        ctk.CTkButton(controls, text="Run", command=self.run_code, width=70).pack(side="left", padx=4, pady=6)
        ctk.CTkButton(controls, text="Play", command=self.play, width=70).pack(side="left", padx=4)
        ctk.CTkButton(controls, text="Pause", command=self.pause, width=70).pack(side="left", padx=4)
        ctk.CTkButton(controls, text="Step", command=self.step, width=70).pack(side="left", padx=4)
        ctk.CTkButton(controls, text="Reset", command=self.reset, width=70).pack(side="left", padx=4)
        ctk.CTkButton(controls, text="Quit", command=self.root.destroy, width=70).pack(side="left", padx=4)

        ctk.CTkLabel(controls, text="Delay (ms/step):", text_color=theme.fg).pack(side="left", padx=(16, 4))
        self.speed_label = ctk.CTkLabel(controls, text=str(self.playback.delay_ms), text_color=theme.fg, width=36)
        ctk.CTkSlider(
            controls, from_=10, to=500, width=140, command=self._on_speed_change
        ).pack(side="left", padx=4)
        self.speed_label.pack(side="left")

        self.canvas_frame = ctk.CTkFrame(self.root, fg_color=theme.bg)
        self.canvas_frame.pack(padx=8, pady=4)

        self.status = ctk.CTkTextbox(self.root, width=680, height=110)
        self.status.pack(padx=8, pady=(4, 8))

    def _reload_preset_list(self, select: str | None = None) -> None:
        loaded, errors = load_all_presets(self.bundled_dir, self.user_dir)
        for err in errors:
            self._log(f"Preset load warning: {err}")

        registered = all_canvas_types()
        self.presets = {}
        for name, preset in loaded.items():
            if preset.canvas_type_id not in registered:
                self._log(
                    f"Preset '{name}' needs canvas type '{preset.canvas_type_id}', "
                    "which isn't registered (missing plugin?) -- skipped."
                )
                continue
            self.presets[name] = preset

        self.algo_menu.configure(values=list(self.presets))

        if not self.presets:
            self._log("No presets found.")
            return
        target = select if select in self.presets else next(iter(self.presets))
        self.algo_menu.set(target)
        self._load_algorithm()

    def _on_algo_selected(self, _choice: str) -> None:
        self._load_algorithm()

    def _load_algorithm(self) -> None:
        if self.runner is not None:
            self.runner.pause()
        self.runner = None

        self.preset = self.presets[self.algo_menu.get()]
        self.canvas_type = get_canvas_type(self.preset.canvas_type_id)
        if hasattr(self.root, "title"):
            self.root.title(f"AlgoViz — {self.preset.name}")

        for widget in self.canvas_frame.winfo_children():
            widget.destroy()
        for widget in self.input_frame.winfo_children():
            widget.destroy()
        self.input_widgets.clear()

        self.canvas = self.canvas_type.make_canvas(self.preset.canvas_params)
        renderer_cls = self.canvas_type.renderers["tk"]
        self.renderer = renderer_cls(self.canvas_frame, self.canvas, theme=self.theme)
        self.renderer.widget.pack()

        for key, spec in self.preset.inputs.items():
            ctk.CTkLabel(self.input_frame, text=f"{spec.label}:", text_color=self.theme.fg).pack(
                side="left", padx=(8, 2)
            )
            entry = ctk.CTkEntry(self.input_frame, width=64)
            entry.insert(0, str(spec.default))
            entry.pack(side="left", padx=(0, 4))
            self.input_widgets[key] = entry

        self.code_input.delete("1.0", tk.END)
        self.code_input.insert("1.0", self.preset.source)
        self._clear_line_highlight()
        self._log(f"Loaded {self.preset.name}.")

    def _log(self, message: str) -> None:
        self.status.insert(tk.END, message + "\n")
        self.status.see(tk.END)

    def _on_speed_change(self, value) -> None:
        self.playback.delay_ms = int(value)
        self.speed_label.configure(text=str(int(value)))

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
        name = ctk.CTkInputDialog(text="Preset name:", title="Save preset").get_input()
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

    def open_graph_editor(self) -> None:
        GraphEditorView(self.root, theme=self.theme, user_dir=self.user_dir, on_saved=self._on_network_saved)

    def _on_network_saved(self, name: str) -> None:
        self._log(f"Saved network '{name}'.")
        self._reload_preset_list(select=name)


def launch() -> None:
    theme = load_theme("dark")
    ctk.set_appearance_mode("dark" if theme.name == "dark" else "light")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    MainWindow(root, theme=theme)
    root.mainloop()
