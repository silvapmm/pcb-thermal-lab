#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file import_window.py
@brief The Gerber import window ("Import Gerber board..." in the File menu): a stepper header (Files and layers, Parts, Model), Back / Next (Import on the last step) and an "Import now" button.
@details Designed like the Power Calculator: a separate window opened from the menu, every colour a token of `pcbthermal.gui.theme` read when it is painted (so a live theme switch
         recolours it), every control with a tooltip. The window reads and writes nothing but an `ImportSession`; the steps whose feature is not merged yet (the parts from the paste layer,
         the imported copper) are pages that say so and keep the stepper, Back / Next and Import now working, so the layout does not change when the real pages arrive.
         Step 1 is complete: folder, ZIP or files chooser, the detected function of every file in an editable list (two files claiming one function are shown), the layer count with the proposed
         stack-up, the outline, the drills and a zoomable preview of the selected layer.
"""

import html

import numpy as np
from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                               QMessageBox, QPushButton, QSizePolicy, QStackedWidget, QTableWidget, QTableWidgetItem, QToolTip, QVBoxLayout, QWidget)

from ..gerber import GerberError
from . import theme as th
from .import_session import COPPER, COPPER_BOTTOM, COPPER_TOP, ROLES, UNIQUE, VIA_MAX_MM, ImportNotAvailable, ImportSession

STEP_TITLES = ["Files and layers", "Parts", "Model"]
STEP_SUBTITLES = ["Choose the folder, ZIP or files, check the function of every file and the stack-up.",
                  "Turn paste openings into heat sources: click an opening, give a power in W, choose the shape.",
                  "Choose how the copper is given to the models, the cell, the vias; read the memory verdict."]
PENDING = {1: "Heat sources from the paste layer and the placement file are not part of this version yet. Import with the copper, the outline and the vias now, "
              "and draw the heaters on the imported board in the editor.",
           2: "The choice of the copper mapping, the mask pixel and the model options is not part of this version yet: the import uses the defaults."}


class Preview(QWidget):
    """!
    @brief Zoomable preview of the board: copper layers, outline and drilled holes (mouse wheel zooms, drag pans, double click shows all).
    """

    def __init__(self, session: ImportSession):
        """!
        @param session The import session whose board is drawn.
        """
        super().__init__()
        self.session = session
        self.show_layers = {"copper": True, "outline": True, "holes": True}
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
                p.setOpacity(1.0 if role == self.selected else 0.35)
                p.drawImage(rect, self._image(role, cov, c))
        p.setOpacity(1.0)
        if self.show_layers["outline"]:
            p.setPen(QPen(QColor(c["doc_note_edge"]), 1.6))
            p.setBrush(Qt.NoBrush)
            for outer, holes in b.outline:
                for ring in [outer] + list(holes):
                    p.drawPolygon(QPolygonF([self.to_px(x, y) for x, y in ring]))
        if self.show_layers["holes"]:
            p.setBrush(Qt.NoBrush)
            for h in b.holes:
                # A via-sized hole in the via colour, a larger one (a component hole) in the warning colour, a non-plated one in the muted colour
                tone = "muted" if not h.plated else "via" if h.diameter <= VIA_MAX_MM else "warn"
                p.setPen(QPen(QColor(c[tone]), 1.2))
                r = max(h.diameter * s / 2, 1.6)
                p.drawEllipse(self.to_px(h.x, h.y), r, r)
        p.setPen(QColor(c["muted"]))
        p.drawText(10, self.height() - 8, f"{b.width:.1f} x {b.height:.1f} mm   zoom {self.zoom:.1f}x")
        p.end()

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


class PendingPage(QWidget):
    """!
    @brief The page of a step whose feature is not part of this version yet: a short text and nothing to fill.
    """

    def __init__(self, index: int):
        """!
        @param index Step index (1 or 2).
        """
        super().__init__()
        lay = QVBoxLayout(self)
        t = QLabel(f"<b>{STEP_TITLES[index]}</b>")
        lay.addWidget(t)
        self.text = QLabel(PENDING[index])
        self.text.setWordWrap(True)
        self.text.setToolTip("This step is filled by a feature that is not in this version. Back, Next and Import work as they will with the full step.")
        lay.addWidget(self.text)
        lay.addStretch(1)


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

    def __init__(self, parent=None, session: ImportSession = None):
        """!
        @param parent Qt parent (the main window).
        @param session An ImportSession; a new one when omitted.
        """
        super().__init__(parent)
        self.session = session or ImportSession()
        self.step = 0
        self.problem = None                                   # The Problem built by Import (None until the import ran)
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
        self.pages = [self.page1, PendingPage(1), PendingPage(2)]
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
            self.session.load()
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
            self.session.load()
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
        try:
            self.problem = sx.build_problem()
        except ImportNotAvailable as exc:
            self.notify("Import not available", str(exc))
            return False
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
        super().changeEvent(ev)

    def done(self, result):
        """!
        @brief Release the archive and the caches when the window closes.
        @param result Dialog result code.
        @return None
        """
        self.session.close()
        super().done(result)


__all__ = ["ImportBoardWindow", "Preview", "Stepper"]
