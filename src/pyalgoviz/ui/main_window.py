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

import pyalgoviz.canvas_types  # noqa: F401 -- side effect: registers grid/array/graph canvas types
from pyalgoviz.canvas.registry import ParamSpec, all_types as all_canvas_types, get as get_canvas_type
from pyalgoviz.engine.playback import PlaybackState
from pyalgoviz.engine.runner import Runner
from pyalgoviz.plugins import DEFAULT_PLUGINS_DIR, load_all_plugins
from pyalgoviz.ui.graph_editor_view import GraphEditorView
from pyalgoviz.preset_loader import (
    BUNDLED_PRESETS_DIR,
    USER_PRESETS_DIR,
    LoadedPreset,
    load_all_presets,
    write_preset_file,
)
from pyalgoviz.pseudocode.errors import PseudocodeError
from pyalgoviz.pseudocode.interpreter import Interpreter
from pyalgoviz.pseudocode.step_event import StepEvent
from pyalgoviz.theme import DARK, ThemeTokens, load_theme

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
        self.render_scale = 1.0
        self.presentation = False

        if hasattr(self.root, "configure"):
            try:
                self.root.configure(fg_color=self.theme.bg)
            except tk.TclError:
                pass  # root isn't a CTk-aware widget (e.g. a bare tk.Tk in some tests)

        self._build_static_widgets()
        if hasattr(self.root, "bind"):
            self.root.bind("<Escape>", lambda _event: self.exit_presentation())

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

        self.top = ctk.CTkFrame(self.root, fg_color=theme.panel_bg)
        ctk.CTkLabel(self.top, text="Algorithm:", text_color=theme.fg).pack(side="left", padx=(8, 4))
        self.algo_menu = ctk.CTkComboBox(
            self.top, values=[], state="readonly", width=220, command=self._on_algo_selected
        )
        self.algo_menu.pack(side="left")
        ctk.CTkButton(self.top, text="Save preset…", command=self.save_preset, width=110).pack(
            side="left", padx=(8, 4)
        )
        ctk.CTkButton(self.top, text="Update Preset", command=self.update_preset, width=110).pack(
            side="left", padx=(0, 4)
        )
        self.network_button = ctk.CTkButton(self.top, text="New Network…", command=self.open_graph_editor, width=120)
        self.network_button.pack(side="left", padx=(0, 8))

        self.input_frame = ctk.CTkFrame(self.root, fg_color=theme.panel_bg)

        self.code_input = ctk.CTkTextbox(self.root, width=680, height=280)
        self.code_input.tag_config(CURRENT_LINE_TAG, background="#444444", foreground="#ffffff")

        self.controls = ctk.CTkFrame(self.root, fg_color=theme.panel_bg)
        ctk.CTkButton(self.controls, text="Run", command=self.run_code, width=70).pack(
            side="left", padx=4, pady=6
        )
        ctk.CTkButton(self.controls, text="Play", command=self.play, width=70).pack(side="left", padx=4)
        ctk.CTkButton(self.controls, text="Pause", command=self.pause, width=70).pack(side="left", padx=4)
        ctk.CTkButton(self.controls, text="Step", command=self.step, width=70).pack(side="left", padx=4)
        ctk.CTkButton(self.controls, text="Reset", command=self.reset, width=70).pack(side="left", padx=4)
        self.present_button = ctk.CTkButton(
            self.controls, text="Present", command=self.toggle_presentation, width=80
        )
        self.present_button.pack(side="left", padx=(12, 4))
        ctk.CTkButton(self.controls, text="Quit", command=self.root.destroy, width=70).pack(side="left", padx=4)

        ctk.CTkLabel(self.controls, text="Delay (ms/step):", text_color=theme.fg).pack(side="left", padx=(16, 4))
        self.speed_label = ctk.CTkLabel(self.controls, text=str(self.playback.delay_ms), text_color=theme.fg, width=36)
        ctk.CTkSlider(
            self.controls, from_=10, to=500, width=140, command=self._on_speed_change
        ).pack(side="left", padx=4)
        self.speed_label.pack(side="left")

        self.canvas_frame = ctk.CTkFrame(self.root, fg_color=theme.bg)

        # Always visible in both layouts (including presentation mode, where
        # the status log is hidden) -- this is the one place ShowAnswer()
        # output shows up, so it can't be something the user has to dig for.
        self.answer_label = ctk.CTkLabel(
            self.root, text="", text_color=theme.accent, font=ctk.CTkFont(size=16, weight="bold")
        )

        self.status = ctk.CTkTextbox(self.root, width=680, height=110)

        self._layout_normal()

    def _layout_normal(self) -> None:
        widgets = (
            self.top,
            self.input_frame,
            self.code_input,
            self.controls,
            self.canvas_frame,
            self.answer_label,
            self.status,
        )
        for widget in widgets:
            widget.pack_forget()
        self.top.pack(fill="x", padx=8, pady=(8, 4))
        self.input_frame.pack(fill="x", padx=8, pady=4)
        self.code_input.pack(padx=8, pady=4)
        self.controls.pack(fill="x", padx=8, pady=4)
        self.canvas_frame.pack(padx=8, pady=4)
        self.answer_label.pack(padx=8, pady=(0, 4))
        self.status.pack(padx=8, pady=(4, 8))

    def _layout_presentation(self) -> None:
        # Hides everything but the canvas and a minimal playback bar --
        # the code editor, input fields, and status log are noise once
        # you're actually presenting the visualization.
        widgets = (
            self.top,
            self.input_frame,
            self.code_input,
            self.controls,
            self.canvas_frame,
            self.answer_label,
            self.status,
        )
        for widget in widgets:
            widget.pack_forget()
        self.controls.pack(fill="x", padx=8, pady=8)
        self.canvas_frame.pack(expand=True)
        self.answer_label.pack(pady=(0, 8))

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
            self.root.title(f"PyAlgoViz — {self.preset.name}")
        is_network = self.preset.canvas_type_id == "graph" and "nodes" in self.preset.canvas_params
        self.network_button.configure(text="Edit Network…" if is_network else "New Network…")

        for widget in self.input_frame.winfo_children():
            widget.destroy()
        self.input_widgets.clear()

        self.canvas = self.canvas_type.make_canvas(self.preset.canvas_params)
        self._rebuild_renderer()

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
        self._clear_answer()
        self._log(f"Loaded {self.preset.name}.")

    def _rebuild_renderer(self) -> None:
        """Rebuilds just the renderer against the current canvas model at
        `self.render_scale` -- used both for a fresh algorithm load and for
        zooming the same in-progress canvas up/down when presentation mode
        is toggled, without touching canvas/algorithm state.

        A running Runner is paused first: it drives itself via root.after()
        ticks independent of this call, and a tick landing between the old
        widget's destruction and the new renderer's listener registration
        would notify a renderer whose Tk widget no longer exists. Canvas
        listeners are then detached so the about-to-be-destroyed renderer's
        callback doesn't linger on the canvas forever (listener lists are
        append-only, and this method may run more than once per canvas
        instance -- unlike a fresh algorithm load, which always pairs a new
        canvas with a new renderer)."""
        if self.runner is not None:
            self.runner.pause()
        if hasattr(self.canvas, "detach_listeners"):
            self.canvas.detach_listeners()
        for widget in self.canvas_frame.winfo_children():
            widget.destroy()
        renderer_cls = self.canvas_type.renderers["tk"]
        try:
            self.renderer = renderer_cls(self.canvas_frame, self.canvas, theme=self.theme, scale=self.render_scale)
        except TypeError:
            # Third-party/older renderers (e.g. a plugin built before
            # presentation mode existed) may not accept `scale` -- fall
            # back to unscaled instead of crashing the whole app over it.
            self.renderer = renderer_cls(self.canvas_frame, self.canvas, theme=self.theme)
        self.renderer.widget.pack()

    def toggle_presentation(self) -> None:
        if self.presentation:
            self.exit_presentation()
        else:
            self.enter_presentation()

    def enter_presentation(self) -> None:
        if self.presentation or self.renderer is None:
            return
        self.presentation = True
        self.render_scale = self._compute_presentation_scale()
        self._layout_presentation()
        self._rebuild_renderer()
        if hasattr(self.root, "attributes"):
            try:
                self.root.attributes("-fullscreen", True)
            except tk.TclError:
                pass
        self.present_button.configure(text="Exit Presentation")
        self._log("Entered presentation mode — press Esc or Exit Presentation to leave.")

    def exit_presentation(self) -> None:
        if not self.presentation:
            return
        self.presentation = False
        self.render_scale = 1.0
        if hasattr(self.root, "attributes"):
            try:
                self.root.attributes("-fullscreen", False)
            except tk.TclError:
                pass
        self._layout_normal()
        self._rebuild_renderer()
        self.present_button.configure(text="Present")
        self._log("Exited presentation mode.")

    def _compute_presentation_scale(self) -> float:
        natural_w = int(float(self.renderer.widget.cget("width")))
        natural_h = int(float(self.renderer.widget.cget("height")))
        if not hasattr(self.root, "winfo_screenwidth"):
            return 1.0
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        scale = min((screen_w * 0.85) / natural_w, (screen_h * 0.75) / natural_h)
        return max(1.0, min(scale, 4.0))

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
        if event.action == "ShowAnswer" and event.args:
            self._show_answer(event.args)

    def _show_answer(self, args: tuple) -> None:
        if len(args) == 1:
            text = f"Answer: {args[0]}"
        else:
            label, values = args[0], args[1:]
            text = f"{label}: " + ", ".join(str(v) for v in values)
        self.answer_label.configure(text=text)
        self._log(text)

    def _clear_answer(self) -> None:
        self.answer_label.configure(text="")

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
        self._clear_answer()

    def save_preset(self) -> None:
        if self.preset is None:
            return
        name = ctk.CTkInputDialog(text="Preset name:", title="Save preset").get_input()
        if not name:
            return
        self._do_save_preset(name)

    def update_preset(self) -> None:
        """Overwrites the currently loaded preset in place -- no rename
        prompt, unlike save_preset() which always asks for a (possibly new)
        name. _do_save_preset always writes to self.user_dir regardless of
        where the original came from, so updating a bundled preset creates
        a user-dir override rather than touching the packaged file --
        consistent with the existing "user presets win on name collision"
        rule everywhere else presets are loaded."""
        if self.preset is None:
            return
        self._do_save_preset(self.preset.name)

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
        # If the currently loaded preset is itself a custom weighted
        # network (not a maze), open the editor pre-populated with it
        # instead of a blank canvas -- otherwise there'd be no way to
        # rename a node or tweak an edge on a network you already saved.
        existing = None
        if self.preset is not None and self.preset.canvas_type_id == "graph" and "nodes" in self.preset.canvas_params:
            existing = self.preset
        GraphEditorView(
            self.root,
            theme=self.theme,
            user_dir=self.user_dir,
            on_saved=self._on_network_saved,
            existing_preset=existing,
        )

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
