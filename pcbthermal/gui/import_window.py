#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file import_window.py
@brief The Gerber import window ("Import Gerber board..." in the File menu): a stepper header (Files and layers, Parts, Model), Back / Next (Import on the last step) and an "Import now" button.
@details Designed like the Power Calculator: a separate window opened from the menu, every colour a token of `pcbthermal.gui.theme` read when it is painted (so a live theme switch
         recolours it), every control with a tooltip. The window talks only to an `ImportSession`.
         Step 1, files and layers: folder, ZIP or files chooser, the detected function of every file in an editable list (two files claiming one function are shown), the layer count with the
         proposed stack-up, the outline, the drills and a zoomable preview of the selected layer. Step 2, parts: the parts from the paste layer, the placement file and the X3 layer with power, Tj max,
         role and the Source column, the shape of the heat source (always editable), the frame check and a preview whose red openings are clicked to make a heat source. Step 3, model: the copper
         mapping (faces; the others under Advanced), the pixel, the cell, the vias, the memory verdict and the warnings. Import builds the project; when the open project already holds an import the
         ReimportDialog asks Replace, Update, Add files or Cancel.
"""

import html
import threading

import numpy as np
from PySide6.QtCore import QEvent, QEventLoop, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                               QMessageBox, QPushButton, QRadioButton, QSizePolicy, QStackedWidget, QTableWidget, QTableWidgetItem, QToolTip, QVBoxLayout, QWidget)

from ..gerber import GerberError
from ..memory import MemoryGuardError
from . import theme as th
from .import_session import COPPER, COPPER_BOTTOM, COPPER_TOP, ROLES, UNIQUE, ImportSession
from .panels import WarningList

STEP_TITLES = ["Files and layers", "Parts", "Model"]
STEP_SUBTITLES = ["Choose the folder, ZIP or files, check the function of every file and the stack-up.",
                  "Turn paste openings into heat sources: click an opening, give a power in W, choose the shape.",
                  "Choose how the copper is given to the models, the cell, the vias; read the memory verdict."]

class Preview(QWidget):
    """!
    @brief Zoomable preview of the board: copper layers, outline and drilled holes (mouse wheel zooms, drag pans, double click shows all).
    """

    clicked = Signal(float, float, bool)

    def __init__(self, session: ImportSession, mode: str = "layers"):
        """!
        @param session The import session whose board is drawn.
        @param mode "layers" (step 1), "parts" (step 2: paste openings and heat sources) or "model" (step 3: the solver grid).
        """
        super().__init__()
        self.session, self.mode = session, mode
        self.side, self.cell, self.selected_part = "top", 0.0, None
        self.show_layers = {"copper": True, "outline": True, "holes": True, "paste": True, "sources": True}
        self.selected = COPPER_TOP                                   # Role of the layer drawn at full strength
        self.zoom, self.pan, self._press, self._moved, self._last = 1.0, QPointF(0, 0), None, False, None
        self._images = {}                                            # (role, theme name, id of the array) -> QImage
        self.setMinimumSize(360, 340)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setToolTip("Preview of the board. Mouse wheel zooms, drag pans, double click shows the whole board. The layer selected in the file list is drawn at full strength.")

    def reset_view(self):
        """!
        @brief Show the whole board again.
        @return None
        """
        self.zoom, self.pan = 1.0, QPointF(0, 0)
        self.update()

    @staticmethod
    def _tinted(coverage: np.ndarray, color: QColor) -> QImage:
        """!
        @brief A colour image whose alpha is a coverage array.
        @param coverage uint8 array (rows, columns), 0 to 255.
        @param color QColor of the copper.
        @return QImage (a copy, so the array may go away).
        """
        rgba = np.zeros(coverage.shape + (4,), np.uint8)
        rgba[..., 0], rgba[..., 1], rgba[..., 2], rgba[..., 3] = color.red(), color.green(), color.blue(), coverage
        return QImage(rgba.data, coverage.shape[1], coverage.shape[0], 4 * coverage.shape[1], QImage.Format_RGBA8888).copy()

    def _image(self, role: str, coverage: np.ndarray, colors: dict) -> QImage:
        """!
        @brief The tinted image of a copper layer for the current theme (cached).
        @param role Role of the layer.
        @param coverage Coverage array.
        @param colors Colour table of the theme.
        @return QImage
        """
        key = (role, th.current_name(), id(coverage))
        if key not in self._images:
            self._images = {k: v for k, v in self._images.items() if k[1] == th.current_name() and k[2] != id(coverage) or k == key}   # Drop the images of another theme or board
            tone = "copper" if role == COPPER_TOP else "heatsink" if role == COPPER_BOTTOM else "link_visited"
            self._images[key] = self._tinted(coverage, QColor(colors[tone]))
        return self._images[key]

    def _geometry(self):
        """!
        @brief Scale (pixels per mm) and the top-left pixel of the board in the current view.
        @return tuple (scale, ox, oy).
        """
        b = self.session.board()
        s = min((self.width() - 20) / b.width, (self.height() - 20) / b.height) * self.zoom
        return s, (self.width() - b.width * s) / 2 + self.pan.x(), (self.height() - b.height * s) / 2 + self.pan.y()

    def to_px(self, x: float, y: float) -> QPointF:
        """!
        @brief Board millimetres (Gerber axes) to widget pixels.
        @param x X (mm).
        @param y Y (mm).
        @return QPointF
        """
        b = self.session.board()
        s, ox, oy = self._geometry()
        return QPointF(ox + (x - b.box[0]) * s, oy + (b.box[3] - y) * s)

    def from_px(self, p: QPointF) -> tuple:
        """!
        @brief Widget pixels to board millimetres.
        @param p QPointF.
        @return tuple (x, y) in mm.
        """
        b = self.session.board()
        s, ox, oy = self._geometry()
        return b.box[0] + (p.x() - ox) / s, b.box[3] - (p.y() - oy) / s

    def paintEvent(self, ev):
        """!
        @brief Paint the board with the colours of the current theme.
        @param ev Paint event.
        @return None
        """
        c = th.colors(th.current_name())
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(c["canvas"]))
        b = self.session.board()
        if b is None:
            p.setPen(QColor(c["muted"]))
            p.drawText(self.rect(), Qt.AlignCenter, "No board yet: complete the file list.")
            p.end()
            return
        s, ox, oy = self._geometry()
        rect = QRectF(ox, oy, b.width * s, b.height * s)
        p.fillRect(rect, QColor(c["board"]).darker(150))
        if self.show_layers["copper"]:
            for role, _, cov in reversed(b.copper):                      # The bottom layer first, the top one over it
                p.setOpacity(1.0 if role == self.selected or (self.mode != "layers" and role == COPPER_TOP) else 0.35)
                p.drawImage(rect, self._image(role, cov, c))
        p.setOpacity(1.0)
        if self.show_layers["outline"]:
            p.setPen(QPen(QColor(c["doc_note_edge"]), 1.6))
            p.setBrush(Qt.NoBrush)
            for outer, holes in b.outline:
                for ring in [outer] + list(holes):
                    p.drawPolygon(QPolygonF([self.to_px(x, y) for x, y in ring]))
        if self.mode == "model" and self.cell > 0:
            p.setPen(QPen(th.qcolor(c["solver_grid"]), 1))
            x0, y0, x1, y1 = b.box
            for k in range(int((x1 - x0) / self.cell) + 2):
                p.drawLine(self.to_px(x0 + k * self.cell, y0), self.to_px(x0 + k * self.cell, y1))
            for k in range(int((y1 - y0) / self.cell) + 2):
                p.drawLine(self.to_px(x0, y0 + k * self.cell), self.to_px(x1, y0 + k * self.cell))
        if self.show_layers["holes"]:
            p.setBrush(Qt.NoBrush)
            for h in b.holes:
                # A via-sized hole in the via colour, a larger one (a component hole) in the warning colour, a non-plated one in the muted colour
                tone = "muted" if not h.plated else "via" if h.diameter <= self.session.via_max_mm else "warn"
                p.setPen(QPen(QColor(c[tone]), 1.2))
                r = max(h.diameter * s / 2, 1.6)
                p.drawEllipse(self.to_px(h.x, h.y), r, r)
        if self.mode == "parts":
            self._paint_parts(p, c)
        p.setPen(QColor(c["muted"]))
        p.drawText(10, self.height() - 8, f"{b.width:.1f} x {b.height:.1f} mm   zoom {self.zoom:.1f}x")
        p.end()

    def _paint_parts(self, p, c):
        """!
        @brief Paste openings (matched in the text colour, unmatched in red), the heat sources (dashed) and the selected part (solid, accent).
        @param p QPainter.
        @param c Colour table of the theme.
        @return None
        """
        sx = self.session
        ops = sx.openings()
        owned = sx.owned_indices()
        sel = sx.part(self.selected_part) if self.selected_part else None
        sel_idx = set(sx._owners().get(sel.designator, [])) if sel else set()
        if self.show_layers["paste"]:
            for i, o in enumerate(ops):
                if o.side != self.side:
                    continue
                r = QRectF(self.to_px(o.bbox[0], o.bbox[3]), self.to_px(o.bbox[2], o.bbox[1]))
                if i not in owned:
                    p.setPen(QPen(QColor(c["bad"]), 1.6))
                    fill = QColor(c["bad"])
                else:
                    p.setPen(QPen(QColor(c["accent"]) if i in sel_idx else QColor(c["text"]), 1.6 if i in sel_idx else 1))
                    fill = QColor(c["text"])
                fill.setAlpha(80)
                p.setBrush(fill)
                p.drawRect(r)
        for q in sx.parts():
            if sx.is_source(q) and q.side == self.side and self.show_layers["sources"]:
                p.setPen(QPen(QColor(c["heater"]), 1.5, Qt.DashLine))
                p.setBrush(Qt.NoBrush)
                p.drawPolygon(QPolygonF([self.to_px(x, y) for x, y in q.polygon_mm]))
        if sel is not None and sel.polygon_mm:
            fill = QColor(c["heater"])
            fill.setAlpha(55)
            p.setPen(QPen(QColor(c["accent"]), 2.2))
            p.setBrush(fill)
            p.drawPolygon(QPolygonF([self.to_px(x, y) for x, y in sel.polygon_mm]))
            f = QFont(self.font())
            f.setBold(True)
            p.setFont(f)
            p.setPen(QColor(c["text"]))
            top = max(sel.polygon_mm, key=lambda q: q[1])
            p.drawText(self.to_px(top[0], top[1]) + QPointF(-4, -6), sel.designator)

    def wheelEvent(self, ev):
        """!
        @brief Zoom about the pointer.
        @param ev Wheel event.
        @return None
        """
        if self.session.board() is None:
            return
        pos = ev.position()
        before = self.from_px(pos)
        self.zoom = float(np.clip(self.zoom * 1.25 ** (ev.angleDelta().y() / 120.0), 1.0, 40.0))
        self.pan += pos - self.to_px(*before)                          # Keep the point under the pointer fixed
        self.update()

    def mousePressEvent(self, ev):
        """!
        @brief Start a drag.
        @param ev Mouse event.
        @return None
        """
        self._press, self._moved, self._last = ev.position(), False, ev.position()

    def mouseMoveEvent(self, ev):
        """!
        @brief Pan while the button is down.
        @param ev Mouse event.
        @return None
        """
        if self._press is None or not (ev.buttons() & Qt.LeftButton):
            return
        if (ev.position() - self._press).manhattanLength() > 4:
            self._moved = True
        if self._moved:
            self.pan += ev.position() - self._last
            self.update()
        self._last = ev.position()

    def mouseReleaseEvent(self, ev):
        """!
        @brief End a drag.
        @param ev Mouse event.
        @return None
        """
        if self._press is not None and not self._moved and self.session.board() is not None and self.mode == "parts":
            x, y = self.from_px(ev.position())
            self.clicked.emit(x, y, bool(ev.modifiers() & Qt.ControlModifier))
        self._press = None

    def mouseDoubleClickEvent(self, ev):
        """!
        @brief Show the whole board.
        @param ev Mouse event.
        @return None
        """
        self.reset_view()


class Step1Page(QWidget):
    """!
    @brief Step 1, files and layers: the source, the file list with the editable function, the stack-up, the outline and drills, and the preview.
    """

    def __init__(self, win: "ImportBoardWindow"):
        """!
        @param win The import window (the file choosers and the reading go through it).
        """
        super().__init__()
        self.win, self.session = win, win.session
        self._filling = False
        lay = QHBoxLayout(self)
        left = QVBoxLayout()
        row = QHBoxLayout()
        row.addWidget(QLabel("Folder, ZIP or files"))
        self.source = QLineEdit()
        self.source.setToolTip("A folder or a ZIP archive with the Gerber files, the Excellon drill files and, optionally, the placement file of the same board. Type a path and press Enter to read it.")
        self.source.returnPressed.connect(lambda: self.win.open_path(self.source.text()))
        row.addWidget(self.source, 1)
        for text, tip, fn in (("Folder…", "Choose a folder of fabrication files.", self._folder), ("ZIP…", "Choose a ZIP archive of fabrication files. Nothing is extracted to disk.", self._zip),
                              ("Files…", "Choose the fabrication files one by one (select several).", self._files)):
            b = QPushButton(text)
            b.setToolTip(tip)
            b.clicked.connect(fn)
            row.addWidget(b)
        left.addLayout(row)
        self.box = QGroupBox("Files found")
        gl = QVBoxLayout(self.box)
        note = QLabel("The function of each file was detected from its Gerber X2 attributes, the Excellon header or its name. Check it and change it when it is wrong.")
        note.setWordWrap(True)
        th.hint(note)
        gl.addWidget(note)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Use", "File", "Size", "Function", "Detected from"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setMinimumHeight(240)
        self.table.setToolTip("One row per file. Untick a file to leave it out, or change its function. The models read copper, outline and drills; paste and placement give the parts; "
                              "mask and legend files are not used. Two files claiming one function are shown in red.")
        self.table.cellChanged.connect(self._use_changed)
        self.table.itemSelectionChanged.connect(self._row_selected)
        gl.addWidget(self.table)
        self.problem = QLabel("")
        self.problem.setWordWrap(True)
        self.problem.setToolTip("What stops the import (red) or what it goes on without (muted).")
        gl.addWidget(self.problem)
        left.addWidget(self.box, 1)
        g = QGroupBox("Board")
        f = QFormLayout(g)
        self.layers_label = QLabel("")
        self.layers_label.setWordWrap(True)
        self.layers_label.setToolTip("Number of copper layers (the copper files in use) and the typical stack-up of the program for that count, not a fabricator table. "
                                     "The files do not carry the dielectrics; edit them in the Stack-up tab after the import.")
        f.addRow("Copper layers", self.layers_label)
        self.outline_label = QLabel("")
        self.outline_label.setWordWrap(True)
        self.outline_label.setToolTip("Size and area of the board outline (the profile layer). Without an outline the box of the copper is used.")
        f.addRow("Outline", self.outline_label)
        self.drill_label = QLabel("")
        self.drill_label.setWordWrap(True)
        self.drill_label.setToolTip("Plated holes up to 0.5 mm are vias and are imported; larger plated holes are component holes (a lead is not modelled); non-plated holes are ignored.")
        f.addRow("Drills", self.drill_label)
        left.addWidget(g)
        lay.addLayout(left, 11)
        right = QVBoxLayout()
        bar = QHBoxLayout()
        self.preview = Preview(self.session)
        self.layer_pick = QComboBox()
        self.layer_pick.setToolTip("The copper layer drawn at full strength; the others are faded. Selecting a copper file in the list does the same.")
        self.layer_pick.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.layer_pick.setMinimumContentsLength(14)
        self.layer_pick.currentTextChanged.connect(self._layer_picked)
        bar.addWidget(self.layer_pick)
        for key, label in (("copper", "Copper"), ("outline", "Outline"), ("holes", "Holes")):
            c = QCheckBox(label)
            c.setChecked(True)
            c.setToolTip(f"Show or hide the {label.lower()} in the preview.")
            c.toggled.connect(lambda on, k=key: (self.preview.show_layers.__setitem__(k, on), self.preview.update()))
            bar.addWidget(c)
        bar.addStretch(1)
        right.addLayout(bar)
        right.addWidget(self.preview, 1)
        cap = QLabel("Preview of the selected copper layer. Rings are holes: vias up to 0.5 mm, larger plated holes in the warning colour, non-plated ones muted. Wheel zooms, drag pans.")
        cap.setWordWrap(True)
        th.hint(cap)
        right.addWidget(cap)
        lay.addLayout(right, 9)
        self.refresh()

    # -- choosers
    def _folder(self):
        """!
        @brief Choose a folder.
        @return None
        """
        d = QFileDialog.getExistingDirectory(self, "Folder of fabrication files")
        if d:
            self.win.open_path(d)

    def _zip(self):
        """!
        @brief Choose a ZIP.
        @return None
        """
        f, _ = QFileDialog.getOpenFileName(self, "ZIP of fabrication files", "", "ZIP (*.zip)")
        if f:
            self.win.open_path(f)

    def _files(self):
        """!
        @brief Choose several files.
        @return None
        """
        fs, _ = QFileDialog.getOpenFileNames(self, "Fabrication files", "", "All files (*)")
        if fs:
            self.win.open_path(fs)

    # -- table
    def refresh(self):
        """!
        @brief Fill the table, the messages and the summaries from the session.
        @return None
        """
        sx = self.session
        c = th.colors(th.current_name())
        self._filling = True
        t = self.table
        names = [t.item(i, 1).text() if t.item(i, 1) else None for i in range(t.rowCount())]
        if names != [f.name for f in sx.files]:
            self._build_rows()
        claims = {}
        for f in sx.used():
            if f.role in UNIQUE:
                claims[f.role] = claims.get(f.role, 0) + 1
        for i, f in enumerate(sx.files):
            clash = f.use and claims.get(f.role, 0) > 1
            for col in (1, 2, 4):
                item = t.item(i, col)
                item.setForeground(QColor(c["bad"] if clash or (f.use and f.error) else c["text"] if f.use else c["muted"]))
            t.item(i, 0).setCheckState(Qt.Checked if f.use else Qt.Unchecked)
            cb = t.cellWidget(i, 3)
            if cb.currentText() != f.role:
                cb.blockSignals(True)
                cb.setCurrentText(f.role)
                cb.blockSignals(False)
            t.item(i, 4).setText(f.how + (f"; {f.error}" if f.error else ""))
        self._filling = False
        self.source.setText(sx.source_text)
        self.box.setTitle(f"Files found ({len(sx.files)})")
        probs, notes = sx.problems(), sx.notes()
        text = ""
        if probs:
            text += f'<span style="color:{c["bad"]}">' + "<br>".join(html.escape(p) for p in probs) + "</span>"
        if not probs:
            text += f'<span style="color:{c["ok"]}">Step 1 is complete.</span>'
        if notes:
            text += f'<br><span style="color:{c["muted"]}">' + "<br>".join(html.escape(n) for n in notes) + "</span>"
        self.problem.setText(text if sx.files else "")
        layers = sx.layers()
        self.layers_label.setText(f"{len(layers)}: {sx.stackup_text().split(': ', 1)[1]}" if layers else "none")
        b = sx.board()
        if b is not None and b.outline_area_mm2 is not None:
            self.outline_label.setText(f"{b.width:.2f} x {b.height:.2f} mm, area {b.outline_area_mm2:.1f} mm², {len(b.outline)} board(s)")
        elif b is not None:
            self.outline_label.setText(f"none: the box of the copper, {b.width:.2f} x {b.height:.2f} mm")
        else:
            self.outline_label.setText("-")
        v, comp, nonplated = sx.vias()
        self.drill_label.setText(f"{v} vias, {comp} component holes, {nonplated} non-plated holes" if b is not None else "-")
        picked = [l.role for l in layers]
        if picked != [self.layer_pick.itemText(i) for i in range(self.layer_pick.count())]:
            self.layer_pick.blockSignals(True)
            self.layer_pick.clear()
            self.layer_pick.addItems(picked)
            self.layer_pick.blockSignals(False)
        if picked and self.preview.selected not in picked:
            self.preview.selected = picked[0]
        if picked:
            self.layer_pick.setCurrentText(self.preview.selected)
        self.preview.update()

    def _build_rows(self):
        """!
        @brief Make the rows of the table (one per file) with the function combos.
        @return None
        """
        t = self.table
        t.setRowCount(len(self.session.files))
        for r, f in enumerate(self.session.files):
            it = QTableWidgetItem()
            it.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            t.setItem(r, 0, it)
            for col, text in ((1, f.name), (2, f"{f.size / 1000:.1f} kB"), (4, f.how)):
                item = QTableWidgetItem(text)
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                t.setItem(r, col, item)
            cb = QComboBox()
            cb.addItems(ROLES)
            cb.setCurrentText(f.role)
            cb.setToolTip("What the file is. Inner copper layers are numbered from the top. Choose Ignore to leave the file out.")
            cb.currentTextChanged.connect(lambda text, i=r: self._role_changed(i, text))
            t.setCellWidget(r, 3, cb)
        hh = t.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.Fixed)
        t.setColumnWidth(3, 200)
        hh.setSectionResizeMode(4, QHeaderView.Stretch)

    def _role_changed(self, i, text):
        """!
        @brief The user changed the function of file i.
        @param i Row.
        @param text New function.
        @return None
        """
        if not self._filling:
            self.session.set_role(i, text)
            self.win.refresh()                                # The checks and the buttons answer at once; the board is read a moment later
            self.win.reload_later()

    def _use_changed(self, row, col):
        """!
        @brief The user ticked or unticked a file.
        @param row Row.
        @param col Column.
        @return None
        """
        if col == 0 and not self._filling and row < len(self.session.files):
            self.session.set_use(row, self.table.item(row, 0).checkState() == Qt.Checked)
            self.win.refresh()
            self.win.reload_later()

    def _row_selected(self):
        """!
        @brief The copper layer of the selected row is drawn at full strength.
        @return None
        """
        r = self.table.currentRow()
        if 0 <= r < len(self.session.files) and self.session.files[r].role in COPPER and self.session.files[r].use:
            self.preview.selected = self.session.files[r].role
            self.refresh()

    def _layer_picked(self, text):
        """!
        @brief The layer chosen in the combo above the preview.
        @param text Role of the layer.
        @return None
        """
        if text and text != self.preview.selected:
            self.preview.selected = text
            self.preview.update()


def _spin(lo, hi, value, decimals, suffix, tip):
    """!
    @brief A spin box with a unit and a tooltip.
    @param lo Minimum.
    @param hi Maximum.
    @param value Initial value.
    @param decimals Decimals shown.
    @param suffix Unit text.
    @param tip Tooltip text.
    @return QDoubleSpinBox
    """
    s = QDoubleSpinBox()
    s.setRange(lo, hi)
    s.setDecimals(decimals)
    s.setValue(value)
    s.setSuffix(" " + suffix)
    s.setToolTip(tip)
    s.setKeyboardTracking(False)
    return s


class Step2Page(QWidget):
    """!
    @brief Step 2, parts: the paste openings and the placement file as parts, a table with the heat-source tick, power, Tj max and role, the shape of the heat source, the frame check and the preview with clicks.
    @details The pre-selection from the paste layer is always editable: every number, the tick, the shape (convex hull by default, box, the largest opening) and the openings of a part (a click on a
             red opening makes a part, Ctrl+click adds it to the selected part).
    """

    COLS = ["Heat source", "Part", "Package", "Source", "Openings", "Size (mm)", "Position (mm)", "Power", "Tj max", "Role"]

    def __init__(self, win: "ImportBoardWindow"):
        """!
        @param win The import window.
        """
        super().__init__()
        self.win, self.session = win, win.session
        self.selected = None                                         # Designator of the selected part
        self._building = False
        lay = QHBoxLayout(self)
        left = QVBoxLayout()
        self.info = QLabel("")
        self.info.setWordWrap(True)
        self.info.setToolTip("How many parts the files give and how each was matched to its paste openings.")
        left.addWidget(self.info)
        self.frame_box = QGroupBox("The placement file and the Gerber files")
        fl = QVBoxLayout(self.frame_box)
        self.frame_text = QLabel("")
        self.frame_text.setWordWrap(True)
        fl.addWidget(self.frame_text)
        row = QHBoxLayout()
        self.accept_btn, self.reject_btn = QPushButton("Move the placement file by the offset"), QPushButton("Keep the file as it is")
        self.accept_btn.setToolTip("Add the proposed offset to every position of the placement file and match the parts again. The offset is the one that puts the most SMD parts on their paste openings.")
        self.reject_btn.setToolTip("Do not move the placement file: the parts are matched with its positions as written.")
        self.accept_btn.clicked.connect(lambda: self._answer(True))
        self.reject_btn.clicked.connect(lambda: self._answer(False))
        row.addWidget(self.accept_btn)
        row.addWidget(self.reject_btn)
        row.addStretch(1)
        fl.addLayout(row)
        left.addWidget(self.frame_box)
        self.table = QTableWidget(0, len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setToolTip("The parts of the files. Tick a part to make it a heat source and give it a power in W. The Source column says how the part was found: X3 component layer, "
                              "paste TO.C + placement, placement by position (approximate), paste only, or placement only (no opening). Click a row, or a paste opening in the preview, to select a part.")
        self.table.itemSelectionChanged.connect(self._row)
        self.table.cellChanged.connect(self._tick)
        left.addWidget(self.table, 1)
        g = QGroupBox("Shape of the heat source of the selected part")
        gl = QVBoxLayout(g)
        self.radios = {}
        grp = QButtonGroup(g)
        for key, text, tip in (("hull", "Convex hull of the paste openings (suggested)", "The smallest convex polygon around the openings: follows the pads of a part with a tab and equals the box for a rectangular pattern."),
                               ("box", "Bounding box of the paste openings", "A rectangle around all the openings: the power spreads over the gaps between pads too."),
                               ("largest", "Largest opening only", "The hull of the largest opening: the exposed pad of a QFN or the tab of a power package, where the heat enters.")):
            r = QRadioButton(text)
            r.setToolTip(tip)
            r.toggled.connect(lambda on, k=key: on and self._shape(k))
            grp.addButton(r)
            gl.addWidget(r)
            self.radios[key] = r
        self.suggest = QLabel("")
        self.suggest.setWordWrap(True)
        th.hint(self.suggest)
        gl.addWidget(self.suggest)
        left.addWidget(g)
        row = QHBoxLayout()
        for text, tip, fn in (("Make selected a heat source", "Tick the selected part as a heat source.", self._make_selected),
                              ("All parts with a power", "Tick every part that already has a power.", self._all_power),
                              ("All matched parts", "Tick every part that has a paste opening (0 W until you give a power).", self._all_matched)):
            b = QPushButton(text)
            b.setToolTip(tip)
            b.clicked.connect(fn)
            row.addWidget(b)
        left.addLayout(row)
        lay.addLayout(left, 13)
        right = QVBoxLayout()
        bar = QHBoxLayout()
        self.preview = Preview(self.session, "parts")
        self.side = QComboBox()
        self.side.addItems(["Top side", "Bottom side"])
        self.side.setToolTip("Which side's paste openings are shown and clickable.")
        self.side.currentIndexChanged.connect(lambda i: (setattr(self.preview, "side", "top" if i == 0 else "bottom"), self.preview.update()))
        bar.addWidget(self.side)
        for key, label in (("copper", "Copper"), ("paste", "Paste openings"), ("sources", "Heat sources")):
            c = QCheckBox(label)
            c.setChecked(True)
            c.setToolTip(f"Show or hide: {label.lower()}.")
            c.toggled.connect(lambda on, k=key: (self.preview.show_layers.__setitem__(k, on), self.preview.update()))
            bar.addWidget(c)
        bar.addStretch(1)
        right.addLayout(bar)
        right.addWidget(self.preview, 1)
        cap = QLabel("White squares are matched paste openings, <b>red ones match no part</b>. Click an opening to select its part; click a red one to create a heat source from it; "
                     "Ctrl+click a red one to add it to the selected part. Dashed: heat sources; solid accent: the selected part.")
        cap.setWordWrap(True)
        th.hint(cap)
        right.addWidget(cap)
        self.warn = QLabel("")
        self.warn.setWordWrap(True)
        self.warn.setToolTip("What the matching found about the files: a placement file that does not fit, parts matched by position only, differences between the X3 layer and the placement file.")
        right.addWidget(self.warn)
        lay.addLayout(right, 9)
        self.preview.clicked.connect(self._clicked)

    # -- build
    def refresh(self):
        """!
        @brief Fill the table, the frame box and the messages from the session.
        @return None
        """
        sx = self.session
        c = th.colors(th.current_name())
        self._building = True
        parts = sx.parts()
        t = self.table
        t.setRowCount(0)
        order = sorted(parts, key=lambda p: (not sx.is_source(p), -p.power, not p.polygon_mm, p.designator))
        t.setRowCount(len(order))
        for k, p in enumerate(order):
            orphan, has = sx.is_orphan(p), bool(p.polygon_mm)
            it = QTableWidgetItem()
            it.setFlags((Qt.ItemIsUserCheckable | Qt.ItemIsEnabled) if has and not orphan else Qt.ItemIsEnabled)
            it.setCheckState(Qt.Checked if sx.is_source(p) else Qt.Unchecked)
            it.setToolTip("Heat source: the part's power enters the board in its shape." if has and not orphan else
                          "An orphan does not heat the board." if orphan else "No paste opening and no outline: there is no area to heat; click an opening in the preview to give it one.")
            t.setItem(k, 0, it)
            size = "-"
            if has:
                xs, ys = [q[0] for q in p.polygon_mm], [q[1] for q in p.polygon_mm]
                size = f"{max(xs) - min(xs):.1f} x {max(ys) - min(ys):.1f}"
            pos = p.from_file.get("position_mm") or ([sum(q[0] for q in p.polygon_mm) / len(p.polygon_mm), sum(q[1] for q in p.polygon_mm) / len(p.polygon_mm)] if has else None)
            nop = len(sx._openings_of(p))
            vals = {1: p.designator, 2: (p.footprint or p.from_file.get("package", ""))[:24], 3: sx.source_label(p), 4: str(nop or p.from_file.get("n_openings", 0)), 5: size,
                    6: f"{pos[0]:.2f}, {pos[1]:.2f}" if pos else "-"}
            if p.from_file.get("heat_source") is False:
                vals[3] += f" ({p.from_file.get('mount', 'not SMD')})"
            for col, text in vals.items():
                item = QTableWidgetItem(text)
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                if not has or orphan:
                    item.setForeground(QColor(c["muted"]))
                t.setItem(k, col, item)
            sp = _spin(0, 1000, p.power, 3, "W", "Power the part dissipates, in W. Worst case: all of it enters the board. From the datasheet or the Power Calculator.")
            sp.setEnabled(has and not orphan)
            sp.valueChanged.connect(lambda v, d=p.designator: self._set(d, power=v))
            t.setCellWidget(k, 7, sp)
            tj = _spin(0, 300, float(p.edits.get("tj_max", 0.0)), 0, "°C", "Highest junction temperature of the datasheet (0: none). The result reports the margin.")
            tj.valueChanged.connect(lambda v, d=p.designator: self._set(d, tj_max=v))
            t.setCellWidget(k, 8, tj)
            cb = QComboBox()
            cb.addItems(["Component", "Source"])
            cb.setCurrentText(p.edits.get("role", "Component"))
            cb.setToolTip("Component: a package with a junction (theta, Tj limit, optional heatsink on top). Source: only a heated area on the board.")
            cb.currentTextChanged.connect(lambda v, d=p.designator: self._set(d, role=v))
            t.setCellWidget(k, 9, cb)
        hh = t.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeToContents)
        self._building = False
        counts = sx.parts_info().get("counts", {})
        n_open = len(sx.openings())
        self.info.setText(f"<b>{len(parts)} parts</b> ({', '.join(f'{v} {k}' for k, v in counts.items() if v) or 'none found'}); {n_open} paste openings, "
                          f"<span style='color:{c['bad']}'>{len(sx.unmatched())} match no part (red in the preview).</span>")
        fr = sx.frame_proposal()
        self.frame_box.setVisible(bool(fr))
        if fr:
            self.frame_text.setText(f"<span style='color:{c['warn']}'>" + html.escape(
                (f"The positions of the placement file differ from the Gerber files by {fr['dx']:+.2f}, {fr['dy']:+.2f} mm: with this offset {fr['best'] * 100:.0f} % of the SMD parts sit on their openings "
                 f"instead of {fr['given'] * 100:.0f} %." if fr.get("propose") else
                 "The placement file and the Gerber files do not fit (another origin beyond 10 mm, a rotation, a mirror or a unit): the parts matched by position are not reliable.")) + "</span>")
            self.accept_btn.setVisible(bool(fr.get("propose")))
            self.accept_btn.setEnabled(sx.offset_answer != "accepted")
        self.warn.setText("<br>".join(f"<span style='color:{c['warn']}'>{html.escape(w)}</span>" for w in sx.parts_warnings()))
        if self.selected is not None and sx.part(self.selected) is None:
            self.selected = None
        self._sync_selection()
        self.preview.selected_part = self.selected
        self.preview.update()

    def _answer(self, accept):
        """!
        @brief The user answered the frame check.
        @param accept True to move the placement file.
        @return None
        """
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.session.answer_frame(accept)
            self.session.parts()
        finally:
            QApplication.restoreOverrideCursor()
        self.refresh()
        self.win.update_nav()

    # -- selection
    def _row(self):
        """!
        @brief A table row was selected.
        @return None
        """
        if self._building:
            return
        r = self.table.currentRow()
        if r >= 0 and self.table.item(r, 1):
            self.selected = self.table.item(r, 1).text()
            self._shape_controls()
            self.preview.selected_part = self.selected
            self.preview.update()

    def _sync_selection(self):
        """!
        @brief Select the table row of the selected part.
        @return None
        """
        self._building = True
        for r in range(self.table.rowCount()):
            if self.table.item(r, 1) and self.table.item(r, 1).text() == self.selected:
                self.table.selectRow(r)
        self._building = False
        self._shape_controls()

    def _shape_controls(self):
        """!
        @brief Set the shape radios and the text for the selected part.
        @return None
        """
        sx = self.session
        p = sx.part(self.selected) if self.selected else None
        avail = sx.shapes_of(p) if p else []
        for k, r in self.radios.items():
            r.blockSignals(True)
            r.setEnabled(k in avail)
            r.setChecked(bool(p) and p.shape == k and k in avail)
            r.blockSignals(False)
        if p is None:
            self.suggest.setText("Select a part with a paste opening.")
        elif not avail:
            self.suggest.setText(f"{p.designator} has no paste opening of its own ({sx.source_label(p)}): click a red opening in the preview with Ctrl to add one.")
        else:
            self.suggest.setText(f"{p.designator}: shape '{p.shape}'. The convex hull is the suggestion; you can always change it.")

    def _shape(self, kind):
        """!
        @brief The user chose a shape.
        @param kind "hull", "box" or "largest".
        @return None
        """
        if self.selected and not self._building:
            self.session.set_shape(self.selected, kind)
            self._shape_controls()
            self.preview.update()

    # -- edits
    def _set(self, des, **kw):
        """!
        @brief A cell editor changed a value; a power above 0 ticks the part as a heat source.
        @param des Designator.
        @param kw power, tj_max or role.
        @return None
        """
        if self._building:
            return
        was = self.session.is_source(self.session.part(des))
        self.session.set_part(des, **kw)
        if self.session.is_source(self.session.part(des)) != was:
            self.refresh()
        self.preview.update()
        self.win.update_nav()

    def _tick(self, r, c):
        """!
        @brief The user ticked a heat source.
        @param r Row.
        @param c Column.
        @return None
        """
        if c == 0 and not self._building and self.table.item(r, 1):
            self.session.set_part(self.table.item(r, 1).text(), use=self.table.item(r, 0).checkState() == Qt.Checked)
            self.preview.update()
            self.win.update_nav()

    def _make_selected(self):
        """!
        @brief Tick the selected part.
        @return None
        """
        if self.selected:
            self.session.set_part(self.selected, use=True)
            self.refresh()
            self.win.update_nav()

    def _all_power(self):
        """!
        @brief Tick every part with a power.
        @return None
        """
        for p in self.session.parts():
            if p.power > 0 and p.polygon_mm:
                self.session.set_part(p.designator, use=True)
        self.refresh()
        self.win.update_nav()

    def _all_matched(self):
        """!
        @brief Tick every part with an opening.
        @return None
        """
        for p in self.session.parts():
            if p.polygon_mm and not self.session.is_orphan(p):
                self.session.set_part(p.designator, use=True)
        self.refresh()
        self.win.update_nav()

    def _clicked(self, x, y, ctrl):
        """!
        @brief A click on the preview: select the part of an opening, create a heat source from a red one, or add it to the selected part (Ctrl).
        @param x X (mm, Gerber frame).
        @param y Y (mm).
        @param ctrl True when Ctrl was held.
        @return None
        """
        des = self.session.click(x, y, ctrl, self.selected, self.preview.side)
        if des is not None:
            self.selected = des
            self.refresh()
            self.win.update_nav()


class Step3Page(QWidget):
    """!
    @brief Step 3, model: the copper mapping (faces; the others under Advanced), the pixel of the masks, the solver cell, the vias, the memory verdict, the warnings and a grid preview.
    """

    MAPPINGS = {"faces": ("Faces from the heat flow, on the reduced sheet (recommended)",
                          "Each cell face takes the conductance of the copper pattern across it, computed from the flow. Within about 3 to 5 % of the pixel network on windows of real boards at cells of 0.5 to 1.3 mm "
                          "(up to 10 % too hot at a 2 mm cell on 4 mm parts). The default."),
                "lambda": ("Lambda 0.5 (fast, comparison)", "A quick blend of the series and parallel limits of the copper in the cell. Better than the fill, not as good as the faces."),
                "fill": ("Fill fraction per cell, as for a drawn zone (comparison)", "The mean copper fraction of the cell as a drawn zone's fill. Reads 10 to 30 % too cool on thin copper of real boards: for comparison only.")}

    def __init__(self, win: "ImportBoardWindow"):
        """!
        @param win The import window.
        """
        super().__init__()
        self.win, self.session = win, win.session
        lay = QHBoxLayout(self)
        left = QVBoxLayout()
        g = QGroupBox("Copper mapping")
        gl = QVBoxLayout(g)
        self.radios = {}
        grp = QButtonGroup(g)
        text, tip = self.MAPPINGS["faces"]
        r = QRadioButton(text)
        r.setToolTip(tip)
        r.setChecked(True)
        r.toggled.connect(lambda on: on and self._mapping("faces"))
        grp.addButton(r)
        gl.addWidget(r)
        self.radios["faces"] = r
        # The other mappings are comparison options: one collapsed group, easy to move or remove
        self.adv = QPushButton("Advanced \u25b8")
        self.adv.setCheckable(True)
        self.adv.setFlat(True)
        self.adv.setToolTip("Other ways to turn the copper pattern into cell conductances, kept for comparison. The faces are the recommended mapping.")
        al = QVBoxLayout()
        al.setContentsMargins(18, 0, 0, 0)
        for key in ("lambda", "fill"):
            text, tip = self.MAPPINGS[key]
            r = QRadioButton(text)
            r.setToolTip(tip)
            r.toggled.connect(lambda on, k=key: on and self._mapping(k))
            grp.addButton(r)
            al.addWidget(r)
            self.radios[key] = r
        self.adv_body = QWidget()
        self.adv_body.setLayout(al)
        self.adv_body.setVisible(False)
        self.adv.toggled.connect(self._advanced)
        gl.addWidget(self.adv, 0, Qt.AlignLeft)
        gl.addWidget(self.adv_body)
        left.addWidget(g)
        g = QGroupBox("Pixel, cell and memory")
        f = QFormLayout(g)
        self.pix = _spin(0.005, 1.0, 0.1, 3, "mm", "Pixel of the copper masks. Auto: the thinnest line of the files, and at most a tenth of the cell (about ten pixels per cell, which the faces need).")
        self.pix.valueChanged.connect(self._pix)
        row = QHBoxLayout()
        row.addWidget(self.pix, 1)
        a = QPushButton("Auto")
        a.clicked.connect(self._auto_pix)
        row.addWidget(a)
        f.addRow("Mask pixel", row)
        self.cell = _spin(0.1, 20, 1.0, 2, "mm", "Cell of the solver grid. The masks are reduced to this grid by the mapping above. Imported copper warns above 1 mm.")
        self.cell.valueChanged.connect(self._cell)
        row = QHBoxLayout()
        row.addWidget(self.cell, 1)
        a = QPushButton("Auto")
        a.clicked.connect(self._auto_cell)
        row.addWidget(a)
        f.addRow("Cell size", row)
        self.mem = QLabel("")
        self.mem.setWordWrap(True)
        self.mem.setToolTip("Memory verdict of the memory guard before anything is drawn: the unknowns of the model grid and the masks of the import, against the limit of Preferences.")
        f.addRow(self.mem)
        left.addWidget(g)
        g = QGroupBox("Layers and vias")
        f = QFormLayout(g)
        self.layers_label = QLabel("")
        self.layers_label.setWordWrap(True)
        self.layers_label.setToolTip("The copper layers come from the functions of the files (step 1: the file list is the only place to change them).")
        f.addRow("Copper layers", self.layers_label)
        self.via_max = _spin(0.1, 5, self.session.via_max_mm, 2, "mm", "Largest diameter of a plated hole that is a via. Larger plated holes are component holes: a lead is not modelled.")
        self.via_max.valueChanged.connect(self._via)
        f.addRow("Vias up to", self.via_max)
        self.vias = QLabel("")
        th.hint(self.vias)
        f.addRow(self.vias)
        self.newname = QLineEdit()
        self.newname.setToolTip("Name of the new project.")
        self.newname.textChanged.connect(lambda t: setattr(self.session, "name", t or "board"))
        f.addRow("Project name", self.newname)
        left.addWidget(g)
        left.addStretch(1)
        lay.addLayout(left, 9)
        right = QVBoxLayout()
        right.addWidget(QLabel("<b>Warnings</b> (the import still runs)"))
        self.wl = WarningList()
        self.wl.setMinimumHeight(160)
        self.wl.setMaximumHeight(260)
        right.addWidget(self.wl)
        self.preview = Preview(self.session, "model")
        right.addWidget(self.preview, 1)
        cap = QLabel("The solver grid of the cell chosen on the left, over the copper.")
        th.hint(cap)
        right.addWidget(cap)
        lay.addLayout(right, 11)

    def _advanced(self, on):
        """!
        @brief Show or hide the comparison mappings.
        @param on True to show.
        @return None
        """
        self.adv_body.setVisible(on)
        self.adv.setText("Advanced \u25be" if on else "Advanced \u25b8")

    def _mapping(self, key):
        """!
        @brief The mapping changed.
        @param key "faces", "lambda" or "fill".
        @return None
        """
        self.session.mapping = key
        self.refresh()

    def _pix(self, v):
        """!
        @brief The user typed a pixel.
        @param v Pixel (mm).
        @return None
        """
        if not self._loading:
            self.session.pixel_mm = v
            self.refresh()

    def _cell(self, v):
        """!
        @brief The cell changed (the automatic pixel follows it unless the user typed one).
        @param v Cell (mm).
        @return None
        """
        if not self._loading:
            self.session.cell_mm = v
            self.refresh()

    def _via(self, v):
        """!
        @brief The via limit changed.
        @param v Diameter (mm).
        @return None
        """
        if not self._loading:
            self.session.via_max_mm = v
            self.refresh()

    def _auto_pix(self):
        """!
        @brief Back to the automatic pixel.
        @return None
        """
        self.session.pixel_mm = None
        self.refresh()

    def _auto_cell(self):
        """!
        @brief The automatic cell.
        @return None
        """
        self.session.cell_mm = self.session.auto_cell()
        self.refresh()

    _loading = False

    def refresh(self):
        """!
        @brief Update the values, the memory verdict, the via counts and the warnings.
        @return None
        """
        sx = self.session
        c = th.colors(th.current_name())
        self._loading = True
        self.pix.setValue(sx.effective_pixel())
        self.cell.setValue(sx.cell_mm)
        self.via_max.setValue(sx.via_max_mm)
        if not self.newname.text():
            self.newname.setText(sx.name)
        self.radios[sx.mapping].setChecked(True)
        if sx.mapping != "faces":
            self.adv.setChecked(True)
        self._loading = False
        self.preview.cell = sx.cell_mm
        layers = sx.layers()
        self.layers_label.setText(f"{len(layers)}: " + ", ".join(l.role.replace(' copper', '') for l in layers) + f"  ({sx.stackup_text().split(': ', 1)[-1]})" if layers else "none")
        mv = sx.memory_verdict()
        if mv is None:
            self.mem.setText("No board yet.")
        else:
            v = mv["fvm"]
            tone = {"ok": "ok", "slow": "warn", "refuse": "bad"}[v.verdict]
            text = (f"<span style='color:{c[tone]}'>FVM: {v.unknowns} unknowns, about {v.estimate / 1e9:.2f} GB of {v.limit / 1e9:.1f} GB ({v.verdict})</span><br>")
            if mv["import_error"]:
                text += f"<span style='color:{c['bad']}'>Masks: {html.escape(mv['import_error'])}</span>"
            else:
                text += (f"<span style='color:{c['ok']}'>Masks: {len(sx.board().copper)} layers of {mv['cols']} x {mv['rows']} pixels, peak about {mv['import_peak'] / 1e9:.2f} GB (fits)</span>")
            self.mem.setText(text)
        n, comp, nonp = sx.vias()
        self.vias.setText(f"{n} vias, {comp} component holes kept out of the models; {nonp} non-plated holes ignored." if sx.board() else "-")
        self.wl.set_warnings(sx.warnings() if sx.board() else [])
        self.preview.update()


class ReimportDialog(QDialog):
    """!
    @brief What to do when the project already holds an import: replace, update after a layout revision, add files, or cancel; with the table of what changed.
    """

    def __init__(self, session: ImportSession, old, parent=None):
        """!
        @param session The import session of the new files (`build_problem` was run: its record is the new import).
        @param old Stored ImportRecord of the project.
        @param parent Qt parent.
        """
        super().__init__(parent)
        self.session, self.old, self.new = session, old, session.record
        self.setWindowTitle("The project already has an imported board")
        self.resize(900, 620)
        c = th.colors(th.current_name())
        self.diff = session.part_diff(old)
        self.sources = session.classify_files(old, self.new)
        same, reasons = session.same_board(old, self.new)
        lay = QVBoxLayout(self)
        ident = sum(1 for s in self.sources if s["status"] == "identical")
        intro = QLabel(f"The open project holds an import of <b>{html.escape(old.name)}</b> ({len(old.files)} files, {len(old.parts)} parts). "
                       f"Of the {len(self.sources)} functions in the new set, {ident} are byte-identical to the stored files. What do you want to do?")
        intro.setWordWrap(True)
        lay.addWidget(intro)
        self.warn = QLabel("")
        self.warn.setWordWrap(True)
        if not same:
            self.warn.setText(f'<span style="color:{c["bad"]}"><b>This looks like a different board:</b> ' + "; ".join(html.escape(r) for r in reasons) +
                              ". Replacing it makes orphans of the parts that are not in the new files (kept with their power, not heating). Consider a new project instead.</span>")
        lay.addWidget(self.warn)
        self.radios = {}
        grp = QButtonGroup(self)
        texts = {"replace": ("Replace the previous import", "Copper, drills and outline are replaced. Parts with the same designator keep their power, Tj max, role and shape edits. Parts that disappeared stay as orphans (not heating) unless you tick them to remove."),
                 "update": ("Update after a layout revision", "Like replace, plus a table of what changed: moved, new, removed, resized and rotated parts. Nothing is lost silently."),
                 "add": ("Add files to the existing import", "A missing layer, a drill file, a placement file or an extra paste layer. The stored copper and outline are not touched; files that claim a function the import already has are shown to choose.")}
        for key, (t, tip) in texts.items():
            r = QRadioButton(t)
            r.setToolTip(tip)
            r.toggled.connect(self._mode)
            grp.addButton(r)
            self.radios[key] = r
            lay.addWidget(r)
            d = QLabel(tip)
            d.setWordWrap(True)
            th.hint(d)
            d.setContentsMargins(22, 0, 0, 0)
            lay.addWidget(d)
        self.radios["update" if (same and any(d["change"] != "kept" for d in self.diff)) else "replace"].setChecked(True)
        self.table = QTableWidget(0, 4)
        self.table.verticalHeader().setVisible(False)
        self.table.setToolTip("The comparison for the chosen command.")
        lay.addWidget(self.table, 1)
        self.note = QLabel("")
        self.note.setWordWrap(True)
        th.hint(self.note)
        lay.addWidget(self.note)
        foot = QLabel("The result is one undo step. Results of earlier runs stay in the project and are marked outdated; run again after the import.")
        foot.setWordWrap(True)
        th.hint(foot)
        lay.addWidget(foot)
        bb = QDialogButtonBox(QDialogButtonBox.Cancel)
        self.go = bb.addButton("Continue", QDialogButtonBox.AcceptRole)
        self.go.setObjectName("primary")
        self.go.setToolTip("Apply the chosen command to the project as one undo step.")
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self._mode()

    @property
    def mode(self):
        """!
        @brief The chosen command.
        @return "replace", "update" or "add".
        """
        return next(k for k, r in self.radios.items() if r.isChecked())

    def _mode(self, *_):
        """!
        @brief Fill the table for the chosen command.
        @param _ Ignored (the toggled signal's argument).
        @return None
        """
        if not hasattr(self, "table") or not any(r.isChecked() for r in self.radios.values()):
            return
        t = self.table
        t.blockSignals(True)
        t.setRowCount(0)
        mode = self.mode
        self.combos, self.checks = {}, {}
        if mode == "add":
            t.setHorizontalHeaderLabels(["Function", "Stored import", "New file", "Choose"])
            rows = [s for s in self.sources if s["status"] != "only stored"]
            t.setRowCount(len(rows))
            for k, s in enumerate(rows):
                for col, v in ((0, s["function"]), (1, s["old"].name if s["old"] else "-"), (2, s["new"].name if s["new"] else "-")):
                    t.setItem(k, col, QTableWidgetItem(v))
                if s["status"] == "added":
                    t.setItem(k, 3, QTableWidgetItem("added"))
                elif s["status"] == "identical":
                    t.setItem(k, 3, QTableWidgetItem("identical, nothing to do"))
                else:
                    cb = QComboBox()
                    cb.addItems(["Keep the stored file", "Use the new file"])
                    cb.setToolTip("Two files claim this function and they differ.")
                    t.setCellWidget(k, 3, cb)
                    self.combos[s["function"]] = cb
            self.note.setText(f"{sum(1 for s in rows if s['status'] == 'added')} function(s) added, {len(self.combos)} conflict(s) to choose. The stored copper, outline and existing parts are not touched.")
        else:
            t.setHorizontalHeaderLabels(["Part", "Change", "Detail", "Kept from the stored import" if mode != "replace" else "Action"])
            rows = [d for d in self.diff if d["change"] != "kept"] if mode == "update" else [d for d in self.diff if d["change"] == "removed"]
            t.setRowCount(len(rows))
            oldp = {p.designator: p for p in self.old.parts}
            for k, d in enumerate(rows):
                o = oldp.get(d["ref"])
                kept = f"{o.power:g} W, Tj {o.edits.get('tj_max', 0):g} °C, {o.edits.get('role', 'Component')}" if o and o.power and d["change"] != "removed" else ""
                for col, v in ((0, d["ref"]), (1, d["change"]), (2, d["detail"])):
                    t.setItem(k, col, QTableWidgetItem(v))
                if d["change"] == "removed":
                    it = QTableWidgetItem("Remove this part")
                    it.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                    it.setCheckState(Qt.Unchecked)
                    it.setToolTip("Unticked: the part stays in the project as an orphan (kept with its power, not heating) until you remove it.")
                    t.setItem(k, 3, it)
                    self.checks[d["ref"]] = it
                else:
                    t.setItem(k, 3, QTableWidgetItem(kept or "nothing to keep"))
            n_keep = sum(1 for p in self.old.parts if p.power)
            counts = {k: sum(1 for d in self.diff if d["change"] == k) for k in ("new", "removed")}
            moved = sum(1 for d in self.diff if "moved" in d["change"])
            resized = sum(1 for d in self.diff if "resized" in d["change"])
            self.note.setText(f"{n_keep} part(s) have a power to keep. New {counts['new']}, removed {counts['removed']}, moved {moved}, resized {resized}. Removed parts stay as orphans unless ticked.")
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        t.horizontalHeader().setStretchLastSection(True)
        t.blockSignals(False)

    def remove_refs(self):
        """!
        @brief Designators the user ticked for removal.
        @return list of str.
        """
        return [r for r, it in self.checks.items() if it.checkState() == Qt.Checked]

    def file_choice(self):
        """!
        @brief The choice for each conflicting function (command "add").
        @return dict function -> "stored" or "new".
        """
        return {fn: ("new" if cb.currentIndex() == 1 else "stored") for fn, cb in self.combos.items()}


class Stepper(QWidget):
    """!
    @brief The header: numbered round markers joined by a line (current in the accent, finished with a check mark, locked muted); a click on a reachable marker jumps to the step.
    """

    step_clicked = Signal(int)

    def __init__(self, states):
        """!
        @param states Function returning a list of (state, tooltip) per step; state is "current", "done", "ready" or "locked".
        """
        super().__init__()
        self.states = states
        self.setMinimumHeight(54)
        self.setMouseTracking(True)

    def _slots(self):
        """!
        @brief The rectangle of every step.
        @return list of QRectF.
        """
        w = self.width() / len(STEP_TITLES)
        return [QRectF(i * w, 0, w, self.height()) for i in range(len(STEP_TITLES))]

    def paintEvent(self, ev):
        """!
        @brief Paint markers, labels and the joining lines with the tokens of the current theme.
        @param ev Paint event.
        @return None
        """
        c = th.colors(th.current_name())
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        st = self.states()
        r = 15
        f = QFont(self.font())
        slots = self._slots()
        accent, border = QColor(c["accent"]), QColor(c["border"])
        for i, (slot, (state, _)) in enumerate(zip(slots, st)):
            cx, cy = slot.left() + 8 + r, self.height() / 2
            if i + 1 < len(slots):
                # The line to the next marker: accent once this step is finished, border colour otherwise; it never runs past the next marker on a narrow window
                p.setPen(QPen(accent if state == "done" else border, 2))
                x0, x1 = cx + r + 150, slots[i + 1].left() + 8 - 6
                if x1 > x0:
                    p.drawLine(QPointF(x0, cy), QPointF(x1, cy))
            if state == "current":
                p.setPen(Qt.NoPen)
                p.setBrush(accent)
            elif state == "done":
                p.setPen(QPen(accent, 2))
                p.setBrush(QColor(c["base"]))
            else:
                p.setPen(QPen(border, 2))
                p.setBrush(QColor(c["alt"]))
            p.drawEllipse(QPointF(cx, cy), r, r)
            mark = QColor(c["on_accent"]) if state == "current" else accent if state == "done" else QColor(c["muted"])
            p.setPen(QPen(mark, 2.2))
            if state == "done":
                p.drawLine(QPointF(cx - 6, cy), QPointF(cx - 2, cy + 5))
                p.drawLine(QPointF(cx - 2, cy + 5), QPointF(cx + 6, cy - 5))
            else:
                f.setBold(True)
                p.setFont(f)
                p.drawText(QRectF(cx - r, cy - r, 2 * r, 2 * r), Qt.AlignCenter, str(i + 1))
            f.setBold(state == "current")
            p.setFont(f)
            p.setPen(QColor(c["muted"] if state == "locked" else c["text"]))
            p.drawText(QRectF(cx + r + 8, cy - 14, 150, 28), Qt.AlignVCenter | Qt.AlignLeft, STEP_TITLES[i])
        p.end()

    def at(self, pos):
        """!
        @brief The step under a point.
        @param pos QPointF in widget pixels.
        @return int index or -1.
        """
        return next((i for i, s in enumerate(self._slots()) if s.contains(pos)), -1)

    def point_of(self, i):
        """!
        @brief A point inside the slot of a step (to click or show its tooltip from a test).
        @param i Step index.
        @return QPoint
        """
        return self._slots()[i].center().toPoint()

    def mousePressEvent(self, ev):
        """!
        @brief A click on a reachable marker jumps to the step.
        @param ev Mouse event.
        @return None
        """
        i = self.at(ev.position())
        if i >= 0 and self.states()[i][0] != "locked":
            self.step_clicked.emit(i)

    def event(self, ev):
        """!
        @brief Tooltip of the step under the pointer (what it is, or why it is locked).
        @param ev Event.
        @return bool
        """
        if ev.type() == QEvent.ToolTip:
            i = self.at(ev.pos().toPointF())
            if i >= 0:
                QToolTip.showText(ev.globalPos(), self.states()[i][1], self)
            else:
                QToolTip.hideText()
            return True
        return super().event(ev)


class ImportBoardWindow(QDialog):
    """!
    @brief The import window: stepper, the page of the current step, and Help / Close / Import now / Back / Next (Import on the last step).
    """

    def __init__(self, parent=None, session: ImportSession = None, existing=None):
        """!
        @param parent Qt parent (the main window).
        @param session An ImportSession; a new one when omitted.
        @param existing The ImportRecord of the open project when it already holds an import (the re-import dialog is asked), else None.
        """
        super().__init__(parent)
        self.session = session or ImportSession()
        self.existing = existing
        self.step = 0
        self.problem = None                                   # The Problem built by Import (None until the import ran)
        self.record = None                                    # The ImportRecord to store in the project
        self.mode = "new"                                     # "new", or the re-import command "replace", "update" or "add"
        self.changes = []                                     # Text lines of what a re-import changed
        self.ask_reimport = lambda dlg: dlg.exec() == QDialog.Accepted
        # The questions are attributes so that a test (or a script) can answer them without a modal box
        self.confirm = lambda title, text: QMessageBox.question(self, title, text) == QMessageBox.Yes
        self.notify = lambda title, text: QMessageBox.information(self, title, text)
        self.setWindowTitle("Import Gerber board")
        self.resize(1280, 820)
        lay = QVBoxLayout(self)
        self.stepper = Stepper(self.step_states)
        self.stepper.step_clicked.connect(self.go)
        lay.addWidget(self.stepper)
        self.subtitle = QLabel("")
        th.hint(self.subtitle)
        self.subtitle.setToolTip("What the current step is for.")
        lay.addWidget(self.subtitle)
        self.page1 = Step1Page(self)
        self.page2, self.page3 = Step2Page(self), Step3Page(self)
        self.pages = [self.page1, self.page2, self.page3]
        self.stack = QStackedWidget()
        for p in self.pages:
            self.stack.addWidget(p)
        lay.addWidget(self.stack, 1)
        row = QHBoxLayout()
        self.status = QLabel("")
        th.hint(self.status)
        row.addWidget(self.status, 1)
        self.help_btn, self.close_btn = QPushButton("Help"), QPushButton("Close")
        self.early_btn = QPushButton("Import now")
        self.early_btn.setToolTip("Import with what is set so far; the later steps keep their defaults. Available once step 1 is complete.")
        self.back_btn, self.next_btn = QPushButton("Back"), QPushButton("Next")
        self.next_btn.setObjectName("primary")
        self.next_btn.setMinimumWidth(90)
        self.back_btn.setToolTip("Go back one step.")
        self.next_btn.setToolTip("Go to the next step; on the last step it imports the board.")
        self.close_btn.clicked.connect(self.reject)
        self.help_btn.clicked.connect(self.show_help)
        self.early_btn.clicked.connect(self.do_import)
        self.back_btn.clicked.connect(lambda: self.go(self.step - 1))
        self.next_btn.clicked.connect(self._next)
        for b in (self.help_btn, self.close_btn, self.early_btn, self.back_btn, self.next_btn):
            row.addWidget(b)
        lay.addLayout(row)
        self._reload_timer = QTimer(self)
        self._reload_timer.setSingleShot(True)
        self._reload_timer.timeout.connect(self.reload)
        self.update_nav()

    def _in_thread(self, fn):
        """!
        @brief Run a slow call of the session (reading the copper, building the parts, rasterising the import) off the GUI thread, keeping the window repainting; the window is disabled meanwhile.
        @details The caller waits for the result as for a normal call (a local event loop), so the rest of the code stays sequential. An exception of the call is raised in the caller.
        @param fn Function without arguments.
        @return what fn returns.
        """
        box = {}

        def work():
            """!
            @brief Thread body: call fn and keep its result or its exception.
            @return None
            """
            try:
                box["value"] = fn()
            except BaseException as exc:                      # handed back to the caller's thread
                box["error"] = exc

        t = threading.Thread(target=work, daemon=True)
        loop, tick = QEventLoop(self), QTimer(self)
        tick.setInterval(20)
        tick.timeout.connect(lambda: None if t.is_alive() else loop.quit())
        self.setEnabled(False)
        t.start()
        tick.start()
        try:
            if t.is_alive():
                loop.exec()
        finally:
            tick.stop()
            t.join()
            self.setEnabled(True)
        if "error" in box:
            raise box["error"]
        return box.get("value")

    # -- reading
    def open_path(self, source):
        """!
        @brief Read a folder, ZIP or list of files chosen by the user.
        @param source Path, or list of paths.
        @return None
        """
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.session.set_files(source)
            self._in_thread(self.session.load)
        except (OSError, ValueError, GerberError) as exc:
            self.notify("Cannot read the files", str(exc))
        finally:
            QApplication.restoreOverrideCursor()
        self.refresh()

    def reload_later(self):
        """!
        @brief Read the board again soon (after a function or use change; several changes in a row cost one read).
        @return None
        """
        self._reload_timer.start(50)

    def reload(self):
        """!
        @brief Read the board again from the files as assigned.
        @return None
        """
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self._in_thread(self.session.load)
        finally:
            QApplication.restoreOverrideCursor()
        self.refresh()

    def refresh(self):
        """!
        @brief Update the pages and the buttons from the session.
        @return None
        """
        self.page1.refresh()
        self.update_nav()

    def _refresh_page(self, i):
        """!
        @brief Fill the page of step i from the session (the parts are built on first use, with a wait cursor).
        @param i Step index.
        @return None
        """
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            if i == 1:
                self._in_thread(self.session.parts)               # built on first use (about 0.7 s on a 130-part board)
                self.page2.refresh()
            elif i == 2:
                if self.session.cell_mm == 1.0 and not getattr(self, "_cell_set", False):
                    self.session.cell_mm, self._cell_set = self.session.auto_cell(), True
                self.page3.refresh()
        finally:
            QApplication.restoreOverrideCursor()

    # -- steps
    def reachable(self, i: int) -> bool:
        """!
        @brief Whether step i can be opened now (the first always; the others once step 1 is complete).
        @param i Step index.
        @return bool
        """
        return i == 0 or self.session.complete()

    def step_states(self):
        """!
        @brief State and tooltip of every step for the stepper.
        @return list of (state, tooltip).
        """
        sx = self.session
        out = []
        for i, t in enumerate(STEP_TITLES):
            if i == self.step:
                out.append(("current", f"Step {i + 1}: {t}. You are here."))
            elif not self.reachable(i):
                why = "; ".join(sx.problems()) or "the files could not be read into a board"
                out.append(("locked", f"Locked: step 1 is not complete. {why}."))
            elif i == 0:
                out.append(("done", "Step 1: files and layers are complete. Click to go back."))
            elif i == 1 and sx.heat_sources():
                out.append(("done", f"Step 2: {len(sx.heat_sources())} heat source(s) defined. Click to open."))
            else:
                out.append(("ready", f"Step {i + 1}: {t}. Click to open."))
        return out

    def go(self, i: int):
        """!
        @brief Show step i if it is reachable.
        @param i Step index.
        @return None
        """
        if 0 <= i < len(STEP_TITLES) and self.reachable(i):
            self.step = i
            self._refresh_page(i)
            self.stack.setCurrentIndex(i)
            self.update_nav()

    def _next(self):
        """!
        @brief Next, or Import on the last step.
        @return None
        """
        if self.step == len(STEP_TITLES) - 1:
            self.do_import()
        else:
            self.go(self.step + 1)

    def update_nav(self):
        """!
        @brief Back / Next / Import now buttons, the status line and the stepper.
        @return None
        """
        last = self.step == len(STEP_TITLES) - 1
        ok = self.session.complete()
        self.back_btn.setEnabled(self.step > 0)
        self.next_btn.setText("Import" if last else "Next")
        self.next_btn.setEnabled(ok)
        self.early_btn.setVisible(not last)
        self.early_btn.setEnabled(ok)
        self.status.setText("" if ok else "Next is disabled: " + "; ".join(self.session.problems()))
        self.subtitle.setText(STEP_SUBTITLES[self.step])
        self.early_btn.setToolTip("Import with what is set so far; the later steps keep their defaults. "
                                  + ("" if self.session.heat_sources() else "No heat source is defined yet: you will be asked to confirm.") if ok
                                  else "Available once step 1 is complete.")
        self.stepper.update()

    def do_import(self):
        """!
        @brief The Import command: confirm when no heat source is defined, then build the project from the session.
        @return bool True when a project was built.
        """
        sx = self.session
        if not sx.complete():
            return False
        if not sx.heat_sources() and not self.confirm("No heat source defined", "No part is ticked as a heat source, so the imported board will have no power until you add one. Import anyway?"):
            return False
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            prob = self._in_thread(sx.build_problem)
        except (ValueError, MemoryGuardError, GerberError) as exc:
            self.notify("Cannot import", str(exc))
            return False
        finally:
            QApplication.restoreOverrideCursor()
        self.mode, self.changes = "new", []
        if self.existing is not None:
            dlg = ReimportDialog(sx, self.existing, self)
            if not self.ask_reimport(dlg):
                return False
            res = sx.merge_import(dlg.mode, self.existing, dlg.remove_refs(), dlg.file_choice())
            self.mode, self.changes, self.record = dlg.mode, res["changes"], res["record"]
            if dlg.mode != "add":
                prob.heaters = []                                 # the heaters come from the merged parts (they keep the powers of the stored import)
                sx._add_heaters(prob, sx.record.box_mm, res["parts"])
            self.problem = prob if dlg.mode != "add" else None
        else:
            self.problem, self.record = prob, sx.record
        self.accept()
        return True

    def show_help(self):
        """!
        @brief Open the user guide (on the main window's guide when there is one).
        @return None
        """
        guide = getattr(self.parent(), "show_guide", None)
        if guide is not None:
            guide()

    def changeEvent(self, ev):
        """!
        @brief A theme switch repaints the labels that carry theme colours.
        @param ev Change event.
        @return None
        """
        if ev.type() == QEvent.PaletteChange and hasattr(self, "page1"):
            self.page1.refresh()
            if self.step == 1:
                self.page2.refresh()
            elif self.step == 2:
                self.page3.refresh()
        super().changeEvent(ev)

    def done(self, result):
        """!
        @brief Release the archive and the caches when the window closes.
        @param result Dialog result code.
        @return None
        """
        self.session.close()
        super().done(result)


__all__ = ["ImportBoardWindow", "Preview", "ReimportDialog", "Stepper"]
