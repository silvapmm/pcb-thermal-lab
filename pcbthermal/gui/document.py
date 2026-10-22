"""!
@file document.py
@brief The document model of the GUI: a Project with undo/redo, element editing and file I/O.

The GUI works in millimetres and 0-based layers on screen, while the Problem stores metres. The
conversion between the two happens in this module, so the rest of the GUI rarely deals with SI units.
"""

import copy
import os

import numpy as np
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QUndoCommand, QUndoStack

from .. import defaults
from ..api import SolverOptions, default_options
from ..model import Dielectric, Heater, Problem, Heatsink, Via, Zone, new_problem, via_fill_k
from ..project import Project, load_project, project_from_dict, project_to_dict, save_project

KINDS = ("zone", "heater", "heatsink", "via")
_LISTS = {"zone": "zones", "heater": "heaters", "heatsink": "heatsinks", "via": "vias"}


class _SnapshotCommand(QUndoCommand):
    """!
    @brief Undo command that swaps whole-project snapshots (simple and always consistent).
    """

    def __init__(self, doc, text, before, after, merge_key=None):
        """!
        @param doc Owning Document.
        @param text Text shown in the Edit menu.
        @param before Snapshot dict before the edit.
        @param after Snapshot dict after the edit.
        @param merge_key Commands with the same key merge into one (typing in a spin box).
        """
        super().__init__(text)
        self.doc, self.before, self.after = doc, before, after
        self._key = (hash(merge_key) & 0x7FFFFFFF) if merge_key else -1
        self._first = True

    def id(self):
        """!
        @brief Merge identifier (-1 disables merging).
        @return int.
        """
        return self._key

    def mergeWith(self, other):
        """!
        @brief Merge a following command with the same key into this one.
        @param other The newer command.
        @return True if merged.
        """
        if self._key == -1 or other.id() != self._key:
            return False
        self.after = other.after
        return True

    def redo(self):
        """!
        @brief Apply the "after" snapshot (the first call is skipped: the edit is already applied).
        """
        if self._first:
            self._first = False
            return
        self.doc._restore(self.after)

    def undo(self):
        """!
        @brief Apply the "before" snapshot.
        """
        self.doc._restore(self.before)


class Document(QObject):
    """!
    @brief Holds the Project being edited and notifies the views when it changes.
    """

    changed = Signal()          # The problem or the options changed (views must refresh)
    state_changed = Signal()    # File name or modified flag changed (window title)

    def __init__(self, project=None):
        """!
        @param project Initial Project (default: an empty 100 x 80 mm, 2-layer board).
        """
        super().__init__()
        self.project = project or Project(problem=new_problem(), options=default_options())
        self.path = None
        self.stack = QUndoStack(self)
        self.stack.cleanChanged.connect(self._clean_changed)

    def _clean_changed(self, _clean):
        """!
        @brief Forward the undo stack clean flag (ignored while the document is being destroyed).
        @param _clean New clean state.
        """
        try:
            self.state_changed.emit()
        except RuntimeError:
            pass

    # ------------------------------------------------------------------ state
    @property
    def problem(self):
        """!
        @brief The Problem being edited.
        @return Problem.
        """
        return self.project.problem

    @property
    def options(self):
        """!
        @brief The solver options of the project.
        @return SolverOptions.
        """
        return self.project.options

    @property
    def modified(self):
        """!
        @brief True if there are unsaved edits.
        @return bool.
        """
        return not self.stack.isClean()

    @property
    def title(self):
        """!
        @brief File name or "untitled".
        @return str.
        """
        return os.path.basename(self.path) if self.path else self.problem.name

    def snapshot(self):
        """!
        @brief Serialise the whole project.
        @return Dict.
        """
        return copy.deepcopy(project_to_dict(self.project))

    def _restore(self, snap):
        """!
        @brief Replace the project by a snapshot (used by undo and redo).
        @param snap Snapshot dict.
        """
        self.project = project_from_dict(copy.deepcopy(snap), validate=False)
        self.changed.emit()

    def _set_project(self, project, path):
        """!
        @brief Replace the project and clear the undo history.
        @param project New Project.
        @param path Its file path or None.
        """
        self.project, self.path = project, path
        self.stack.clear()
        self.stack.setClean()
        self.changed.emit()
        self.state_changed.emit()

    # ------------------------------------------------------------------ generic edit
    def edit(self, text, mutator, merge_key=None):
        """!
        @brief Apply a change to the project as one undoable step.
        @param text Description for the Edit menu.
        @param mutator Callable(project) that modifies the project in place.
        @param merge_key Optional key to merge consecutive similar edits.
        """
        before = self.snapshot()
        mutator(self.project)
        after = self.snapshot()
        if before == after:
            return
        self.stack.push(_SnapshotCommand(self, text, before, after, merge_key))
        self.changed.emit()

    # ------------------------------------------------------------------ files
    def new(self, width_mm=None, height_mm=None, layers=None):
        """!
        @brief Start an empty board.
        @param width_mm Width in mm (default: the default of a new board).
        @param height_mm Height in mm (default: the default of a new board).
        @param layers Number of copper layers (default: the default of a new board).
        """
        self._set_project(Project(problem=new_problem(width_mm, height_mm, layers), options=default_options()), None)

    def open(self, path):
        """!
        @brief Load a project file (native, project or legacy editor JSON).
        @param path File path.
        """
        self._set_project(load_project(path), path if not path.endswith("legacy") else None)

    def open_problem(self, problem, name=None):
        """!
        @brief Use a ready Problem (for example an example board) as a new unsaved document.
        @param problem The Problem.
        @param name Optional project name.
        """
        if name:
            problem.name = name
        self._set_project(Project(problem=problem), None)

    def save(self, path=None):
        """!
        @brief Save the project.
        @param path Target path (default: the current path).
        @throws ValueError If no path is known.
        """
        path = path or self.path
        if not path:
            raise ValueError("no file name")
        save_project(path, self.project)
        self.path = path
        self.problem.name = os.path.basename(path).replace(".pcbt.json", "").replace(".json", "")
        self.stack.setClean()
        self.state_changed.emit()

    # ------------------------------------------------------------------ elements (mm on screen)
    def _items(self, kind):
        """!
        @brief The element list of a kind.
        @param kind One of KINDS.
        @return list.
        """
        return getattr(self.problem, _LISTS[kind])

    def count(self, kind):
        """!
        @brief Number of elements of a kind.
        @param kind One of KINDS.
        @return int.
        """
        return len(self._items(kind))

    @staticmethod
    def polygon_mm(element):
        """!
        @brief Polygon of an element in millimetres.
        @param element Zone, Heater or Heatsink.
        @return Array (n, 2).
        """
        return np.asarray(element.polygon) * 1000.0

    def add_shape(self, kind, layer, polygon_mm):
        """!
        @brief Create a zone, heater or heatsink from a polygon in millimetres.
        @param kind "zone", "heater" or "heatsink".
        @param layer 0-based layer.
        @param polygon_mm Array-like (n, 2) in mm.
        @return Index of the new element.
        """
        poly = np.asarray(polygon_mm, dtype=float) / 1000.0
        n = self.count(kind) + 1

        def mutate(proj):
            pr = proj.problem
            new = defaults.load()["new_elements"]                              # The user's defaults for a new element
            if kind == "zone":
                pr.zones.append(Zone(layer, poly, new["zone_fill"], f"Zone {n}"))
            elif kind == "heater":
                pr.heaters.append(Heater(layer, poly, new["heater_power_w"], f"U{n}", role=new.get("heater_kind", "source")))
            else:
                last = pr.board.layers - 1
                pr.heatsinks.append(Heatsink(last if layer != 0 else 0, poly, new["heatsink_h_extra"], f"Heatsink {n}"))

        self.edit(f"Add {kind}", mutate)
        return self.count(kind) - 1

    def add_via(self, x_mm, y_mm, diameter_mm=None):
        """!
        @brief Place a via with the default fill.
        @param x_mm X in mm.
        @param y_mm Y in mm.
        @param diameter_mm Hole diameter in mm (default: the default via diameter).
        @return Index of the new via.
        """
        new = defaults.load()["new_elements"]
        d = diameter_mm if diameter_mm is not None else new["via_diameter_mm"]
        fill = new["via_fill"]
        self.edit("Add via", lambda proj: proj.problem.vias.append(
            Via(x_mm / 1000.0, y_mm / 1000.0, d / 1000.0, False, f"V{len(proj.problem.vias) + 1}", via_fill_k(fill), fill)))
        return self.count("via") - 1

    def set_polygon(self, kind, index, polygon_mm):
        """!
        @brief Replace the polygon of an element.
        @param kind "zone", "heater" or "heatsink".
        @param index Element index.
        @param polygon_mm New vertices in mm.
        """
        poly = np.asarray(polygon_mm, dtype=float) / 1000.0
        self.edit("Edit shape", lambda proj: setattr(getattr(proj.problem, _LISTS[kind])[index], "polygon", poly))

    def set_outline(self, polygon_mm):
        """!
        @brief Give the board an outline polygon, or restore the full rectangle.
        @param polygon_mm Vertices in mm inside the board box, or None for the rectangle.
        """
        poly = None if polygon_mm is None else np.asarray(polygon_mm, dtype=float) / 1000.0
        self.edit("Board outline", lambda proj: setattr(proj.problem.board, "outline", poly))

    def set_props(self, kind, index, text="Edit properties", merge=True, **props):
        """!
        @brief Change attributes of one element (SI units for physical values, see the element classes).
        @param kind Element kind.
        @param index Element index.
        @param text Undo text.
        @param merge If True, repeated edits of the same property merge into one undo step.
        @param props Attribute names and new values.
        """
        def mutate(proj):
            el = getattr(proj.problem, _LISTS[kind])[index]
            for k, v in props.items():
                setattr(el, k, v)

        self.edit(text, mutate, merge_key=f"{kind}{index}{sorted(props)}" if merge else None)

    def delete(self, selection):
        """!
        @brief Delete the selected elements.
        @param selection Iterable of (kind, index).
        """
        sel = sorted(set(selection), key=lambda s: -s[1])

        def mutate(proj):
            for kind, idx in sel:
                lst = getattr(proj.problem, _LISTS[kind])
                if 0 <= idx < len(lst):
                    del lst[idx]

        if sel:
            self.edit("Delete", mutate)

    def duplicate(self, selection, offset_mm=(5.0, 5.0)):
        """!
        @brief Duplicate the selected elements, shifted by an offset.
        @param selection Iterable of (kind, index).
        @param offset_mm Shift (dx, dy) in mm.
        @return List of (kind, index) of the copies.
        """
        sel = list(selection)
        dx, dy = offset_mm[0] / 1000.0, offset_mm[1] / 1000.0
        created = []

        def mutate(proj):
            for kind, idx in sel:
                lst = getattr(proj.problem, _LISTS[kind])
                el = copy.deepcopy(lst[idx])
                if hasattr(el, "polygon"):
                    el.polygon = np.asarray(el.polygon) + np.array([dx, dy])
                else:
                    el.x, el.y = el.x + dx, el.y + dy
                if el.name:
                    el.name += " copy"
                lst.append(el)
                created.append((kind, len(lst) - 1))

        if sel:
            self.edit("Duplicate", mutate)
        return created

    def move(self, selection, dx_mm, dy_mm):
        """!
        @brief Translate the selected elements.
        @param selection Iterable of (kind, index).
        @param dx_mm Shift along x in mm.
        @param dy_mm Shift along y in mm.
        """
        sel = list(selection)
        d = np.array([dx_mm, dy_mm]) / 1000.0
        # Keep the whole selection inside the board: the shift is limited so no element crosses the edge
        b = self.problem.board
        lo, hi = np.array([np.inf, np.inf]), np.array([-np.inf, -np.inf])
        for kind, idx in sel:
            el = getattr(self.problem, _LISTS[kind])[idx]
            pts = np.asarray(el.polygon) if hasattr(el, "polygon") else np.array([[el.x, el.y]])
            lo, hi = np.minimum(lo, pts.min(axis=0)), np.maximum(hi, pts.max(axis=0))
        if sel:
            d = np.clip(d, -lo, np.array([b.width, b.height]) - hi) if np.all(lo >= -1e-12) and np.all(hi <= np.array([b.width, b.height]) + 1e-12) else d
            dx_mm, dy_mm = d * 1000.0

        def mutate(proj):
            for kind, idx in sel:
                el = getattr(proj.problem, _LISTS[kind])[idx]
                if hasattr(el, "polygon"):
                    el.polygon = np.asarray(el.polygon) + d
                else:
                    el.x, el.y = el.x + d[0], el.y + d[1]

        if sel and (dx_mm or dy_mm):
            self.edit("Move", mutate)

    # ------------------------------------------------------------------ board and options
    def edit_board(self, text="Board parameters", **fields):
        """!
        @brief Change board attributes (SI units; see the Board class).
        @param text Undo text.
        @param fields Board attribute names and values.
        """
        def mutate(proj):
            for k, v in fields.items():
                setattr(proj.problem.board, k, v)

        self.edit(text, mutate, merge_key="board" + str(sorted(fields)))

    def set_layers(self, n, template=True):
        """!
        @brief Change the layer count, moving elements that fall outside onto the last layer, and load the typical stack-up of the new count.
        @param n New number of layers (1..12).
        @param template True to load the typical stack-up of `n` layers (copper, dielectrics, thickness; see Board.apply_template); False to keep the old values.
        """
        def mutate(proj):
            pr = proj.problem
            b = pr.board
            old = b.layers
            t = b.copper_thickness[0] if b.copper_thickness else 35e-6
            b.copper_thickness = (list(b.copper_thickness) + [t] * n)[:n]
            if b.dielectrics is not None:                      # Advanced stack-up: keep one dielectric per gap (new gaps copy the last one)
                last = copy.deepcopy(b.dielectrics[-1]) if b.dielectrics else Dielectric()
                b.dielectrics = (list(b.dielectrics) + [copy.deepcopy(last) for _ in range(n)])[:max(n - 1, 0)]
                b.layers = n
                b.thickness = b.total_thickness()
            b.layers = n
            for lst in (pr.zones, pr.heaters):
                for e in lst:
                    e.layer = min(e.layer, n - 1)
            for s in pr.heatsinks:
                s.layer = n - 1 if s.layer == old - 1 or s.layer >= n else 0
            if template:
                b.apply_template()

        self.edit("Layer count", mutate)

    def load_typical_stackup(self):
        """!
        @brief Replace the copper and the dielectrics by the typical stack-up of the current number of layers (undoable).
        """
        self.edit("Typical stack-up", lambda proj: proj.problem.board.apply_template())

    def set_options(self, **fields):
        """!
        @brief Change solver options (not part of the undo history).
        @param fields SolverOptions attribute names and values.
        """
        for k, v in fields.items():
            setattr(self.options, k, v)
        self.state_changed.emit()
