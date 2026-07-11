"""Tkinter shell: algorithm picker + pseudocode editor + canvas + playback
controls. Switches canvas/renderer/input fields based on the selected
AlgorithmPreset (see presets.py).
"""

from __future__ import annotations

import tkinter as tk
from tkinter import scrolledtext, ttk

from algoviz.engine.playback import PlaybackState
from algoviz.engine.runner import Runner
from algoviz.pseudocode.errors import PseudocodeError
from algoviz.pseudocode.interpreter import Interpreter
from algoviz.pseudocode.step_event import StepEvent
from algoviz.ui.presets import PRESETS

CURRENT_LINE_TAG = "current_line"
CURRENT_LINE_BG = "#444444"
CURRENT_LINE_FG = "#ffffff"


class MainWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.playback = PlaybackState(delay_ms=40)
        self.runner: Runner | None = None
        self.canvas = None
        self.renderer = None
        self.preset = None
        self.entries: dict[str, tk.Entry] = {}

        self._build_static_widgets()
        self.algo_var.set(next(iter(PRESETS)))
        self._load_algorithm()

    def _build_static_widgets(self) -> None:
        top = tk.Frame(self.root)
        top.pack(fill="x")
        tk.Label(top, text="Algorithm:").pack(side="left")
        self.algo_var = tk.StringVar()
        self.algo_menu = ttk.Combobox(
            top, textvariable=self.algo_var, values=list(PRESETS), state="readonly", width=20
        )
        self.algo_menu.pack(side="left")
        self.algo_menu.bind("<<ComboboxSelected>>", lambda _event: self._load_algorithm())

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

    def _load_algorithm(self) -> None:
        if self.runner is not None:
            self.runner.pause()
        self.runner = None

        self.preset = PRESETS[self.algo_var.get()]
        self.root.title(f"AlgoViz — {self.preset.name}")

        for widget in self.canvas_frame.winfo_children():
            widget.destroy()
        for widget in self.input_frame.winfo_children():
            widget.destroy()
        self.entries.clear()

        self.canvas, renderer_cls = self.preset.build()
        self.renderer = renderer_cls(self.canvas_frame, self.canvas)
        self.renderer.widget.pack()

        default_env = self.preset.initial_env()
        for key in self.preset.input_fields:
            tk.Label(self.input_frame, text=f"{key}:").pack(side="left")
            entry = tk.Entry(self.input_frame, width=5)
            entry.insert(0, str(default_env.get(key, "")))
            entry.pack(side="left")
            self.entries[key] = entry

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
        env = dict(self.preset.initial_env())
        try:
            for key, entry in self.entries.items():
                env[key] = int(entry.get())
        except ValueError:
            self._log("Invalid input: fields must be integers.")
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
            interpreter = Interpreter(source, self.canvas)
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


def launch() -> None:
    root = tk.Tk()
    MainWindow(root)
    root.mainloop()
