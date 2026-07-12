"""Tk glue for the in-app graph editor: turns mouse clicks on a canvas into
GraphEditorModel calls and redraws from model state after each one. All
actual state logic lives in graph_editor_model.py; every handler here that
does real work is a one-line wrapper around a testable `_do_*` core method
(mirroring MainWindow's save_preset/_do_save_preset split), so a smoke
script can drive the editor end-to-end via synthetic click coordinates
without a real mouse or a blocking dialog in the way.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from typing import Callable

import customtkinter as ctk

from pyalgoviz.preset_loader import LoadedPreset, USER_PRESETS_DIR, write_preset_file
from pyalgoviz.theme import DARK, ThemeTokens, graph_state_color

from .graph_editor_model import GraphEditorModel

NODE_RADIUS = 15

MODE_ADD_NODE = "add_node"
MODE_ADD_EDGE = "add_edge"
MODE_SET_START = "set_start"
MODE_SET_GOAL = "set_goal"
MODE_RENAME = "rename"
MODE_DELETE = "delete"

_MODE_LABELS = {
    MODE_ADD_NODE: "Add Node",
    MODE_ADD_EDGE: "Add Edge",
    MODE_SET_START: "Set Start",
    MODE_SET_GOAL: "Set Goal",
    MODE_RENAME: "Rename",
    MODE_DELETE: "Delete",
}


def _format_weight(value: float) -> str:
    return str(int(value)) if value == int(value) else str(value)


class GraphEditorView(ctk.CTkToplevel):
    def __init__(
        self,
        master: tk.Misc,
        theme: ThemeTokens = DARK,
        user_dir: Path = USER_PRESETS_DIR,
        on_saved: Callable[[str], None] | None = None,
        existing_preset: LoadedPreset | None = None,
    ):
        super().__init__(master)
        self.theme = theme
        self.user_dir = user_dir
        self.on_saved = on_saved
        self._editing_name = existing_preset.name if existing_preset is not None else None
        self.model = GraphEditorModel.from_preset(existing_preset) if existing_preset is not None else GraphEditorModel()
        self.title(f"Network editor — editing '{self._editing_name}'" if self._editing_name else "Network editor — new network")
        self.mode = MODE_ADD_NODE
        self._pending_edge_source: int | None = None
        self._mode_buttons: dict[str, ctk.CTkButton] = {}
        self._build_widgets()
        self._redraw()  # shows any hydrated nodes/edges immediately, not just after the first click

    def _build_widgets(self) -> None:
        theme = self.theme
        toolbar = ctk.CTkFrame(self, fg_color=theme.panel_bg)
        toolbar.pack(fill="x", padx=8, pady=8)

        for mode, label in _MODE_LABELS.items():
            btn = ctk.CTkButton(toolbar, text=label, width=90, command=lambda m=mode: self.set_mode(m))
            btn.pack(side="left", padx=4)
            self._mode_buttons[mode] = btn
        self._default_button_color = next(iter(self._mode_buttons.values())).cget("fg_color")

        if self._editing_name is not None:
            ctk.CTkButton(
                toolbar, text=f"Update '{self._editing_name}'", command=self.update_existing, width=140
            ).pack(side="right", padx=4)
        ctk.CTkButton(toolbar, text="Save as Preset…", command=self.save, width=130).pack(side="right", padx=4)

        self.status_label = ctk.CTkLabel(self, text="", text_color=theme.fg)
        self.status_label.pack(fill="x", padx=8)

        self.canvas = tk.Canvas(
            self, width=700, height=460, background=theme.graph_background, highlightthickness=0
        )
        self.canvas.pack(padx=8, pady=8)
        self.canvas.bind("<Button-1>", self._on_click)

        self.set_mode(MODE_ADD_NODE)

    # -- mode / status -------------------------------------------------

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self._pending_edge_source = None
        for m, btn in self._mode_buttons.items():
            btn.configure(fg_color=self.theme.accent if m == mode else self._default_button_color)
        self._set_status(f"Mode: {_MODE_LABELS[mode]}")

    def _set_status(self, text: str) -> None:
        self.status_label.configure(text=text)

    # -- click dispatch --------------------------------------------------

    def _on_click(self, event: tk.Event) -> None:
        x, y = event.x, event.y
        if self.mode == MODE_ADD_NODE:
            self._on_click_add_node(x, y)
        elif self.mode == MODE_ADD_EDGE:
            self._on_click_add_edge(x, y)
        elif self.mode == MODE_SET_START:
            hit = self.model.node_near(x, y)
            if hit is not None:
                self.model.set_start(hit)
                self._redraw()
        elif self.mode == MODE_SET_GOAL:
            hit = self.model.node_near(x, y)
            if hit is not None:
                self.model.set_goal(hit)
                self._redraw()
        elif self.mode == MODE_RENAME:
            self._on_click_rename(x, y)
        elif self.mode == MODE_DELETE:
            self._on_click_delete(x, y)

    def _on_click_add_node(self, x: int, y: int) -> None:
        if self.model.node_near(x, y) is not None:
            return  # clicking an existing node in Add Node mode is a no-op
        self.model.add_node(x, y)
        self._redraw()

    def _on_click_add_edge(self, x: int, y: int) -> None:
        hit = self.model.node_near(x, y)
        if hit is None:
            return
        if self._pending_edge_source is None:
            self._pending_edge_source = hit
            self._set_status(f"Edge from node {hit} — click the other node")
            return
        source = self._pending_edge_source
        self._pending_edge_source = None
        if hit == source:
            self._set_status("Cancelled (same node clicked twice)")
            return
        raw = ctk.CTkInputDialog(text="Edge weight:", title="Weight").get_input()
        weight = _parse_weight(raw)
        if weight is None:
            self._set_status("Cancelled — invalid or empty weight")
            return
        self._do_connect(source, hit, weight)

    def _do_connect(self, source: int, target: int, weight: float) -> None:
        """Testable core of edge creation: bypasses the blocking weight
        prompt so a smoke script can drive it directly."""
        self.model.connect(source, target, weight=weight)
        self._set_status(f"Connected {source} <-> {target} (weight {weight})")
        self._redraw()

    def _on_click_rename(self, x: int, y: int) -> None:
        hit = self.model.node_near(x, y)
        if hit is None:
            return
        current = self.model.nodes[hit].label
        raw = ctk.CTkInputDialog(
            text=f"New name for node {hit} (currently '{current or hit}'). Any name is fine:",
            title="Rename node",
        ).get_input()
        if raw is None:
            self._set_status("Cancelled")
            return
        self._do_rename(hit, raw)

    def _do_rename(self, node_id: int, label: str) -> None:
        """Testable core of renaming: bypasses the blocking name prompt so
        a smoke script can drive it directly. `label` can be any string --
        including empty, which falls back to the node's id when displayed."""
        self.model.rename_node(node_id, label)
        self._set_status(f"Renamed node {node_id} to '{label}'" if label else f"Cleared node {node_id}'s name")
        self._redraw()

    def _on_click_delete(self, x: int, y: int) -> None:
        node_hit = self.model.node_near(x, y)
        if node_hit is not None:
            self.model.remove_node(node_hit)
            self._redraw()
            return
        edge_hit = self.model.edge_near(x, y)
        if edge_hit is not None:
            self.model.disconnect(edge_hit.a, edge_hit.b)
            self._redraw()

    # -- rendering --------------------------------------------------------

    def _redraw(self) -> None:
        self.canvas.delete("all")
        theme = self.theme

        for e in self.model.edges:
            na, nb = self.model.nodes[e.a], self.model.nodes[e.b]
            self.canvas.create_line(na.x, na.y, nb.x, nb.y, fill=theme.graph_edge, width=2)
            mx, my = (na.x + nb.x) / 2, (na.y + nb.y) / 2
            self.canvas.create_rectangle(mx - 12, my - 9, mx + 12, my + 9, fill=theme.panel_bg, outline="")
            self.canvas.create_text(mx, my, text=_format_weight(e.weight), fill=theme.fg, font=("TkDefaultFont", 9))

        for n in self.model.nodes.values():
            if n.id == self.model.start:
                state = "start"
            elif n.id == self.model.goal:
                state = "goal"
            else:
                state = "default"
            color = graph_state_color(theme, state)
            self.canvas.create_oval(
                n.x - NODE_RADIUS,
                n.y - NODE_RADIUS,
                n.x + NODE_RADIUS,
                n.y + NODE_RADIUS,
                fill=color,
                outline=theme.graph_background,
                width=2,
            )
            label = n.label or str(n.id)
            self.canvas.create_text(
                n.x, n.y + NODE_RADIUS + 10, text=label, fill=theme.fg, font=("TkDefaultFont", 9)
            )

    # -- save ------------------------------------------------------------

    def save(self) -> None:
        ok, reason = self.model.validate()
        if not ok:
            self._set_status(f"Cannot save: {reason}")
            return
        name = ctk.CTkInputDialog(text="Preset name:", title="Save network").get_input()
        if not name:
            return
        path = self._do_save(name)
        if path is not None:
            self.destroy()

    def update_existing(self) -> None:
        """Overwrites the network preset this editor was opened to edit, in
        place -- no name prompt. Only available when the editor was opened
        via an existing preset (see MainWindow.open_graph_editor), mirroring
        MainWindow's own save_preset/update_preset split."""
        if self._editing_name is None:
            return
        path = self._do_save(self._editing_name)
        if path is not None:
            self.destroy()

    def _do_save(self, name: str) -> Path | None:
        """Testable core of saving: bypasses the blocking name prompt (and
        doesn't close the window), so a smoke script or test can drive it
        directly and inspect what was written."""
        ok, reason = self.model.validate()
        if not ok:
            self._set_status(f"Cannot save: {reason}")
            return None
        preset = self.model.to_preset(name)
        path = write_preset_file(preset, directory=self.user_dir)
        self._set_status(f"Saved '{name}' to {path}")
        if self.on_saved:
            self.on_saved(name)
        return path


def _parse_weight(raw: str | None) -> float | None:
    if raw is None or raw.strip() == "":
        return None
    try:
        return float(raw)
    except ValueError:
        return None
