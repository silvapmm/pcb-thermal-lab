"""!
@file panels.py
@brief Side panels: board parameters, element list, inspector and solver settings.
"""

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox,
                               QHBoxLayout, QLabel, QLineEdit, QMenu, QProgressBar, QPushButton, QSpinBox,
                               QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from ..api import suggest_cell_mm
from .document import KINDS

_TITLES = {"zone": "Zones", "heater": "Heaters", "sink": "Sinks", "via": "Vias"}


def _spin(lo, hi, value=0.0, decimals=2, step=0.1, suffix=""):
    """!
    @brief Create a configured QDoubleSpinBox.
    @param lo Minimum.
    @param hi Maximum.
    @param value Initial value.
    @param decimals Decimals shown.
    @param step Single step.
    @param suffix Unit suffix shown after the number.
    @return QDoubleSpinBox.
    """
    s = QDoubleSpinBox()
    s.setRange(lo, hi)
    s.setDecimals(decimals)
    s.setSingleStep(step)
    s.setValue(value)
    s.setKeyboardTracking(False)
    if suffix:
        s.setSuffix(" " + suffix)
    return s


class BoardPanel(QWidget):
    """!
    @brief Board size, stack-up, environment and materials.
    """

    def __init__(self, doc, parent=None):
        """!
        @param doc The Document.
        @param parent Qt parent.
        """
        super().__init__(parent)
        self.doc, self._updating = doc, False
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)

        g = QGroupBox("Board")
        f = QFormLayout(g)
        self.width = _spin(5, 1000, 100, 1, 1, "mm")
        self.height = _spin(5, 1000, 80, 1, 1, "mm")
        self.thickness = _spin(0.2, 10, 1.6, 2, 0.1, "mm")
        self.layers = QSpinBox()
        self.layers.setRange(1, 12)
        self.copper = _spin(5, 210, 35, 1, 5, "µm")
        for label, w in (("Width", self.width), ("Height", self.height), ("Thickness", self.thickness),
                         ("Copper layers", self.layers), ("Copper per layer", self.copper)):
            f.addRow(label, w)
        lay.addWidget(g)

        g = QGroupBox("Environment")
        f = QFormLayout(g)
        self.ambient = _spin(-60, 200, 25, 1, 1, "°C")
        self.h_top = _spin(0, 500, 10, 1, 1, "W/m²K")
        self.h_bottom = _spin(0, 500, 15, 1, 1, "W/m²K")
        self.side_on = QCheckBox("Edges lose heat")
        self.h_side = _spin(0, 500, 10, 1, 1, "W/m²K")
        for label, w in (("Ambient", self.ambient), ("h top", self.h_top), ("h bottom", self.h_bottom),
                         ("", self.side_on), ("h edges", self.h_side)):
            f.addRow(label, w)
        lay.addWidget(g)

        g = QGroupBox("Materials")
        f = QFormLayout(g)
        self.k_cu = _spin(1, 1000, 385, 0, 5, "W/mK")
        self.k_th = _spin(0.05, 20, 0.3, 2, 0.05, "W/mK")
        self.k_ip = _spin(0.05, 20, 0.9, 2, 0.05, "W/mK")
        self.plating = _spin(1, 200, 25, 0, 1, "µm")
        for label, w in (("Copper k", self.k_cu), ("FR-4 k through", self.k_th), ("FR-4 k in-plane", self.k_ip),
                         ("Via plating", self.plating)):
            f.addRow(label, w)
        lay.addWidget(g)
        lay.addStretch(1)

        for w in (self.width, self.height, self.thickness, self.copper, self.ambient, self.h_top,
                  self.h_bottom, self.h_side, self.k_cu, self.k_th, self.k_ip, self.plating):
            w.valueChanged.connect(self._apply)
        self.layers.valueChanged.connect(self._apply_layers)
        self.side_on.toggled.connect(self._apply)
        doc.changed.connect(self.refresh)
        self.refresh()

    def refresh(self):
        """!
        @brief Load the values from the document without triggering edits.
        """
        b = self.doc.problem.board
        m = b.materials
        self._updating = True
        self.width.setValue(b.width * 1000)
        self.height.setValue(b.height * 1000)
        self.thickness.setValue(b.thickness * 1000)
        self.layers.setValue(b.layers)
        self.copper.setValue(b.copper_thickness[0] * 1e6)
        self.ambient.setValue(b.ambient)
        self.h_top.setValue(b.h_top)
        self.h_bottom.setValue(b.h_bottom)
        self.side_on.setChecked(b.h_side is not None)
        self.h_side.setValue(b.h_side or 10.0)
        self.h_side.setEnabled(b.h_side is not None)
        self.k_cu.setValue(m.k_copper)
        self.k_th.setValue(m.k_fr4_through)
        self.k_ip.setValue(m.k_fr4_inplane)
        self.plating.setValue(b.via_plating * 1e6)
        self._updating = False

    def _apply(self, *_):
        """!
        @brief Write the control values to the document.
        @param _ Ignored (extra arguments of the Qt signal).
        """
        if self._updating:
            return
        b = self.doc.problem.board
        self.h_side.setEnabled(self.side_on.isChecked())

        def mutate(project):
            bd = project.problem.board
            bd.width, bd.height = self.width.value() / 1000, self.height.value() / 1000
            bd.thickness = self.thickness.value() / 1000
            bd.copper_thickness = [self.copper.value() * 1e-6] * bd.layers
            bd.ambient, bd.h_top, bd.h_bottom = self.ambient.value(), self.h_top.value(), self.h_bottom.value()
            bd.h_side = self.h_side.value() if self.side_on.isChecked() else None
            bd.via_plating = self.plating.value() * 1e-6
            bd.materials.k_copper, bd.materials.k_fr4_through = self.k_cu.value(), self.k_th.value()
            bd.materials.k_fr4_inplane = self.k_ip.value()

        self.doc.edit("Board parameters", mutate, merge_key="board")

    def _apply_layers(self, n):
        """!
        @brief Change the number of layers.
        @param n New layer count.
        """
        if not self._updating and n != self.doc.problem.board.layers:
            self.doc.set_layers(n)


class ElementList(QWidget):
    """!
    @brief Tree of all elements, kept in sync with the canvas selection.
    """

    selection_requested = Signal(list)

    def __init__(self, doc, parent=None):
        """!
        @param doc The Document.
        @param parent Qt parent.
        """
        super().__init__(parent)
        self.doc, self._updating = doc, False
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Element", "Layer", "Value"])
        self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tree.setRootIsDecorated(True)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._menu)
        self.tree.itemSelectionChanged.connect(self._on_selection)
        lay.addWidget(self.tree)
        doc.changed.connect(self.refresh)
        self.refresh()

    def refresh(self):
        """!
        @brief Rebuild the tree from the document, keeping the selection.
        """
        sel = set(self.selected())
        self._updating = True
        self.tree.clear()
        pr = self.doc.problem
        for kind in KINDS:
            lst = getattr(pr, {"zone": "zones", "heater": "heaters", "sink": "sinks", "via": "vias"}[kind])
            top = QTreeWidgetItem([f"{_TITLES[kind]} ({len(lst)})"])
            top.setFlags(top.flags() & ~Qt.ItemIsSelectable)
            self.tree.addTopLevelItem(top)
            for i, el in enumerate(lst):
                if kind == "via":
                    row = [el.name or f"V{i + 1}", "all", f"Ø {el.diameter * 1000:.2f} mm"]
                else:
                    # Only the attribute of this kind exists, so pick it explicitly
                    if kind == "zone":
                        value = f"fill {el.fill:.2f}"
                    elif kind == "heater":
                        value = f"{el.power:.2f} W"
                    else:
                        value = f"+{el.h_extra:g} W/m²K"
                    row = [el.name or f"{kind} {i + 1}", str(el.layer + 1), value]
                child = QTreeWidgetItem(row)
                child.setData(0, Qt.UserRole, (kind, i))
                top.addChild(child)
                if (kind, i) in sel:
                    child.setSelected(True)
            top.setExpanded(len(lst) <= 12)
        for c in range(3):
            self.tree.resizeColumnToContents(c)
        self._updating = False

    def selected(self):
        """!
        @brief Selected elements.
        @return List of (kind, index).
        """
        return [it.data(0, Qt.UserRole) for it in self.tree.selectedItems() if it.data(0, Qt.UserRole)]

    def set_selected(self, items):
        """!
        @brief Select elements without sending a request back to the canvas.
        @param items Iterable of (kind, index).
        """
        want = set(items)
        self._updating = True
        self.tree.clearSelection()
        for t in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(t)
            for c in range(top.childCount()):
                ch = top.child(c)
                if ch.data(0, Qt.UserRole) in want:
                    ch.setSelected(True)
        self._updating = False

    def _on_selection(self):
        """!
        @brief Ask the canvas to select what the user clicked in the list.
        """
        if not self._updating:
            self.selection_requested.emit(self.selected())

    def _menu(self, pos):
        """!
        @brief Context menu with duplicate and delete.
        @param pos Click position in the tree.
        """
        sel = self.selected()
        if not sel:
            return
        m = QMenu(self)
        m.addAction("Duplicate", lambda: self.doc.duplicate(sel))
        m.addAction("Delete", lambda: self.doc.delete(sel))
        m.exec(self.tree.viewport().mapToGlobal(pos))


class Inspector(QWidget):
    """!
    @brief Property editor of the selected element.
    """

    def __init__(self, doc, parent=None):
        """!
        @param doc The Document.
        @param parent Qt parent.
        """
        super().__init__(parent)
        self.doc, self.selection, self._updating = doc, [], False
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(8, 8, 8, 8)
        self.form_host = QWidget()
        self.lay.addWidget(self.form_host)
        self.lay.addStretch(1)
        doc.changed.connect(self.rebuild)
        self.rebuild()

    def set_selection(self, items):
        """!
        @brief Show the properties of a selection.
        @param items List of (kind, index).
        """
        self.selection = list(items)
        self.rebuild()

    def rebuild(self):
        """!
        @brief Rebuild the form for the current selection and the current document values.
        """
        self._updating = True
        old = self.form_host
        self.form_host = QWidget()
        self.lay.replaceWidget(old, self.form_host)
        old.hide()
        old.deleteLater()
        lay = QFormLayout(self.form_host)
        lay.setContentsMargins(0, 0, 0, 0)
        pr = self.doc.problem
        valid = [(k, i) for k, i in self.selection if i < self.doc.count(k)]
        if not valid:
            lbl = QLabel("Select an element on the board or in the list to edit its properties.")
            lbl.setWordWrap(True)
            lbl.setEnabled(False)
            lay.addRow(lbl)
        elif len(valid) > 1:
            lay.addRow(QLabel(f"{len(valid)} elements selected"))
            movable = [(k, i) for k, i in valid if k in ("zone", "heater")]
            if movable:
                combo = self._layer_combo(None)
                combo.currentIndexChanged.connect(lambda idx, m=movable: self._set_layers(m, idx))
                lay.addRow("Move to layer", combo)
        else:
            kind, i = valid[0]
            el = getattr(pr, {"zone": "zones", "heater": "heaters", "sink": "sinks", "via": "vias"}[kind])[i]
            title = QLabel(f"<b>{kind.capitalize()}</b>")
            lay.addRow(title)
            name = QLineEdit(el.name)
            name.editingFinished.connect(lambda: self.doc.set_props(kind, i, "Rename", name=name.text()))
            lay.addRow("Name", name)
            if kind != "via":
                lay.addRow("Layer", self._layer_combo(el.layer, outer_only=(kind == "sink"),
                                                       cb=lambda idx: self._set_layers([(kind, i)], idx)))
            if kind == "zone":
                w = _spin(0, 1, el.fill, 2, 0.05)
                w.valueChanged.connect(lambda v: self.doc.set_props(kind, i, fill=v))
                lay.addRow("Copper fill", w)
            elif kind == "heater":
                w = _spin(0, 1000, el.power, 3, 0.1, "W")
                w.valueChanged.connect(lambda v: self.doc.set_props(kind, i, power=v))
                lay.addRow("Power", w)
                t = _spin(0, 500, el.theta_jb, 2, 0.5, "K/W")
                t.valueChanged.connect(lambda v: self.doc.set_props(kind, i, theta_jb=v))
                lay.addRow("θ junction-board", t)
            elif kind == "sink":
                w = _spin(0, 5000, el.h_extra, 1, 5, "W/m²K")
                w.valueChanged.connect(lambda v: self.doc.set_props(kind, i, h_extra=v))
                lay.addRow("Extra h", w)
            else:
                x = _spin(0, 2000, el.x * 1000, 2, 0.5, "mm")
                y = _spin(0, 2000, el.y * 1000, 2, 0.5, "mm")
                d = _spin(0.05, 5, el.diameter * 1000, 2, 0.05, "mm")
                fl = QCheckBox("Filled with copper")
                fl.setChecked(el.filled)
                x.valueChanged.connect(lambda v: self.doc.set_props(kind, i, x=v / 1000))
                y.valueChanged.connect(lambda v: self.doc.set_props(kind, i, y=v / 1000))
                d.valueChanged.connect(lambda v: self.doc.set_props(kind, i, diameter=v / 1000))
                fl.toggled.connect(lambda v: self.doc.set_props(kind, i, filled=v, merge=False))
                lay.addRow("X", x)
                lay.addRow("Y", y)
                lay.addRow("Diameter", d)
                lay.addRow("", fl)
            if kind != "via":
                self._geometry_rows(lay, kind, i, el)
        self._updating = False

    def _layer_combo(self, current, outer_only=False, cb=None):
        """!
        @brief Layer chooser.
        @param current Current 0-based layer or None.
        @param outer_only If True offer only the top and bottom layers (sinks).
        @param cb Callable(index) connected to the selection.
        @return QComboBox whose item data holds the 0-based layer.
        """
        n = self.doc.problem.board.layers
        combo = QComboBox()
        layers = [0, n - 1] if outer_only and n > 1 else ([0] if outer_only else list(range(n)))
        if current is None:
            combo.addItem("choose…", -1)
        for l in layers:
            combo.addItem(f"{l + 1}" + (" (top)" if l == 0 else " (bottom)" if l == n - 1 else ""), l)
        if current is not None:
            combo.setCurrentIndex(max(combo.findData(current), 0))
        if cb:
            combo.currentIndexChanged.connect(lambda _i: cb(combo.currentData()))
        return combo

    def _set_layers(self, items, layer):
        """!
        @brief Move elements to a layer.
        @param items List of (kind, index).
        @param layer 0-based layer or -1 for "no change".
        """
        if self._updating or layer is None or layer < 0:
            return

        def mutate(proj):
            for kind, i in items:
                getattr(proj.problem, {"zone": "zones", "heater": "heaters", "sink": "sinks"}[kind])[i].layer = layer

        self.doc.edit("Change layer", mutate)

    def _geometry_rows(self, lay, kind, i, el):
        """!
        @brief Position and size rows for rectangles, or a note for general polygons.
        @param lay Form layout.
        @param kind Element kind.
        @param i Element index.
        @param el The element.
        """
        p = np.asarray(el.polygon) * 1000.0
        axis_aligned = len(p) == 4 and all(
            abs(p[k][0] - p[(k + 1) % 4][0]) < 1e-6 or abs(p[k][1] - p[(k + 1) % 4][1]) < 1e-6 for k in range(4))
        if not axis_aligned:
            lay.addRow(QLabel(f"Polygon with {len(p)} vertices (drag the corner handles to reshape)"))
            return
        x0, y0 = p[:, 0].min(), p[:, 1].min()
        w, h = p[:, 0].max() - x0, p[:, 1].max() - y0
        fields = {"x": _spin(-1000, 2000, x0, 2, 0.5, "mm"), "y": _spin(-1000, 2000, y0, 2, 0.5, "mm"),
                  "w": _spin(0.1, 2000, w, 2, 0.5, "mm"), "h": _spin(0.1, 2000, h, 2, 0.5, "mm")}

        def commit():
            x, y, ww, hh = (fields[k].value() for k in "xywh")
            self.doc.edit("Edit shape", lambda proj: setattr(
                getattr(proj.problem, {"zone": "zones", "heater": "heaters", "sink": "sinks"}[kind])[i],
                "polygon", np.array([[x, y], [x + ww, y], [x + ww, y + hh], [x, y + hh]]) / 1000.0),
                merge_key=f"geom{kind}{i}")

        for label, key in (("X", "x"), ("Y", "y"), ("Width", "w"), ("Height", "h")):
            fields[key].valueChanged.connect(lambda _v: commit())
            lay.addRow(label, fields[key])


class SolverPanel(QWidget):
    """!
    @brief Model choice, solver settings and the Run button.
    """

    run_requested = Signal()

    def __init__(self, doc, parent=None):
        """!
        @param doc The Document.
        @param parent Qt parent.
        """
        super().__init__(parent)
        self.doc, self._updating = doc, False
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)

        g = QGroupBox("Models")
        v = QVBoxLayout(g)
        self.cb = {"fvm": QCheckBox("Finite volume (FVM), reference"),
                   "lumped": QCheckBox("Thermal network (LPTN)"),
                   "analytic": QCheckBox("Analytical (Fourier series)")}
        tips = {"fvm": "Reference model. Any geometry, full temperature field, exact energy balance. Use it for final answers "
                       "and whenever a warning appears. Cost grows with the number of cells.",
                "lumped": "Fast network (milliseconds). Handles partial copper, vias, sinks and several heaters; "
                          "within about 4 % in most cases. Weak when a copper edge crosses the heater, at corners and for thin heaters.",
                "analytic": "Closed-form series (instant). Exact on uniform boards, within a few percent with vias, sinks and "
                            "partial copper. Assumes insulated edges and rectangular heaters; unreliable if a copper edge crosses a heater."}
        for k, c in self.cb.items():
            c.setToolTip(tips[k])
            v.addWidget(c)
            c.toggled.connect(self._apply)
        lay.addWidget(g)

        g = QGroupBox("Settings")
        f = QFormLayout(g)
        self.cell = _spin(0.1, 20, 1.0, 2, 0.25, "mm")
        self.auto_cell = QPushButton("Auto")
        self.auto_cell.setToolTip("Choose a cell size that resolves the smallest heater (about 4 cells across)")
        self.auto_cell.clicked.connect(lambda: self.cell.setValue(suggest_cell_mm(self.doc.problem)))
        cell_row = QHBoxLayout()
        cell_row.addWidget(self.cell, 1)
        cell_row.addWidget(self.auto_cell)
        self.cells_label = QLabel()
        self.solver = QComboBox()
        self.solver.addItem("Sparse direct (exact)", "direct")
        self.solver.addItem("Conjugate gradients", "cg")
        self.solver.addItem("SOR (iterative, for comparison)", "sor")
        self.rings = QSpinBox()
        self.rings.setRange(3, 40)
        self.modes = QSpinBox()
        self.modes.setRange(20, 800)
        self.modes.setSingleStep(20)
        self.local = QCheckBox("Local via and sink corrections")
        self.hot = _spin(-50, 1000, 100, 1, 5, "°C")
        f.addRow("Cell size", cell_row)
        f.addRow("", self.cells_label)
        f.addRow("FVM solver", self.solver)
        f.addRow("Lumped rings", self.rings)
        f.addRow("Analytic modes", self.modes)
        f.addRow("", self.local)
        f.addRow("Hotspot limit", self.hot)
        lay.addWidget(g)

        self.run = QPushButton("Run simulation   (F5)")
        self.run.setObjectName("primary")
        self.run.clicked.connect(self.run_requested)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.status = QLabel("")
        self.status.setWordWrap(True)
        self.checks = QLabel("")
        self.checks.setWordWrap(True)
        lay.addWidget(self.run)
        lay.addWidget(self.progress)
        lay.addWidget(self.status)
        lay.addWidget(self.checks)
        lay.addStretch(1)

        for w in (self.cell, self.rings, self.modes, self.hot):
            w.valueChanged.connect(self._apply)
        self.solver.currentIndexChanged.connect(self._apply)
        self.local.toggled.connect(self._apply)
        doc.changed.connect(self._update_cells)
        doc.state_changed.connect(self.refresh)
        self.refresh()

    def refresh(self):
        """!
        @brief Load the options from the document.
        """
        o = self.doc.options
        self._updating = True
        for k, c in self.cb.items():
            c.setChecked(k in o.models)
        self.cell.setValue(o.cell_mm)
        self.solver.setCurrentIndex(max(self.solver.findData(o.linear_solver), 0))
        self.rings.setValue(o.lumped_rings)
        self.modes.setValue(o.analytic_modes)
        self.local.setChecked(o.analytic_local_corrections)
        self.hot.setValue(o.hotspot_c)
        self._updating = False
        self._update_cells()

    def _update_cells(self):
        """!
        @brief Show the number of FVM cells of the current setting.
        """
        b = self.doc.problem.board
        c = self.cell.value()
        n = max(int(round(b.width * 1000 / c)), 2) * max(int(round(b.height * 1000 / c)), 2) * b.layers
        self.cells_label.setText(f"{n:,} unknowns".replace(",", " "))

    def _apply(self, *_):
        """!
        @brief Write the controls to the document options (at least one model stays selected).
        @param _ Ignored (extra arguments of the Qt signal).
        """
        if self._updating:
            return
        models = tuple(k for k, c in self.cb.items() if c.isChecked())
        if not models:
            self._updating = True
            self.cb["fvm"].setChecked(True)
            self._updating = False
            models = ("fvm",)
        self.doc.set_options(models=models, cell_mm=self.cell.value(), linear_solver=self.solver.currentData(),
                             lumped_rings=self.rings.value(), analytic_modes=self.modes.value(),
                             analytic_local_corrections=self.local.isChecked(), hotspot_c=self.hot.value())
        self._update_cells()

    def set_checks(self, warnings):
        """!
        @brief Show the validity checks of the current design under the Run button.
        @param warnings List of warning strings from checks.check_problem.
        """
        if not warnings:
            self.checks.setText("")
            self.checks.setToolTip("")
            return
        self.checks.setText("⚠ " + warnings[0] + (f"  (+{len(warnings) - 1} more)" if len(warnings) > 1 else ""))
        self.checks.setToolTip("\n\n".join(warnings))

    def set_running(self, running, text=""):
        """!
        @brief Enable or disable the Run button while a simulation runs.
        @param running True while running.
        @param text Status text.
        """
        self.run.setEnabled(not running)
        self.status.setText(text)
        if not running:
            self.progress.setValue(0)

    def set_progress(self, text, fraction):
        """!
        @brief Update the progress bar.
        @param text Status text.
        @param fraction Progress between 0 and 1.
        """
        self.status.setText(text)
        self.progress.setValue(int(fraction * 100))
