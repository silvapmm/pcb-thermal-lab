"""!
@file stackup.py
@brief Stack-up tab: the vertical cross-section of the board drawn to scale and the table that edits every copper layer and every dielectric.
@details The simple stack-up (equal gaps of one FR-4) is edited in the Board panel; here the board can be switched to the advanced stack-up, where each
         copper layer has its own thickness and each gap its own thickness and material. The diagram shows the thickness of every layer in
         micrometres and millimetres and the total thickness of the board; a click on a layer tells its dimensions and properties.
"""

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDoubleSpinBox, QHBoxLayout, QLabel, QPushButton,
                               QSizePolicy, QSplitter, QTableWidget, QVBoxLayout, QWidget)

from ..model import DIELECTRICS, Dielectric
from . import theme as th

_UNITS = (("µm and mm", "both"), ("µm", "um"), ("mm", "mm"))


def stack_layers(problem):
    """!
    @brief The layers of the board from the top face to the bottom face.
    @param problem A Problem.
    @return List of dicts: kind ("copper" or "dielectric"), label, thickness (m), material, k_through, k_inplane, rho, cp, index (layer or gap number, 0-based).
    """
    b = problem.board
    m = b.materials
    out = []
    gaps = b.gap_thicknesses()
    kz, kp, _ = b.gap_properties()
    names = [d.name for d in b.dielectrics] if b.dielectrics is not None else ["FR-4 (standard)"] * len(gaps)
    rho_cp = [(d.rho, d.cp) for d in b.dielectrics] if b.dielectrics is not None else [(m.rho_fr4, m.cp_fr4)] * len(gaps)
    for l in range(b.layers):
        out.append({"kind": "copper", "label": f"Copper L{l + 1}", "thickness": b.copper_thickness[l], "material": "Copper", "k_through": m.k_copper,
                    "k_inplane": m.k_copper, "rho": m.rho_copper, "cp": m.cp_copper, "index": l})
        if l < b.layers - 1:
            out.append({"kind": "dielectric", "label": f"Dielectric {l + 1}-{l + 2}", "thickness": float(gaps[l]), "material": names[l],
                        "k_through": float(kz[l]), "k_inplane": float(kp[l]), "rho": rho_cp[l][0], "cp": rho_cp[l][1], "index": l})
    return out


def format_thickness(metres, unit="both"):
    """!
    @brief Thickness as text in micrometres, millimetres or both.
    @param metres Thickness in metres.
    @param unit "um", "mm" or "both".
    @return Text such as "35 µm (0.035 mm)".
    """
    um, mm = metres * 1e6, metres * 1e3
    if unit == "um":
        return f"{um:.4g} µm"
    if unit == "mm":
        return f"{mm:.4g} mm"
    return f"{um:.4g} µm ({mm:.4g} mm)"


class StackupView(QWidget):
    """!
    @brief Painted cross-section of the board with the dimensions of every layer.
    """

    layer_clicked = Signal(int)          # Index in stack_layers(), -1 for none

    def __init__(self, theme="dark", parent=None):
        """!
        @param theme Colour theme name.
        @param parent Qt parent.
        """
        super().__init__(parent)
        self.theme, self.layers, self.unit, self.true_scale, self.selected = theme, [], "both", False, -1
        self.ambient_note, self._rects = "", []
        self.setMinimumSize(360, 300)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setToolTip("Cross-section of the board, top face first. Click a layer to see its dimensions and properties.")

    def set_theme(self, theme):
        """!
        @brief Change the colour theme.
        @param theme "dark" or "light".
        """
        self.theme = theme
        self.update()

    def set_layers(self, layers, ambient_note=""):
        """!
        @brief Set the layers to draw.
        @param layers List from stack_layers().
        @param ambient_note Text for the top/bottom faces (for example the heat transfer coefficients).
        """
        self.layers, self.ambient_note = layers, ambient_note
        self.selected = min(self.selected, len(layers) - 1)
        self.update()

    def heights(self, total_px):
        """!
        @brief Height in pixels of every layer.
        @details True proportions, or readable: copper layers get at least 9 pixels and the dielectrics share the rest in proportion to their thickness
                 (never less than 12 pixels), so the thin copper is visible next to a 1.5 mm core.
        @param total_px Height available.
        @return List of floats.
        """
        t = [l["thickness"] for l in self.layers]
        total = sum(t) or 1.0
        if self.true_scale:
            return [max(total_px * x / total, 1.0) for x in t]
        cu = [9.0 if l["kind"] == "copper" else 0.0 for l in self.layers]
        diel = [x for x, l in zip(t, self.layers) if l["kind"] == "dielectric"]
        room = max(total_px - sum(cu), 12.0 * len(diel))
        out = []
        for x, l, c in zip(t, self.layers, cu):
            out.append(c if l["kind"] == "copper" else max(room * x / (sum(diel) or 1.0), 12.0))
        scale = total_px / (sum(out) or 1.0)
        return [h * scale for h in out]

    def paintEvent(self, e):
        """!
        @brief Draw the cross-section: the layers as bars, dimension labels on the right and the total thickness on the left.
        @param e QPaintEvent.
        """
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        c = th.colors(self.theme)
        p.fillRect(self.rect(), QColor(c["canvas"]))
        p.setPen(QColor(c["text"]))
        if not self.layers:
            p.drawText(self.rect(), Qt.AlignCenter, "No layers")
            return
        w, h = self.width(), self.height()
        top, bottom = 38, 44
        bar_x, bar_w = 90, max(w * 0.30, 120)
        hs = self.heights(h - top - bottom)
        y = float(top)
        self._rects = []
        font = QFont(self.font())
        font.setPointSizeF(9.0)
        p.setFont(font)
        # Top face note
        p.setPen(QColor(c["muted"]))
        p.drawText(QPointF(bar_x, top - 22), "Top face (layer 1)")
        arrow = QPolygonF([QPointF(bar_x + bar_w + 16, top - 20), QPointF(bar_x + bar_w + 26, top - 20), QPointF(bar_x + bar_w + 21, top - 8)])
        p.setBrush(QBrush(QColor(c["muted"])))
        p.drawPolygon(arrow)
        t_total = sum(l["thickness"] for l in self.layers)
        for i, (layer, hp) in enumerate(zip(self.layers, hs)):
            rect = QRectF(bar_x, y, bar_w, hp)
            self._rects.append(rect)
            if layer["kind"] == "copper":
                fill = QColor(c["copper"])
            else:
                k = layer["k_through"]
                fill = QColor("#4a6f5a") if k < 1.0 else QColor("#6c8f9d") if k < 10 else QColor("#9aa7b4")
                fill = QColor(c["board"]) if k <= 0.35 and layer["material"].startswith("FR-4") else fill
            p.setBrush(QBrush(fill))
            p.setPen(QPen(QColor("white") if i == self.selected else QColor(c["border"]), 2.0 if i == self.selected else 1.0))
            p.drawRect(rect)
            # Label inside the bar (when there is room) and the dimension to the right
            p.setPen(QColor("white"))
            if hp >= 14:
                text = layer["label"] if layer["kind"] == "copper" else layer["material"]
                p.drawText(rect.adjusted(6, 0, -4, 0), Qt.AlignVCenter | Qt.AlignLeft, p.fontMetrics().elidedText(text, Qt.ElideRight, int(bar_w) - 10))
            p.setPen(QColor(c["text"]))
            ymid = y + hp / 2.0
            p.drawLine(QPointF(bar_x + bar_w, ymid), QPointF(bar_x + bar_w + 14, ymid))
            p.drawText(QPointF(bar_x + bar_w + 18, ymid + 4), f"{layer['label'] if layer['kind'] == 'copper' else 'Gap ' + str(layer['index'] + 1) + '-' + str(layer['index'] + 2)}"
                       f"  {format_thickness(layer['thickness'], self.unit)}")
            y += hp
        # Bottom face and total thickness bracket
        p.setPen(QColor(c["muted"]))
        p.drawText(QPointF(bar_x, y + 26), f"Bottom face (layer {sum(1 for l in self.layers if l['kind'] == 'copper')})")
        p.setPen(QPen(QColor(c["accent"]), 1.5))
        bx = bar_x - 14
        p.drawLine(QPointF(bx, top), QPointF(bx, y))
        p.drawLine(QPointF(bx - 4, top), QPointF(bx + 4, top))
        p.drawLine(QPointF(bx - 4, y), QPointF(bx + 4, y))
        p.save()
        p.translate(bx - 8, (top + y) / 2.0)
        p.rotate(-90)
        p.setPen(QColor(c["accent"]))
        p.drawText(QRectF(-110, -12, 220, 18), Qt.AlignCenter, "Total " + format_thickness(t_total, self.unit if self.unit != "both" else "both"))
        p.restore()
        if not self.true_scale:
            p.setPen(QColor(c["muted"]))
            p.drawText(QPointF(8, h - 6), "Not to scale: thin layers enlarged to stay visible (choose 'True proportions' for the real ratios)")
        p.end()

    def mousePressEvent(self, e):
        """!
        @brief Select the layer under the cursor.
        @param e QMouseEvent.
        """
        pos = e.position()
        self.selected = next((i for i, r in enumerate(self._rects) if r.contains(pos)), -1)
        self.layer_clicked.emit(self.selected)
        self.update()


class StackupEditor(QTableWidget):
    """!
    @brief Table with one row per copper layer and per dielectric gap, editing the board of the document.
    """

    COLUMNS = ("Layer", "Material", "Thickness (µm)", "k through (W/mK)", "k in-plane (W/mK)", "ρ (kg/m³)", "cp (J/kgK)")
    TIPS = ("Copper layer or dielectric gap between two copper layers, from the top face down.",
            "Dielectric material. Choosing one fills the four properties with typical values (indicative; edit them for your laminate). Copper is described in the Board panel (Materials).",
            "Thickness in micrometres (1 oz copper is 35 µm, 0.5 oz 17.5 µm, 2 oz 70 µm; a 0.2 mm prepreg is 200 µm).",
            "Thermal conductivity across the thickness (between the copper layers), W/mK.",
            "Thermal conductivity along the plane (spreading inside the dielectric), W/mK.",
            "Density in kg/m³ (time simulation only).",
            "Specific heat in J/kgK (time simulation only).")

    def __init__(self, doc, parent=None):
        """!
        @param doc The Document.
        @param parent Qt parent.
        """
        super().__init__(0, len(self.COLUMNS), parent)
        self.doc, self._updating = doc, False
        self.setHorizontalHeaderLabels(list(self.COLUMNS))
        for i, tip in enumerate(self.TIPS):
            self.horizontalHeaderItem(i).setToolTip(tip)
        self.setSelectionMode(QAbstractItemView.NoSelection)
        self.setToolTip("Every copper layer and dielectric gap of the advanced stack-up, top face first. Edit the thickness and the material properties of each.")
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.setMinimumWidth(520)
        doc.changed.connect(self.refresh)
        self.refresh()

    def _spin(self, value, lo, hi, decimals, enabled, tip, slot):
        """!
        @brief A spin box for a cell.
        @param value Initial value.
        @param lo Minimum.
        @param hi Maximum.
        @param decimals Decimals.
        @param enabled False for values taken from elsewhere (copper properties).
        @param tip Tooltip.
        @param slot Called with the new value.
        @return QDoubleSpinBox.
        """
        s = QDoubleSpinBox()
        s.setRange(lo, hi)
        s.setDecimals(decimals)
        s.setValue(value)
        s.setKeyboardTracking(False)
        s.setEnabled(enabled)
        s.setToolTip(tip)
        s.setFrame(False)
        if enabled:
            s.valueChanged.connect(slot)
        return s

    def refresh(self):
        """!
        @brief Rebuild the rows from the board (only in the advanced stack-up; empty otherwise).
        """
        pr = self.doc.problem
        b = pr.board
        self._updating = True
        self.setRowCount(0)
        if b.is_advanced():
            layers = stack_layers(pr)
            self.setRowCount(len(layers))
            for r, ly in enumerate(layers):
                self.setCellWidget(r, 0, QLabel("  " + ly["label"]))
                copper = ly["kind"] == "copper"
                i = ly["index"]
                if copper:
                    self.setCellWidget(r, 1, QLabel("  Copper"))
                    self.cellWidget(r, 1).setToolTip("Copper properties are set in the Board panel (Materials).")
                else:
                    combo = QComboBox()
                    for name, *_ in DIELECTRICS:
                        combo.addItem(name)
                    combo.addItem("Custom")
                    idx = combo.findText(ly["material"])
                    combo.setCurrentIndex(idx if idx >= 0 else combo.count() - 1)
                    combo.setToolTip(self.TIPS[1])
                    combo.currentIndexChanged.connect(lambda _x, g=i, cb=combo: self._choose(g, cb))
                    self.setCellWidget(r, 1, combo)
                lo = 1.0 if copper else 5.0
                self.setCellWidget(r, 2, self._spin(ly["thickness"] * 1e6, lo, 20000.0, 1, True, self.TIPS[2],
                                                    (lambda v, k=i: self._set_copper(k, v)) if copper else (lambda v, g=i: self._set_gap(g, thickness=v * 1e-6))))
                cols = ((ly["k_through"], "k_through", 0.01, 2000.0, 2), (ly["k_inplane"], "k_inplane", 0.01, 2000.0, 2),
                        (ly["rho"], "rho", 10.0, 30000.0, 0), (ly["cp"], "cp", 10.0, 5000.0, 0))
                for c, (val, key, a, z, dec) in enumerate(cols):
                    self.setCellWidget(r, 3 + c, self._spin(val, a, z, dec, not copper, self.TIPS[3 + c] if not copper else "Copper: set in the Board panel (Materials).",
                                                            (lambda v, g=i, k=key: self._set_gap(g, **{k: v})) if not copper else None))
                self.setRowHeight(r, 26)
            self.resizeColumnsToContents()
            self.setColumnWidth(0, 100)
            self.setColumnWidth(1, 190)
            for c in range(2, 7):
                self.setColumnWidth(c, 92)
        self._updating = False

    def _set_copper(self, layer, um):
        """!
        @brief Change the thickness of one copper layer.
        @param layer 0-based layer.
        @param um Thickness in micrometres.
        """
        if self._updating:
            return

        def mutate(proj):
            b = proj.problem.board
            b.copper_thickness[layer] = um * 1e-6
            b.thickness = b.total_thickness()

        self.doc.edit("Copper thickness", mutate, merge_key=f"cu{layer}")

    def _set_gap(self, gap, **fields):
        """!
        @brief Change properties of one dielectric gap (SI units).
        @param gap 0-based gap.
        @param fields Dielectric attribute names and values.
        """
        if self._updating:
            return

        def mutate(proj):
            b = proj.problem.board
            for k, v in fields.items():
                setattr(b.dielectrics[gap], k, v)
            b.thickness = b.total_thickness()

        self.doc.edit("Dielectric", mutate, merge_key=f"gap{gap}{sorted(fields)}")

    def _choose(self, gap, combo):
        """!
        @brief Apply a material preset to a gap.
        @param gap 0-based gap.
        @param combo The material combo box.
        """
        if self._updating:
            return
        name = combo.currentText()
        preset = next((d for d in DIELECTRICS if d[0] == name), None)

        def mutate(proj):
            d = proj.problem.board.dielectrics[gap]
            d.name = name
            if preset is not None:
                d.k_through, d.k_inplane, d.rho, d.cp = preset[1:]

        self.doc.edit("Dielectric material", mutate)


class StackupPage(QWidget):
    """!
    @brief The Stack-up tab: mode switch, cross-section, and the table of layers.
    """

    def __init__(self, doc, theme="dark", parent=None):
        """!
        @param doc The Document.
        @param theme Colour theme name.
        @param parent Qt parent.
        """
        super().__init__(parent)
        self.doc, self._updating = doc, False
        lay = QVBoxLayout(self)
        bar = QHBoxLayout()
        self.mode = QComboBox()
        self.mode.addItem("Simple: equal layers, one FR-4", False)
        self.mode.addItem("Advanced: each layer on its own", True)
        self.mode.setToolTip("Simple: the Board panel sets the thickness, the copper and the FR-4 of equal gaps. Advanced: every copper layer and every dielectric "
                             "gap has its own thickness and material (all models use them). Switching keeps the same board.")
        self.unit = QComboBox()
        for label, key in _UNITS:
            self.unit.addItem(label, key)
        self.unit.setToolTip("Units of the dimensions in the diagram.")
        self.scale = QComboBox()
        self.scale.addItem("Readable (thin layers enlarged)", False)
        self.scale.addItem("True proportions", True)
        self.scale.setToolTip("True proportions draw each layer with its real thickness ratio (35 µm copper next to 1.5 mm of laminate is a thin line).")
        for text, w in (("Stack-up ", self.mode), ("  Units ", self.unit), ("  Scale ", self.scale)):
            bar.addWidget(QLabel(text))
            bar.addWidget(w)
        bar.addStretch(1)
        lay.addLayout(bar)
        split = QSplitter(Qt.Horizontal)
        self.view = StackupView(theme)
        self.editor = StackupEditor(doc)
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        self.note = QLabel("")
        self.note.setWordWrap(True)
        rl.addWidget(self.note)
        rl.addWidget(self.editor, 1)
        split.addWidget(self.view)
        split.addWidget(right)
        split.setStretchFactor(0, 2)
        split.setStretchFactor(1, 3)
        lay.addWidget(split, 1)
        self.info = QLabel("Click a layer in the diagram to see its dimensions.")
        self.info.setWordWrap(True)
        self.info.setStyleSheet("padding: 4px;")
        lay.addWidget(self.info)

        self.mode.currentIndexChanged.connect(self._mode_changed)
        self.unit.currentIndexChanged.connect(self._look_changed)
        self.scale.currentIndexChanged.connect(self._look_changed)
        self.view.layer_clicked.connect(self._show_layer)
        doc.changed.connect(self.refresh)
        self.refresh()

    def set_theme(self, theme):
        """!
        @brief Change the colour theme.
        @param theme "dark" or "light".
        """
        self.view.set_theme(theme)

    def refresh(self):
        """!
        @brief Redraw from the document.
        """
        pr = self.doc.problem
        b = pr.board
        self._updating = True
        self.mode.setCurrentIndex(1 if b.is_advanced() else 0)
        self._updating = False
        self.editor.setVisible(b.is_advanced())
        layers = stack_layers(pr)
        self.view.set_layers(layers)
        self._look_changed()
        if b.is_advanced():
            self.note.setText(f"Advanced stack-up: {b.layers} copper layers, {len(b.dielectrics)} dielectrics, total thickness "
                              f"{format_thickness(b.total_thickness(), 'both')}. Copper conductivity and the via plating are in the Board panel.")
        else:
            self.note.setText("Simple stack-up: the Board panel sets the total thickness, the copper thickness of the layers and the FR-4 properties; "
                              "the gaps are equal. Switch to Advanced to describe each layer.")
        if self.view.selected >= 0:
            self._show_layer(self.view.selected)

    def _look_changed(self, *_):
        """!
        @brief Apply the unit and scale choices to the diagram.
        """
        self.view.unit = self.unit.currentData()
        self.view.true_scale = bool(self.scale.currentData())
        self.view.update()

    def _mode_changed(self, _i):
        """!
        @brief Switch the board between the simple and the advanced stack-up.
        @param _i Ignored.
        """
        if self._updating:
            return
        advanced = bool(self.mode.currentData())

        def mutate(proj):
            if advanced:
                proj.problem.board.make_advanced()
            else:
                proj.problem.board.make_simple()

        if advanced != self.doc.problem.board.is_advanced():
            self.doc.edit("Stack-up mode", mutate)

    def _show_layer(self, index):
        """!
        @brief Describe the clicked layer.
        @param index Index in the list of layers, -1 for none.
        """
        layers = stack_layers(self.doc.problem)
        if not 0 <= index < len(layers):
            self.info.setText("Click a layer in the diagram to see its dimensions.")
            return
        ly = layers[index]
        pr = self.doc.problem
        what = ""
        if ly["kind"] == "copper":
            l = ly["index"]
            counts = [(len([z for z in pr.zones if z.layer == l]), "zones"), (len([h for h in pr.heaters if h.layer == l]), "heaters"),
                      (len([s for s in pr.heatsinks if s.layer == l]), "heatsinks")]
            what = "; on this layer: " + ", ".join(f"{n} {w}" for n, w in counts if n) if any(n for n, _ in counts) else "; nothing drawn on this layer"
            if pr.vias:
                what += f"; {len(pr.vias)} vias cross it"
        self.info.setText(f"<b>{ly['label'] if ly['kind'] == 'copper' else 'Dielectric ' + str(ly['index'] + 1) + '-' + str(ly['index'] + 2) + ' (' + ly['material'] + ')'}</b>: "
                          f"thickness {format_thickness(ly['thickness'], 'both')}; k through {ly['k_through']:g} W/mK, in-plane {ly['k_inplane']:g} W/mK; "
                          f"density {ly['rho']:g} kg/m³, specific heat {ly['cp']:g} J/kgK{what}.")
