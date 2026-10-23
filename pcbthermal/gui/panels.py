"""!
@file panels.py
@brief Side panels: board parameters, element list, inspector and solver settings.
"""

import numpy as np
from PySide6.QtCore import Qt, Signal
import math

from PySide6.QtWidgets import (QAbstractItemView, QTableWidget, QTableWidgetItem, QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox,
                               QHBoxLayout, QLabel, QLineEdit, QMenu, QProgressBar, QPushButton, QSpinBox,
                               QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from .. import blocks
from .. import defaults
from ..api import suggest_cell_mm
from ..model import DIELECTRICS, HEATSINKS, INTERFACES, METALS, PACKAGE_THETA, VIA_FILLS
from ..geometry import polygon_area, rounded_rectangle
from . import tips
from .document import KINDS


def _is_rect(pts):
    """!
    @brief True if the points are an axis-aligned rectangle (four corners, two distinct x and two distinct y values).
    @param pts Array (n, 2).
    @return bool.
    """
    if len(pts) != 4:
        return False
    xs, ys = np.unique(np.round(pts[:, 0], 9)), np.unique(np.round(pts[:, 1], 9))
    return len(xs) == 2 and len(ys) == 2 and len({(round(x, 9), round(y, 9)) for x, y in pts}) == 4


_TITLES = {"zone": "Zones", "heater": "Heaters", "heatsink": "Heatsinks", "via": "Vias"}


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
    @brief Board size, outline and environment. The simple stack-up (`stack_box`) and the materials (`materials_box`) are built here but shown in the Stack-up tab.
    """

    draw_outline_requested = Signal()

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
        self.thickness = _spin(0.2, 10, 1.6, 3, 0.1, "mm")
        self.layers = QSpinBox()
        self.layers.setRange(1, 12)
        self.copper = _spin(5, 210, 35, 1, 5, "µm")
        self.stack_note = QLabel("")
        self.stack_note.setWordWrap(True)
        self.stack_note.setStyleSheet("font-size: 11px; color: gray;")
        self.width.setToolTip("Board size along x in millimetres.")
        self.height.setToolTip("Board size along y in millimetres.")
        self.thickness.setToolTip("Total board thickness in millimetres (simple stack-up: copper and equal dielectric gaps share it). "
                                  "In the advanced stack-up it is the sum of the layers and is edited in the Stack-up tab.")
        self.layers.setToolTip("Number of copper layers (1 to 12). Layer 1 is the top face.")
        self.copper.setToolTip("Copper thickness of every layer in micrometres: 35 µm is 1 oz, 17.5 µm is 0.5 oz, 70 µm is 2 oz. "
                               "Different thickness per layer: use the advanced stack-up in the Stack-up tab.")
        for label, w in (("Width", self.width), ("Height", self.height)):
            f.addRow(label, w)
        lay.addWidget(g)

        # The simple stack-up and the materials are shown in the Stack-up tab (StackupPage.add_parameters); they stay attributes of this panel
        self.stack_box = QGroupBox("Simple stack-up")
        sf = QFormLayout(self.stack_box)
        for label, w in (("Total thickness", self.thickness), ("Copper layers", self.layers), ("Copper per layer", self.copper)):
            sf.addRow(label, w)
        sf.addRow(self.stack_note)

        g = QGroupBox("Board outline")
        v = QVBoxLayout(g)
        self.outline_label = QLabel("")
        self.outline_label.setWordWrap(True)
        self.outline_label.setToolTip("Shape of the board inside the width x height box. Outside the outline there is no board: no copper, no heat, no heat loss. "
                                      "The FVM, FDM and 3D solid solve any outline; the lumped and analytic models run on the rectangle of the same area.")
        self.preset = QComboBox()
        self.preset.addItem("Preset shape...", None)
        for label in ("Rectangle (full box)", "L shape", "T shape", "Circle / ellipse", "Chamfered corners", "Rounded corners"):
            self.preset.addItem(label, label)
        self.preset.setToolTip("Replace the outline by a preset that fits the width x height box. Edit the vertices below afterwards.")
        self.preset.currentIndexChanged.connect(self._pick_outline)
        self.outline_table = QTableWidget(0, 2)
        self.outline_table.setHorizontalHeaderLabels(["x (mm)", "y (mm)"])
        self.outline_table.setMaximumHeight(140)
        self.outline_table.setToolTip("Vertices of the outline in millimetres, from the lower-left corner of the box. Edit a cell to move a vertex.")
        self.outline_table.itemChanged.connect(self._edit_vertex)
        row = QHBoxLayout()
        self.v_add = QPushButton("Add vertex")
        self.v_add.setToolTip("Insert a vertex in the middle of the last edge.")
        self.v_del = QPushButton("Remove vertex")
        self.v_del.setToolTip("Remove the selected vertex (an outline needs at least three).")
        self.v_sub = QPushButton("Subdivide")
        self.v_sub.setToolTip("Insert a vertex in the middle of every edge (twice as many vertices): the first step to turn a corner or a curve into a smooth outline "
                              "by moving the new vertices. A curve is a polygon with many short edges; use edges a few cells long at most.")
        self.v_draw = QPushButton("Draw (O)")
        self.v_draw.setToolTip("Draw the outline on the board: drag a rectangle or click the vertices in polygon mode.")
        for w in (self.v_add, self.v_del, self.v_sub, self.v_draw):
            row.addWidget(w)
        self.v_sub.clicked.connect(self._subdivide)
        self.v_add.clicked.connect(self._add_vertex)
        self.v_del.clicked.connect(self._remove_vertex)
        self.v_draw.clicked.connect(self.draw_outline_requested)
        v.addWidget(self.outline_label)
        v.addWidget(self.preset)
        v.addWidget(self.outline_table)
        v.addLayout(row)
        lay.addWidget(g)

        g = QGroupBox("Environment")
        f = QFormLayout(g)
        self.ambient = _spin(-60, 200, 25, 1, 1, "°C")
        self.h_mode = QComboBox()
        self.h_mode.addItem("Typed by me", "manual")
        self.h_mode.addItem("Computed (convection + radiation)", "computed")
        self.h_mode.setToolTip("Computed: the coefficient of each face follows from the board temperature with natural or "
                               "forced convection correlations plus radiation, solved by iteration.")
        self.h_top = _spin(0, 500, 10, 1, 1, "W/m²K")
        self.h_bottom = _spin(0, 500, 15, 1, 1, "W/m²K")
        self.side_on = QCheckBox("Edges lose heat")
        self.h_side = _spin(0, 500, 10, 1, 1, "W/m²K")
        self.orientation = QComboBox()
        self.orientation.addItem("Horizontal (layer 1 = top faces up)", "horizontal")
        self.orientation.addItem("Vertical (on its edge)", "vertical")
        self.orientation.setToolTip("How the board is mounted (computed heat transfer only). Horizontal: layer 1 is the top face and looks up, the last layer looks "
                                    "down, so the mounting follows from the layer numbering (a hot face looking up loses heat better than one looking down: 0.54 against "
                                    "0.27 in the natural convection correlation). Vertical: the plate correlation with the board height on both faces. "
                                    "With typed coefficients the orientation does not matter: type the h of the real mounting.")
        self.emis_top = _spin(0, 1, 0.9, 2, 0.05, "(0 to 1)")
        self.emis_bottom = _spin(0, 1, 0.9, 2, 0.05, "(0 to 1)")
        self.emis_top.setToolTip("Emissivity of the top face: solder mask and FR-4 about 0.9, bare copper 0.05 to 0.1")
        self.emis_bottom.setToolTip(self.emis_top.toolTip())
        self.air_speed = _spin(0, 50, 0, 2, 0.5, "m/s")
        self.air_speed.setToolTip("Air speed along the board; 0 is still air (natural convection)")
        self.calibration = _spin(0.2, 5, 1.0, 2, 0.05, "× (factor)")
        self.calibration.setToolTip("Multiplier of the computed convection (not of the radiation); fit it to a measurement. "
                                    "The correlations are for isothermal plates and are uncertain by about 20 to 30 % on a board with hot spots.")
        self.computed_rows = []
        f.addRow("Ambient", self.ambient)
        f.addRow("Heat transfer", self.h_mode)
        f.addRow("h top", self.h_top)
        f.addRow("h bottom", self.h_bottom)
        self.manual_rows = [(f.labelForField(self.h_top), self.h_top), (f.labelForField(self.h_bottom), self.h_bottom)]
        self.h_top.setToolTip("Heat transfer coefficient of the top face (convection plus radiation), typed. Natural convection in air is about 5 to 15 W/m²K.")
        self.h_bottom.setToolTip("Heat transfer coefficient of the bottom face, typed. Usually a little lower than the top face for a board facing up.")
        for label, w in (("Orientation", self.orientation), ("Emissivity top", self.emis_top),
                         ("Emissivity bottom", self.emis_bottom), ("Air speed", self.air_speed),
                         ("Convection ×", self.calibration)):
            f.addRow(label, w)
            self.computed_rows.append((f.labelForField(w), w))
        f.addRow("", self.side_on)
        f.addRow("h edges", self.h_side)
        lay.addWidget(g)

        g = self.materials_box = QGroupBox("Materials")
        f = QFormLayout(g)
        self.k_cu = _spin(1, 1000, 385, 0, 5, "W/mK")
        self.k_th = _spin(0.05, 20, 0.3, 2, 0.05, "W/mK")
        self.k_ip = _spin(0.05, 20, 0.9, 2, 0.05, "W/mK")
        self.plating = _spin(1, 200, 25, 0, 1, "µm")
        self.laminate = QComboBox()
        self.laminate.addItem("Laminate preset...", None)
        for entry in DIELECTRICS:
            self.laminate.addItem(f"{entry[0]}: {entry[1]:g} / {entry[2]:g} W/mK", entry)
        self.laminate.setToolTip("Typical dielectric materials (indicative values, not from your laminate datasheet): fills the through-thickness and in-plane "
                                 "conductivity, density and specific heat of the dielectric of the simple stack-up.")
        self.laminate.currentIndexChanged.connect(self._pick_laminate)
        self.k_cu.setToolTip("Thermal conductivity of copper, W/mK (pure copper 385 to 400).")
        self.k_th.setToolTip("Conductivity of the dielectric across the board thickness, W/mK (FR-4 about 0.3). It sets the resistance between layers.")
        self.k_ip.setToolTip("Conductivity of the dielectric along the plane, W/mK (FR-4 about 0.9, glass weave).")
        self.plating.setToolTip("Copper plating thickness of the via barrel in micrometres (typically 20 to 25 µm).")
        for label, w in (("Copper k", self.k_cu), ("Laminate", self.laminate), ("Dielectric k through", self.k_th), ("Dielectric k in-plane", self.k_ip),
                         ("Via plating", self.plating)):
            f.addRow(label, w)
        self.simple_only = [self.laminate, self.k_th, self.k_ip]
        lay.addStretch(1)

        for w in (self.width, self.height, self.thickness, self.copper, self.ambient, self.h_top,
                  self.h_bottom, self.h_side, self.k_cu, self.k_th, self.k_ip, self.plating,
                  self.emis_top, self.emis_bottom, self.air_speed, self.calibration):
            w.valueChanged.connect(self._apply)
        self.h_mode.currentIndexChanged.connect(self._apply)
        self.orientation.currentIndexChanged.connect(self._apply)
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
        advanced = b.is_advanced()
        self.thickness.setValue(b.total_thickness() * 1000)
        # Advanced stack-up: thickness, copper per layer and the dielectric are set layer by layer in the table, so those rows are hidden (not just greyed);
        # the number of layers, the copper conductivity and the via plating still apply
        for w in [self.thickness, self.copper] + self.simple_only:
            w.setEnabled(not advanced)
            w.setVisible(not advanced)
            label = w.parent().layout().labelForField(w) if w.parent() is not None and w.parent().layout() is not None else None
            if label is not None:
                label.setVisible(not advanced)
        self.stack_box.setTitle("Stack-up (layer by layer in the table)" if advanced else "Simple stack-up")
        self.stack_note.setVisible(not advanced)
        self.stack_note.setText("Advanced stack-up: thickness, copper and dielectrics are set layer by layer in the Stack-up tab." if advanced
                                else "Simple stack-up: equal gaps. For different copper weights or dielectrics use the Stack-up tab.")
        self.ambient.setValue(b.ambient)
        self.h_top.setValue(b.h_top)
        self.h_bottom.setValue(b.h_bottom)
        self.h_mode.setCurrentIndex(max(self.h_mode.findData(b.h_mode), 0))
        self.orientation.setCurrentIndex(max(self.orientation.findData(b.orientation), 0))
        self.emis_top.setValue(b.emissivity_top)
        self.emis_bottom.setValue(b.emissivity_bottom)
        self.air_speed.setValue(b.air_speed)
        self.calibration.setValue(b.h_calibration)
        self._show_modes(b.h_mode)
        self.side_on.setChecked(b.h_side is not None)
        self.h_side.setValue(b.h_side or 10.0)
        self.h_side.setEnabled(b.h_side is not None)
        self.k_cu.setValue(m.k_copper)
        self.k_th.setValue(m.k_fr4_through)
        self.k_ip.setValue(m.k_fr4_inplane)
        self.plating.setValue(b.via_plating * 1e6)
        self._fill_outline(b)
        self._updating = False

    def _show_modes(self, mode):
        """!
        @brief Show the controls of the chosen heat-transfer mode (typed values or computed from correlations).
        @param mode "manual" or "computed".
        """
        computed = mode == "computed"
        # The typed h only matters when typed: in computed mode it is just the starting guess of the iteration, so it is hidden
        for label, w in self.manual_rows:
            w.setVisible(not computed)
            if label is not None:
                label.setVisible(not computed)
        for label, w in self.computed_rows:
            w.setVisible(computed)
            if label is not None:
                label.setVisible(computed)

    def _apply(self, *_):
        """!
        @brief Write the control values to the document.
        @param _ Ignored (extra arguments of the Qt signal).
        """
        if self._updating:
            return
        b = self.doc.problem.board
        self.h_side.setEnabled(self.side_on.isChecked())
        self._show_modes(self.h_mode.currentData())

        def mutate(project):
            bd = project.problem.board
            bd.width, bd.height = self.width.value() / 1000, self.height.value() / 1000
            if not bd.is_advanced():                           # In the advanced stack-up these come from the Stack-up tab
                bd.thickness = self.thickness.value() / 1000
                bd.copper_thickness = [self.copper.value() * 1e-6] * bd.layers
            bd.ambient, bd.h_top, bd.h_bottom = self.ambient.value(), self.h_top.value(), self.h_bottom.value()
            bd.h_side = self.h_side.value() if self.side_on.isChecked() else None
            bd.h_mode, bd.orientation = self.h_mode.currentData(), self.orientation.currentData()
            bd.emissivity_top, bd.emissivity_bottom = self.emis_top.value(), self.emis_bottom.value()
            bd.air_speed, bd.h_calibration = self.air_speed.value(), self.calibration.value()
            bd.via_plating = self.plating.value() * 1e-6
            bd.materials.k_copper = self.k_cu.value()
            if not bd.is_advanced():
                bd.materials.k_fr4_through, bd.materials.k_fr4_inplane = self.k_th.value(), self.k_ip.value()

        self.doc.edit("Board parameters", mutate, merge_key="board")

    def _fill_outline(self, b):
        """!
        @brief Show the outline of the board in the label and the vertex table.
        @param b The Board.
        """
        t = self.outline_table
        t.blockSignals(True)
        t.setRowCount(0)
        if b.has_outline():
            o = np.asarray(b.outline) * 1000.0
            t.setRowCount(len(o))
            for r, (x, y) in enumerate(o):
                for c, val in enumerate((x, y)):
                    t.setItem(r, c, QTableWidgetItem(f"{val:.3f}"))
            self.outline_label.setText(f"Polygon: {len(o)} vertices, area {b.board_area() * 1e6:.1f} mm² "
                                       f"({100.0 * b.board_area() / (b.width * b.height):.0f} % of the box).")
        else:
            self.outline_label.setText("Rectangle: the whole width x height box. Choose a preset or draw an outline for other shapes.")
        t.blockSignals(False)
        for w in (self.outline_table, self.v_add, self.v_del, self.v_sub):
            w.setEnabled(b.has_outline())

    def _preset_polygon(self, name):
        """!
        @brief Vertices of a preset outline fitted to the box.
        @param name Preset label.
        @return List of [x, y] in mm, or None for the full rectangle.
        """
        b = self.doc.problem.board
        W, H = b.width * 1000.0, b.height * 1000.0
        if name.startswith("Rectangle"):
            return None
        if name == "L shape":
            return [[0, 0], [W, 0], [W, H / 2], [W / 2, H / 2], [W / 2, H], [0, H]]
        if name == "T shape":
            return [[0, H / 2], [W / 3, H / 2], [W / 3, 0], [2 * W / 3, 0], [2 * W / 3, H / 2], [W, H / 2], [W, H], [0, H]]
        if name == "Circle / ellipse":
            return [[W / 2 * (1 + math.cos(2 * math.pi * k / 32)), H / 2 * (1 + math.sin(2 * math.pi * k / 32))] for k in range(32)]
        c = 0.15 * min(W, H)
        if name == "Rounded corners":
            return rounded_rectangle(W, H, c)
        return [[c, 0], [W - c, 0], [W, c], [W, H - c], [W - c, H], [c, H], [0, H - c], [0, c]]

    def _pick_outline(self, _index):
        """!
        @brief Apply a preset outline.
        @param _index Ignored.
        """
        name = self.preset.currentData()
        if name is None or self._updating:
            return
        self.doc.set_outline(self._preset_polygon(name))
        self.preset.setCurrentIndex(0)

    def _vertices(self):
        """!
        @brief The vertices in the table.
        @return List of [x, y] in mm, or None if a cell is not a number.
        """
        t = self.outline_table
        try:
            return [[float(t.item(r, 0).text()), float(t.item(r, 1).text())] for r in range(t.rowCount())]
        except (ValueError, AttributeError):
            return None

    def _edit_vertex(self, _item):
        """!
        @brief A vertex was edited: apply the table if it is a valid outline, otherwise restore it.
        @param _item The changed QTableWidgetItem (ignored).
        """
        if self._updating:
            return
        pts = self._vertices()
        b = self.doc.problem.board
        if pts is not None:
            probe = np.asarray(pts) / 1000.0
            from ..geometry import polygon_is_simple
            if len(probe) >= 3 and polygon_is_simple(probe) and polygon_area(probe) > 0 and probe.min() >= 0 \
                    and probe[:, 0].max() <= b.width and probe[:, 1].max() <= b.height:
                self.doc.set_outline(pts)
                return
        self._fill_outline(b)                                 # Not a valid outline: show the stored one again

    def _subdivide(self):
        """!
        @brief Insert a vertex in the middle of every edge of the outline.
        """
        pts = self._vertices()
        if pts and len(pts) < 2000:
            out = []
            for a, b in zip(pts, pts[1:] + pts[:1]):
                out += [a, [(a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0]]
            self.doc.set_outline(out)

    def _add_vertex(self):
        """!
        @brief Insert a vertex in the middle of the last edge.
        """
        pts = self._vertices()
        if pts:
            mid = [(pts[-1][0] + pts[0][0]) / 2.0, (pts[-1][1] + pts[0][1]) / 2.0]
            self.doc.set_outline(pts + [mid])

    def _remove_vertex(self):
        """!
        @brief Remove the selected vertex (the last one if none is selected).
        """
        pts = self._vertices()
        if pts and len(pts) > 3:
            row = self.outline_table.currentRow()
            del pts[row if 0 <= row < len(pts) else -1]
            self.doc.set_outline(pts)

    def _pick_laminate(self, _index):
        """!
        @brief Apply a dielectric preset to the simple stack-up.
        @param _index Ignored (the combo index).
        """
        entry = self.laminate.currentData()
        if entry is None or self._updating:
            return

        def mutate(project):
            m = project.problem.board.materials
            m.k_fr4_through, m.k_fr4_inplane, m.rho_fr4, m.cp_fr4 = entry[1:]

        self.doc.edit("Laminate material", mutate)
        self.laminate.setCurrentIndex(0)

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
        self.tree.setToolTip("Every zone, heater, heatsink and via of the board. Click to select it on the board, right-click for more actions.")
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
            lst = getattr(pr, {"zone": "zones", "heater": "heaters", "heatsink": "heatsinks", "via": "vias"}[kind])
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
        self._manual_as = {}                       # (kind, index) -> "h" or "rsa": which value a manual-input heatsink is typed as
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
                combo.setToolTip("Move all the selected zones and heaters to this layer.")
                combo.currentIndexChanged.connect(lambda idx, m=movable: self._set_layers(m, idx))
                lay.addRow("Move to layer", combo)
        else:
            kind, i = valid[0]
            root = lay                                         # The sections below are boxes inside this form

            def box(title, tip="", host=root):
                """Add a titled box to the form and return the form inside it (each box groups the fields that belong together)."""
                g = QGroupBox(title)
                if tip:
                    g.setToolTip(tip)
                host.addRow(g)
                return QFormLayout(g)

            el = getattr(pr, {"zone": "zones", "heater": "heaters", "heatsink": "heatsinks", "via": "vias"}[kind])[i]
            title = QLabel(f"<b>{kind.capitalize()}</b>")
            lay.addRow(title)
            name = QLineEdit(el.name)
            name.editingFinished.connect(lambda: self.doc.set_props(kind, i, "Rename", name=name.text()))
            lay.addRow("Name", name)
            if kind != "via":
                lay.addRow("Layer", self._layer_combo(el.layer, outer_only=(kind == "heatsink"),
                                                       cb=lambda idx: self._set_layers([(kind, i)], idx)))
            if kind == "zone":
                lay = box("Copper")
                w = _spin(0, 1, el.fill, 2, 0.05)
                w.setToolTip("Copper fill fraction inside the polygon: 1 is solid copper, 0.5 a hatched or half-filled area.")
                w.valueChanged.connect(lambda v: self.doc.set_props(kind, i, fill=v))
                lay.addRow("Copper fill", w)
            elif kind == "heater":
                comp = el.is_component()
                typ = QComboBox()
                typ.addItem("Heat source", "source")
                typ.addItem("Component", "component")
                typ.setCurrentIndex(1 if comp else 0)
                typ.setToolTip("Heat source: a power in watts over a footprint (nothing else), optionally with the interface (solder, paste) between it and the board. Component: a part "
                               "with a junction, a package and, if you want, a heatsink on top (junction temperature, limit, top path). Switching to a source clears the component "
                               "fields (it can be undone).")

                def switch_type(_i, c=typ):
                    want = c.currentData()
                    if want == "source" and comp:
                        self.doc.set_props(kind, i, role="source", theta=0.0, tj_max=0.0, psi_jb=0.0, power_tc=0.0, theta_jc_top=0.0, theta_sa=0.0, interface=0.0,
                                           contact_area=0.0, pad_thickness=0.0, pad_k=0.0, family="", heatsink="", merge=False)
                    elif want == "component" and not comp:
                        self.doc.set_props(kind, i, role="component", merge=False)

                typ.currentIndexChanged.connect(switch_type)
                root.addRow("Type", typ)
                lay = box("Part")
                w = _spin(0, 1000, el.power, 3, 0.1, "W")
                w.valueChanged.connect(lambda v: self.doc.set_props(kind, i, power=v))
                w.setToolTip("Power dissipated by the part, in watts.")
                lay.addRow("Power", w)
                if not comp:
                    base_form = box("Interface under the source", "The layer between the heater and the board copper (solder, paste, adhesive). Direct contact if nothing is set.")
                    self._pad_rows(base_form, kind, i, el, heater=True, base=True)
                    theta_now = el.junction_theta()
                    info = QLabel(f"Resistance over the footprint: {theta_now:.2f} K/W" if theta_now > 0 else "Direct contact: the source is at the board temperature.")
                    info.setToolTip("The interface resistance divided by the footprint area: the temperature of the source is the hottest board point under it plus this resistance times the power.")
                    base_form.addRow(info)
                else:
                    lay = box("Junction")
                    fam = QComboBox()
                    fam.addItem("Custom", "")
                    for entry in PACKAGE_THETA:
                        fam.addItem(entry[0], entry[0])
                    fam.setCurrentIndex(max(fam.findData(el.family), 0))
                    fam.setToolTip("Package family: choosing one fills the typical θ junction-pad, θJC(top) and Tj max below (indicative values, not from your datasheet; they are a library "
                                   "in Preferences). Replace them by the datasheet numbers whenever you have them.")
                    typical = QLabel("")
                    typical.setWordWrap(True)
                    typical.setStyleSheet("font-size: 11px; color: gray;")
                    typical.setToolTip("The typical values and the note of the chosen family, from the library.")
                    entry = next((e for e in PACKAGE_THETA if e[0] == el.family), None)
                    typical.setText(f"Typical for {entry[0]}: θ junction-pad {entry[1]:g} K/W, θJC(top) {entry[2]:g} K/W, Tj max {entry[3]:g} °C." if entry else
                                    "Custom: no typical values applied. Type the datasheet numbers below.")
                    if entry and entry[4]:
                        typical.setToolTip(entry[4])                       # The note and the source of the library entry

                    def pick_family(_idx, c=fam):
                        e = next((x for x in PACKAGE_THETA if x[0] == c.currentData()), None)
                        if e is None:
                            self.doc.set_props(kind, i, family="", merge=False)
                        else:                                            # The typical values of the library go into the part
                            fields = dict(theta=e[1], theta_jc_top=e[2], family=e[0])
                            if e[3] > 0:
                                fields["tj_max"] = e[3]
                            self.doc.set_props(kind, i, merge=False, **fields)

                    fam.currentIndexChanged.connect(pick_family)
                    lay.addRow("Package family", fam)
                    lay.addRow(typical)
                    t = _spin(0, 5000, el.theta, 2, 0.5, "K/W")
                    t.valueChanged.connect(lambda v: self.doc.set_props(kind, i, theta=v))
                    t.setToolTip("Junction-to-pad resistance of the part. Take the datasheet's junction-to-bottom or junction-to-pad number (θJC(bot), RθJC of a power "
                                 "MOSFET, θJ-L of a diode, Rth j-sp of an LED). Never θJA. Worst case: all the power enters the board. With only θJB or ψJB use the ψJB "
                                 "box below; with nothing, pick the package family (a typical value) or leave 0 (the report shows the board temperature under the part and "
                                 "says the junction is hotter).")
                    lay.addRow("θ junction-pad", t)
                    tj = _spin(0, 500, el.tj_max, 1, 5, "°C")
                    tj.setToolTip("Maximum junction temperature of the part (0 = no limit). The report gives the margin and the power limit.")
                    tj.valueChanged.connect(lambda v: self.doc.set_props(kind, i, tj_max=v))
                    lay.addRow("Tj max", tj)
                    psi = _spin(0, 500, el.psi_jb, 2, 0.5, "K/W")
                    psi.setToolTip("Junction-to-board characterisation parameter ψJB (0 = not used). The report adds Tj = mean board temperature in the ring "
                                   "0.5 to 1.5 mm around the package + ψJB·P, the least pessimistic estimate when the datasheet has no junction-to-pad number.")
                    psi.valueChanged.connect(lambda v: self.doc.set_props(kind, i, psi_jb=v))
                    lay.addRow("ψJB", psi)
                    tc = _spin(-5, 5, el.power_tc * 100.0, 3, 0.1, "%/K")
                    tc.setToolTip("Temperature coefficient of the dissipated power (0 = constant). A power MOSFET's Rds(on) rises about 0.3 to 0.7 %/K, so its loss grows "
                                  "with its junction temperature: P = P0 (1 + tc (Tj − 25 °C)), P0 the power typed above (at 25 °C). The program solves it together with "
                                  "the board and warns when there is no stable point (thermal runaway). Steady-state models only.")
                    tc.valueChanged.connect(lambda v: self.doc.set_props(kind, i, power_tc=v / 100.0))
                    lay.addRow("Power coefficient", tc)
                    lay = box("Heatsink on the package")
                    # Two lists: the heatsink and the air flow it was catalogued at (only the flows the catalogue gives); the stored name is "heatsink, flow"
                    kinds = []
                    for e in HEATSINKS:
                        if e[3] not in kinds:
                            kinds.append(e[3])
                    cur = next((e for e in HEATSINKS if e[0] == el.heatsink), None)
                    hs = QComboBox()
                    hs.addItem("None (no heatsink)", "none")
                    for k_ in kinds:
                        hs.addItem(k_, k_)
                    hs.addItem("Custom", "custom")
                    hs.setCurrentIndex(hs.findData(cur[3]) if cur else (hs.findData("custom") if el.theta_sa > 0 else 0))
                    hs.setToolTip("A typical heatsink for the top of the package, from a catalogue library (Preferences): choosing one fills θSA below with its catalogue value, which you "
                                  "can change. None: no heatsink (all the power enters the board). Custom: type your own θSA. The catalogue values are for their own test "
                                  "conditions: yours depends on the air flow, the orientation and the mounting.")
                    flow = QComboBox()
                    if cur:
                        for e in HEATSINKS:
                            if e[3] == cur[3]:
                                flow.addItem(f"{e[4]}: {e[1]:g} K/W", e[0])
                        flow.setCurrentIndex(max(flow.findData(cur[0]), 0))
                    flow.setToolTip("The air flow of the catalogue value (natural convection, 1 m/s, 2 m/s, forced air): only the flows the catalogue gives for this heatsink. The "
                                    "air speed of the board (Environment) does not change θSA: choose the flow that matches your case or type your own θSA.")
                    hs_note = QLabel("")
                    hs_note.setWordWrap(True)
                    hs_note.setStyleSheet("font-size: 11px; color: gray;")
                    hs_note.setToolTip("The catalogue value and its source for the chosen heatsink and flow.")
                    hs_note.setText(f"Catalogue: {cur[0]}, {cur[1]:g} K/W." if cur else
                                    ("Custom: your own θSA." if el.theta_sa > 0 else "No heatsink: all the power enters the board (worst case)."))
                    if cur:
                        hs_note.setToolTip(cur[2])                         # The source and the test conditions

                    def pick_heatsink(_idx, c=hs):
                        key = c.currentData()
                        if key == "none":
                            self.doc.set_props(kind, i, theta_sa=0.0, heatsink="", merge=False)
                        elif key == "custom":
                            self.doc.set_props(kind, i, heatsink="", merge=False)
                        else:                                             # The first catalogued flow of the heatsink
                            e = next(x for x in HEATSINKS if x[3] == key)
                            self.doc.set_props(kind, i, theta_sa=e[1], heatsink=e[0], merge=False)

                    def pick_flow(_idx, c=flow):
                        e = next((x for x in HEATSINKS if x[0] == c.currentData()), None)
                        if e is not None:
                            self.doc.set_props(kind, i, theta_sa=e[1], heatsink=e[0], merge=False)

                    hs.currentIndexChanged.connect(pick_heatsink)
                    flow.currentIndexChanged.connect(pick_flow)
                    lay.addRow("Heatsink", hs)
                    if cur:
                        lay.addRow("Air flow", flow)
                    lay.addRow(hs_note)
                    sa = _spin(0, 5000, el.theta_sa, 2, 0.5, "K/W")
                    sa.setToolTip("Resistance from a heatsink on top of the package to the ambient (datasheet θSA at your air flow). 0 = no top path: all the power "
                                  "enters the board (worst case). Needs θ junction-pad. Steady-state models only.")
                    sa.valueChanged.connect(lambda v: self.doc.set_props(kind, i, theta_sa=v))
                    lay.addRow("Heatsink θSA", sa)
                    top_active = el.theta_sa > 0                                # The boxes of the top path appear as soon as there is a heatsink resistance
                    if top_active and el.theta <= 0:
                        need = QLabel("The top path also needs a junction-to-pad θ above zero (Junction box).")
                        need.setWordWrap(True)
                        need.setStyleSheet("font-size: 11px; color: gray;")
                        need.setToolTip("The heat that goes up is taken from the heat that enters the board, which needs the junction-to-pad resistance θ to be known.")
                        lay.addRow(need)
                    why = ""
                    if top_active:                                              # The top path boxes appear as soon as there is a heatsink θSA
                        lay = box("Package top: junction to case", why)
                        jc = _spin(0, 5000, el.theta_jc_top, 2, 0.5, "K/W")
                        jc.setToolTip("Junction-to-case (top) resistance θJC(top) of the package, in series with the interface and the heatsink. Used only when the "
                                      "heatsink resistance is set (a bare mould carries about 1 % of the heat and is ignored: worst case).")
                        jc.valueChanged.connect(lambda v: self.doc.set_props(kind, i, theta_jc_top=v))
                        lay.addRow("θJC top", jc)
                        body_t = _spin(0, 50, 0.0, 2, 0.1, "mm")
                        body_m = QComboBox()
                        for label, k_ in (("Mould compound (0.9 W/mK)", 0.9), ("Thermally enhanced mould (2.3 W/mK)", 2.3), ("Alumina ceramic (24 W/mK)", 24.0),
                                          ("Copper lid / heat spreader (385 W/mK)", 385.0)):
                            body_m.addItem(label, k_)
                        body_t.setToolTip("Estimate θJC(top) when the datasheet has no value: the thickness of the package body above the die (a plastic QFN has 0.3 to 1 mm of mould). "
                                          "θ = thickness / (k × contact area), one-dimensional through the body, no spreading: an upper bound for a small die under a larger "
                                          "lid. A processor's datasheet θJC already includes its heat spreader and the paste under it: use that instead. 0 = not used.")
                        body_m.setToolTip("Material of the package body above the die (typical conductivities: mould 0.88 to 0.9 W/mK, enhanced mould 2.3 to 6, alumina 24, copper 385).")

                        def from_body(_v, t=body_t, m=body_m, spin=jc, e=el):
                            area = (e.contact_area or e.area())
                            if t.value() > 0 and area > 0:
                                spin.setValue(t.value() * 1e-3 / (m.currentData() * area))

                        body_t.valueChanged.connect(from_body)
                        body_m.currentIndexChanged.connect(from_body)
                        lay.addRow("Body thickness", body_t)
                        lay.addRow("Body material", body_m)
                        ca = _spin(0, 100000, el.contact_area * 1e6, 2, 5, "mm²")
                        ca.setToolTip("Area of the package top that touches the heatsink through the paste (0 = the footprint). For a processor it is the lid, for a chip with an "
                                      "exposed top the die or the exposed pad; the interface resistance is divided by this area, not drawn.")
                        ca.valueChanged.connect(lambda v: self.doc.set_props(kind, i, contact_area=v * 1e-6))
                        lay.addRow("Contact area", ca)
                        pad_form = box("Interface: package top to heatsink", why)
                        self._pad_rows(pad_form, kind, i, el, heater=True)
            elif kind == "heatsink":
                is_block = el.is_block()
                mode = QComboBox()
                mode.addItem("Manual input: I give h or θSA", False)
                mode.addItem("Metal block: the program computes it", True)
                mode.setCurrentIndex(1 if is_block else 0)
                mode.setToolTip("How the cooling of this area is described. Manual input: you give the extra heat transfer coefficient h, or the heatsink's θSA from its "
                                "datasheet (one or the other). Metal block: you give the plate (thickness, metal, interface to the board, optional fins) and the program "
                                "computes how it spreads and dissipates the heat with the board's own face coefficient (typed or computed, orientation included).")

                def switch(_i, m=mode):
                    block = bool(m.currentData())
                    if block != is_block:
                        # The extra h of a manual heatsink is its own coolant coefficient: carried into a block it would add cooling to the exposed surface that
                        # nobody asked for, so a new block starts at 0 and a heatsink going back to manual input gets the default again
                        self.doc.set_props(kind, i, **self._block_defaults(), merge=False) if block else self.doc.set_props(kind, i, thickness=0.0, h_extra=defaults.value("new_elements", "heatsink_h_extra"), merge=False)

                mode.currentIndexChanged.connect(switch)
                root.addRow("Cooling model", mode)                 # A single field: no box of its own
                area_m2 = float(polygon_area(np.asarray(el.polygon)))
                if not is_block:
                    lay = box("Manual input")
                    # One value is typed and the other follows (h = 1 / (θSA × area)); which one is typed is a choice of the form, kept while the heatsink is selected
                    use_rsa = self._manual_as.get((kind, i), "h") == "rsa"
                    how = QComboBox()
                    how.addItem("Heat transfer coefficient h (W/m²K)", "h")
                    how.addItem("Heatsink resistance θSA (K/W)", "rsa")
                    how.setCurrentIndex(1 if use_rsa else 0)
                    how.setToolTip("Which value you type. h: the extra coefficient added to the board face inside the polygon. θSA: the datasheet resistance of the whole "
                                   "heatsink to ambient; the program converts it to h = 1/(θSA × area of this polygon), spreading the heatsink over the polygon. "
                                   "Either way the same single number reaches the models.")

                    def pick_how(_i, c=how):
                        self._manual_as[(kind, i)] = c.currentData()
                        self.rebuild()

                    how.currentIndexChanged.connect(pick_how)
                    lay.addRow("Input as", how)
                    if use_rsa:
                        rsa = _spin(0, 5000, (1.0 / (el.h_extra * area_m2)) if el.h_extra > 0 and area_m2 > 0 else 0.0, 3, 0.1, "K/W")
                        rsa.setToolTip("Heatsink resistance to ambient θSA from its datasheet, at your air flow and orientation (0 = not used). The extra h is set to "
                                       "1/(θSA × area of this polygon): the whole heatsink is spread over the polygon. Datasheets give θSA for natural convection in the "
                                       "orientation they tested (fins vertical is the best case): use the value for your mounting.")

                        def from_rsa(v, a=area_m2):
                            if a > 0:
                                self.doc.set_props(kind, i, h_extra=(1.0 / (v * a)) if v > 0 else 0.0)

                        rsa.valueChanged.connect(from_rsa)
                        lay.addRow("θSA from datasheet", rsa)
                        note = QLabel(f"Equivalent h = {el.h_extra:.1f} W/m²K over {area_m2 * 1e6:.0f} mm²")
                        note.setToolTip("The coefficient the models use, computed from θSA and the area of the polygon.")
                        lay.addRow("", note)
                    else:
                        w = _spin(0, 5000, el.h_extra, 1, 5, "W/m²K")
                        w.valueChanged.connect(lambda v: self.doc.set_props(kind, i, h_extra=v))
                        w.setToolTip("Extra heat transfer coefficient added to the board face inside the polygon (convection plus radiation of the heatsink, over its "
                                     "footprint).")
                        lay.addRow("Extra h", w)
                        if el.h_extra > 0 and area_m2 > 0:
                            note = QLabel(f"Equivalent θSA = {1.0 / (el.h_extra * area_m2):.2f} K/W over {area_m2 * 1e6:.0f} mm²")
                            note.setToolTip("The heatsink resistance to ambient that this coefficient and the polygon area correspond to.")
                            lay.addRow("", note)
                else:
                    lay = box("Metal block")
                    only = QLabel("The FVM, FDM and 3D solid model the block fully. The Lumped and Analytic models have it in steady state only (within about 5 % of the FVM); their time simulation does not.")
                    only.setWordWrap(True)
                    only.setStyleSheet("font-size: 11px; color: gray;")
                    only.setToolTip("The Lumped model keeps the block as one more layer of its ring network and the Analytic model as a graph of tiles in its local "
                                    "correction; both were within 5 % of the FVM in 74 test cases, with no time simulation.")
                    lay.addRow(only)
                    th = _spin(0.01, 100, el.thickness * 1000, 2, 0.5, "mm")
                    th.setToolTip("Thickness of the metal block pressed on this face. The heat enters the block only where the block overlaps copper of this layer, "
                                  "spreads in the metal and leaves by its surface.")
                    th.valueChanged.connect(lambda v: self.doc.set_props(kind, i, thickness=v / 1000))
                    lay.addRow("Block thickness", th)
                    mat = QComboBox()
                    presets = list(METALS) + [("Custom", None, None)]
                    for label, k_, c_ in presets:
                        mat.addItem(label, (k_, c_))
                    cur = next((n for n, (_, k_, c_) in enumerate(presets) if k_ == el.k and c_ == el.rho_cp), len(presets) - 1)
                    mat.setCurrentIndex(cur)
                    kk = _spin(0.1, 1000, el.k, 1, 5, "W/mK")
                    kk.valueChanged.connect(lambda v: self.doc.set_props(kind, i, k=v))

                    def pick(_idx, mat=mat, kk=kk):
                        k_, c_ = mat.currentData()
                        if k_ is not None:
                            kk.setValue(k_)
                            self.doc.set_props(kind, i, k=k_, rho_cp=c_, merge=False)

                    mat.currentIndexChanged.connect(pick)
                    lay.addRow("Block material", mat)
                    lay.addRow("Block k", kk)
                    self._pad_rows(box("Interface: board to block"), kind, i, el, heater=False)
                    lay = box("Fins (optional)")
                    fh = _spin(0, 200, el.fin_height * 1000, 2, 1, "mm")
                    ft = _spin(0, 20, el.fin_thickness * 1000, 2, 0.1, "mm")
                    fp = _spin(0, 100, el.fin_pitch * 1000, 2, 0.5, "mm")
                    fh.setToolTip("Height of the plate fins on the exposed face of the block (0 = a plain plate). The program computes the area gain and the fin efficiency "
                                  "tanh(mL)/(mL) of the metal.")
                    ft.setToolTip("Thickness of one fin.")
                    fp.setToolTip("Distance between the axes of two fins. The air gap is pitch minus thickness: in still air less than about 4 to 6 mm chokes the "
                                  "natural convection (the program warns; it does not slow the air between the fins).")
                    for key, spin in (("fin_height", fh), ("fin_thickness", ft), ("fin_pitch", fp)):
                        spin.valueChanged.connect(lambda v, k=key: self.doc.set_props(kind, i, **{k: v / 1000.0}))
                    lay.addRow("Fin height", fh)
                    lay.addRow("Fin thickness", ft)
                    lay.addRow("Fin pitch", fp)
                    lay = box("Extra cooling of the exposed surface (optional)")
                    w = _spin(0, 5000, el.h_extra, 1, 5, "W/m²K")
                    w.valueChanged.connect(lambda v: self.doc.set_props(kind, i, h_extra=v))
                    w.setToolTip("Added to the coefficient of the exposed surface of the block. Leave 0 to use the board's own face coefficient; use it for a finned block "
                                 "of which you know the datasheet performance instead of the fins above.")
                    lay.addRow("Extra h", w)
            else:
                lay = box("Via")
                x = _spin(0, 2000, el.x * 1000, 2, 0.5, "mm")
                y = _spin(0, 2000, el.y * 1000, 2, 0.5, "mm")
                d = _spin(0.05, 5, el.diameter * 1000, 2, 0.05, "mm")
                fill = QComboBox()
                for name_, _k, _note in VIA_FILLS:
                    fill.addItem(name_)
                names = [e[0] for e in VIA_FILLS]
                if el.fill in names:
                    current = names.index(el.fill)
                elif el.filled:                                          # A file written before the fills had names: a copper-filled via
                    current = next((n for n, e in enumerate(VIA_FILLS) if e[1] >= 300.0), 0)
                else:
                    current = next((n for n, e in enumerate(VIA_FILLS) if abs(e[1] - el.fill_k) < 1e-9), None)
                    if current is None:
                        fill.addItem("Custom")
                        current = fill.count() - 1
                fill.setCurrentIndex(current)
                fill.setToolTip("What fills the barrel (Open, Epoxy resin, Conductive paste, Copper): choosing one fills in its typical conductivity below, which you can change. "
                                "The list is a library in Preferences. A fabricator's 'filled via' is usually an epoxy resin plug: it keeps the hole closed but "
                                "barely conducts heat. Only an electroplated copper fill is a real heat path.")
                fill_k = _spin(0, 500, el.fill_k if not (el.filled and not el.fill_k) else 385.0, 2, 1, "W/mK")
                fill_k.setToolTip("Conductivity of the fill used for this via (W/mK). It starts at the typical value of the chosen fill and can be edited for this via; the typical "
                                  "values are in Preferences (Libraries - via fills). 0 = open barrel.")
                typical = QLabel("")
                typical.setWordWrap(True)
                typical.setStyleSheet("font-size: 11px; color: gray;")
                typical.setToolTip("The typical conductivity and the note of the chosen fill, from the library.")
                entry = VIA_FILLS[current] if current < len(VIA_FILLS) else None
                typical.setText(f"Typical: {entry[1]:g} W/mK. {entry[2]}" if entry else "Custom value.")
                x.valueChanged.connect(lambda v: self.doc.set_props(kind, i, x=v / 1000))
                y.valueChanged.connect(lambda v: self.doc.set_props(kind, i, y=v / 1000))
                d.valueChanged.connect(lambda v: self.doc.set_props(kind, i, diameter=v / 1000))

                def pick_fill(idx):
                    if idx < len(VIA_FILLS):                              # The typical value of the library goes into this via
                        self.doc.set_props(kind, i, filled=False, fill_k=VIA_FILLS[idx][1], fill=VIA_FILLS[idx][0], merge=False)

                def edit_k(v):
                    # An edited value stays with this via; the name is kept as the family it started from
                    self.doc.set_props(kind, i, filled=False, fill_k=v, merge=True)

                fill.currentIndexChanged.connect(pick_fill)
                fill_k.valueChanged.connect(edit_k)
                lay.addRow("X", x)
                lay.addRow("Y", y)
                lay.addRow("Diameter", d)
                lay.addRow("Fill", fill)
                lay.addRow("Fill conductivity", fill_k)
                lay.addRow(typical)
            if kind != "via":
                self._geometry_rows(box("Position and size"), kind, i, el)
        tips.apply(self.form_host)
        self._updating = False

    @staticmethod
    def _block_defaults():
        """!
        @brief Properties of a new metal block from the user's defaults: thickness, metal and interface material.
        @return Dict of Heatsink fields (the extra h starts at 0).
        """
        new = defaults.load()["new_elements"]
        metal = next((m for m in METALS if m[0] == new["block_metal"]), METALS[0])
        pad = next((i for i in INTERFACES if i[0] == new["block_interface"]), None)
        out = dict(thickness=new["block_thickness_mm"] * 1e-3, h_extra=0.0, k=metal[1], rho_cp=metal[2])
        if pad is not None:
            out.update(pad_thickness=pad[2] * 1e-3, pad_k=pad[1], contact_r=pad[2] * 1e-3 / pad[1])
        return out

    def _pad_rows(self, lay, kind, index, el, heater, base=False):
        """!
        @brief The interface between a heatsink and the board or the package: one dielectric sheet (paste, gap pad) with its own material and thickness.
        @details Rows: a material preset (typical thickness and conductivity), the thickness (mm), the conductivity (W/mK) and the resulting resistance per area
                 (K cm2/W). The sheet defines the resistance as thickness / conductivity; typing the resistance directly replaces the sheet (custom value).
        @param lay Form layout.
        @param kind Element kind ("heater" or "heatsink").
        @param index Element index.
        @param el The element (a Heater for the package top, a Heatsink for a block on the board).
        @param heater True for the interface of a part, False for the interface under a metal block.
        @param base True for the interface UNDER a pure heat source (between it and the board); False for the one on top of the package.
        """
        where = "between the heater and the board" if base else ("between the package top and the heatsink" if heater else "between the board and the block")
        r_now = el.base_interface_kcm2() if base else (el.interface_kcm2() if heater else el.interface_resistance() * 1e4)
        t_now, k_now = (el.base_pad_thickness, el.base_pad_k) if base else (el.pad_thickness, el.pad_k)

        def write(thickness, conductivity, resistance):
            # Resistance in K cm2/W; the sheet fields are zero for a typed resistance
            if base:
                fields = dict(base_pad_thickness=thickness, base_pad_k=conductivity, base_interface=resistance)
            else:
                fields = dict(pad_thickness=thickness, pad_k=conductivity)
                fields.update(interface=resistance) if heater else fields.update(contact_r=resistance * 1e-4)
            self.doc.set_props(kind, index, merge=False, **fields)

        mat = QComboBox()
        mat.addItem("Interface material preset...", None)
        mat.addItem("Direct contact (no material, R = 0)", "direct")
        for label, k_, t_ in INTERFACES:
            mat.addItem(f"{label}: {t_:g} mm", (k_, t_ * 1e-3))
        mat.setToolTip(f"The one dielectric sheet {where} (thermal paste or gap pad): a preset fills its thickness and conductivity. "
                       "'Direct contact' means no material in between (for example bare copper pressed on the metal): thickness and resistance 0, the optimistic limit. Indicative values (apparent "
                       "conductivity including the contact resistances): check your material's datasheet. The sheet can have its own material and thickness.")
        th = _spin(0, 20, t_now * 1000, 3, 0.1, "mm")
        th.setToolTip(f"Thickness of the dielectric sheet {where} (paste 0.05 to 0.1 mm, gap pad 0.5 to 1.5 mm). With its conductivity it gives the interface "
                      "resistance thickness / k; 0 = type the resistance below instead.")
        kk = _spin(0, 100, k_now, 2, 0.5, "W/mK")
        kk.setToolTip("Conductivity of the dielectric sheet (grease 1 to 5, gap pads 1 to 6 W/mK apparent; the datasheet's bulk value is higher than what a joint "
                      "gives because of the contact resistances).")
        res = _spin(0, 1000, r_now, 3, 0.1, "K·cm²/W")
        res.setToolTip(f"Resistance per area of the interface {where}: thickness / conductivity of the sheet, or typed here (which replaces the sheet). Good paste 0.3, "
                       "default paste 0.5, soft gap pad 1.7, gap pad 5, hard pad 10; 0 = perfect contact (optimistic). " +
                       ("It is divided by the contact area of the part." if heater else "The contact is over the copper under the block: there is nothing to draw."))

        def pick(_i):
            data = mat.currentData()
            if data == "direct":
                write(0.0, 0.0, 0.0)                                   # No sheet and no resistance: perfect contact (optimistic)
            elif data is not None:
                k_, t_ = data
                write(t_, k_, t_ / k_ * 1e4)

        def sheet(_v):
            if th.value() > 0 and kk.value() > 0:
                write(th.value() * 1e-3, kk.value(), th.value() * 1e-3 / kk.value() * 1e4)

        mat.currentIndexChanged.connect(pick)
        th.valueChanged.connect(sheet)
        kk.valueChanged.connect(sheet)
        res.valueChanged.connect(lambda v: write(0.0, 0.0, v))
        lay.addRow("Interface material", mat)
        lay.addRow("Interface thickness", th)
        lay.addRow("Interface conductivity", kk)
        lay.addRow("Interface resistance", res)

    def _layer_combo(self, current, outer_only=False, cb=None):
        """!
        @brief Layer chooser.
        @param current Current 0-based layer or None.
        @param outer_only If True offer only the top and bottom layers (heatsinks).
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
                getattr(proj.problem, {"zone": "zones", "heater": "heaters", "heatsink": "heatsinks"}[kind])[i].layer = layer

        self.doc.edit("Change layer", mutate)

    def _geometry_rows(self, lay, kind, i, el):
        """!
        @brief Position and size of a selected shape: editable rows for a rectangle (plus its area), a read-only summary (vertices, box, area) for any other polygon.
        @param lay Form layout.
        @param kind Element kind.
        @param i Element index.
        @param el The element.
        """
        p = np.asarray(el.polygon) * 1000.0
        x0, y0 = p[:, 0].min(), p[:, 1].min()
        w, h = p[:, 0].max() - x0, p[:, 1].max() - y0
        area = float(polygon_area(np.asarray(el.polygon))) * 1e6
        if not _is_rect(p):
            info = QLabel(f"Polygon with {len(p)} vertices (drag the corner handles to reshape): box {w:.2f} × {h:.2f} mm at ({x0:.2f}, {y0:.2f}), area {area:.2f} mm²")
            info.setWordWrap(True)
            info.setToolTip("Measures of the selected shape in millimetres, from the board's lower-left corner.")
            lay.addRow(info)
            return
        fields = {"x": _spin(-1000, 2000, x0, 2, 0.5, "mm"), "y": _spin(-1000, 2000, y0, 2, 0.5, "mm"),
                  "w": _spin(0.1, 2000, w, 2, 0.5, "mm"), "h": _spin(0.1, 2000, h, 2, 0.5, "mm")}
        tips = {"x": "X of the left edge, measured from the board's lower-left corner.", "y": "Y of the lower edge, measured from the board's lower-left corner.",
                "w": "Width of the rectangle along x.", "h": "Height of the rectangle along y."}

        def commit():
            x, y, ww, hh = (fields[k].value() for k in "xywh")
            self.doc.edit("Edit shape", lambda proj: setattr(
                getattr(proj.problem, {"zone": "zones", "heater": "heaters", "heatsink": "heatsinks"}[kind])[i],
                "polygon", np.array([[x, y], [x + ww, y], [x + ww, y + hh], [x, y + hh]]) / 1000.0),
                merge_key=f"geom{kind}{i}")

        for label, key in (("X", "x"), ("Y", "y"), ("Width", "w"), ("Height", "h")):
            fields[key].setToolTip(tips[key])
            fields[key].valueChanged.connect(lambda _v: commit())
            lay.addRow(label, fields[key])
        info = QLabel(f"Area {area:.2f} mm²")
        info.setToolTip("Area of the rectangle in square millimetres.")
        lay.addRow("", info)


class SolverPanel(QWidget):
    """!
    @brief Model choice, solver settings and the Run button.
    """

    run_requested = Signal()
    cancel_requested = Signal()

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
                   "analytic": QCheckBox("Analytical (Fourier series)"),
                   "fdm": QCheckBox("Finite difference (FDM), comparison"),
                   "solid3d": QCheckBox("3D solid (finite volumes), comparison")}
        tips = {"fvm": "Reference model. Any geometry, full temperature field, exact energy balance. Use it for final answers "
                       "and whenever a warning appears. Cost grows with the number of cells.",
                "lumped": "Fast network (milliseconds). Handles partial copper, vias, heatsinks and several heaters; "
                          "within about 4 % in most cases. Weak when a copper edge crosses the heater, at corners and for thin heaters.",
                "analytic": "Closed-form series (instant). Exact on uniform boards, within a few percent with vias, heatsinks and "
                            "partial copper. Assumes insulated edges and rectangular heaters; unreliable if a copper edge crosses a heater.",
                "solid3d": "The board as a real 3D solid (every copper layer and dielectric gap a slab, vias with their copper area, metal blocks as "
                           "slabs): the only model that does not use one node per copper layer. Steady state only; slower and larger than the FVM, "
                           "within about 1 % of the FVM on ordinary boards; it differs where the layered idea is weakest (a copper pad hardly larger "
                           "than the heater, a copper edge across a footprint).",
                "fdm": "Node-centred finite differences of the same model, to compare discretisations: steady state, animation and power "
                       "profiles. Agrees with the FVM within about 1 %; the FVM is smoother with the grid and is preferred."}
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
        self.local = QCheckBox("Local via and heatsink corrections")
        self.hot = _spin(-50, 1000, 100, 1, 5, "°C")
        self.solver.setToolTip("How the finite-volume system is solved: sparse direct (exact, default), conjugate gradients, or SOR (to compare; slow).")
        self.rings.setToolTip("Number of rings of the thermal network of each heater (thermal resistance steps by distance from the footprint).")
        self.modes.setToolTip("Cosine modes per direction of the analytical series (more modes resolve smaller parts).")
        self.local.setToolTip("Add the local corrections of vias and heatsinks to the analytical series (the Green function of the fin equation around each one).")
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
        self.run.setToolTip("Solve the selected models (F5). The calculation runs in a separate process: the window stays usable and it can be cancelled.")
        self.cancel = QPushButton("Cancel")
        self.cancel.setToolTip("Stop the running calculation at once (Ctrl+.). Nothing is kept from the interrupted run.")
        self.cancel.clicked.connect(self.cancel_requested)
        self.cancel.setVisible(False)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.status = QLabel("")
        self.status.setWordWrap(True)
        self.checks = QLabel("")
        self.checks.setWordWrap(True)
        lay.addWidget(self.run)
        lay.addWidget(self.cancel)
        lay.addWidget(self.progress)
        lay.addWidget(self.status)
        lay.addWidget(self.checks)
        lay.addStretch(1)

        for w in (self.cell, self.rings, self.modes, self.hot):
            w.valueChanged.connect(self._apply)
        self.solver.currentIndexChanged.connect(self._apply)
        self.local.toggled.connect(self._apply)
        doc.changed.connect(self._update_cells)
        doc.changed.connect(self._update_availability)
        doc.state_changed.connect(self.refresh)
        self._base_tips = {k: c.toolTip() for k, c in self.cb.items()}
        self.refresh()

    def _update_availability(self, *_):
        """!
        @brief Grey out the settings of the models that are not selected.
        @param _ Ignored (extra arguments of the Qt signal).
        """
        on = lambda k: self.cb[k].isChecked()                                  # noqa: E731
        for widget, active, why in ((self.solver, on("fvm"), "the FVM"), (self.rings, on("lumped"), "the Lumped model"),
                                    (self.modes, on("analytic"), "the Analytic model"), (self.local, on("analytic"), "the Analytic model")):
            base = widget.property("base_tip")
            if base is None:                                                      # First time: remember the tooltip the control had
                base = widget.toolTip()
                widget.setProperty("base_tip", base)
            widget.setEnabled(active)
            widget.setToolTip(base if active else (base + "\n\n" if base else "") + f"Greyed: used only by {why}, which is not selected or not available for this board.")

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
        self._update_availability()

    def _update_cells(self):
        """!
        @brief Show the number of FVM cells of the current setting.
        """
        b = self.doc.problem.board
        c = self.cell.value()
        n = max(int(round(b.width * 1000 / c)), 2) * max(int(round(b.height * 1000 / c)), 2) * b.layers
        text = f"{n:,} unknowns"
        if self.cb["solid3d"].isChecked():
            # The 3D solid has a slab for every copper layer and four for every gap (plus the blocks)
            n3 = n // b.layers * (b.layers + 4 * (b.layers - 1) + (4 if blocks.has_blocks(self.doc.problem) else 0))
            text += f" (3D solid: {n3:,}" + ("; slow, try a larger cell)" if n3 > 500_000 else ")")
        self.cells_label.setText(text.replace(",", " "))

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
        self._update_availability()

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
        self.cancel.setVisible(running)
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
