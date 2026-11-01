#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file ui.py
@brief Widgets of the Gerber import window prototype: the session, the zoomable preview, the three step pages, the re-import dialog and the three window layouts (tabs, wizard, hybrid).
@details PySide 6 widgets with the program theme (`pcbthermal.gui.theme`, tokens only). The pages are shared by the three layouts, so the same behaviour is tested in each. What is simulated: the Import button writes
         a summary record (JSON) and shows a message; the project is not created. Everything else reads the files for real through `backend`.
"""

import json
import html
import time
from pathlib import Path

import numpy as np
from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, QTimer, Signal, QObject
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout,
                               QHeaderView, QLabel, QLineEdit, QMessageBox, QPushButton, QRadioButton, QSizePolicy, QStackedWidget, QTableWidget, QTableWidgetItem, QTabWidget, QToolTip,
                               QVBoxLayout, QWidget)

import backend as be
from pcbthermal import memory
from pcbthermal.gui import theme as th
from pcbthermal.gui.panels import WarningList
from pcbthermal.model import Problem

STEP_TITLES = ["Files and layers", "Parts", "Model"]
STEP_SUBTITLES = ["Choose the folder or ZIP, check the function of every file and the stack-up.",
                  "Turn paste openings into heat sources: click an opening, give a power in W, choose the shape.",
                  "Choose how the copper is given to the models, the cell, the vias; read the memory verdict."]


def spin(lo, hi, value, decimals, suffix, tip):
    """!
    @brief A spin box with a unit and a tooltip.
    @param lo Minimum.
    @param hi Maximum.
    @param value Initial value.
    @param decimals Decimals shown.
    @param suffix Unit text.
    @param tip Tooltip text.
    @return QDoubleSpinBox.
    """
    s = QDoubleSpinBox()
    s.setRange(lo, hi)
    s.setDecimals(decimals)
    s.setValue(value)
    s.setSuffix(" " + suffix)
    s.setToolTip(tip)
    return s


class Session(QObject):
    """!
    @brief The state of one import: files, board read from them, parts, selection and the choices of step 3 (shared by the pages of every layout).
    """

    board_changed = Signal()
    parts_changed = Signal()
    selection_changed = Signal()

    def __init__(self, workdir, out_dir, previous="none"):
        """!
        @brief Create an empty session.
        @param workdir Folder for extracted archives and synthetic boards.
        @param out_dir Folder where the Import button writes its summary.
        @param previous "none", "demo" (a stored import made from the board with edits) or the path of a summary JSON.
        """
        super().__init__()
        self.workdir, self.out_dir, self.previous_mode = workdir, Path(out_dir), previous
        self.files, self.board, self.parts, self.unmatched = [], None, [], []
        self.selected, self.sel_layer, self.name, self.source_text = None, "Top copper", "board", ""
        self.mapping, self.cell, self.previous = "faces", 1.0, None
        self.cache = {}
        self.visited = {0}

    def open(self, path, label=""):
        """!
        @brief Read a folder or ZIP: scan the files, read the board, match the parts.
        @param path Folder or .zip.
        @param label Text that says which board it is.
        @return None
        """
        folder = be.open_source(path, be.tempfile.mkdtemp(dir=self.workdir))
        self.files = be.scan(folder)
        self.name, self.source_text = Path(path).stem or Path(path).name, label or str(path)
        self.reload()

    def reload(self):
        """!
        @brief Read the board again from the files as assigned (after a function or use change) and rematch the parts, keeping the powers of the parts that still exist.
        @return None
        """
        old = {p["ref"]: p for p in self.parts}
        self.board = be.load_board(self.files, self.cache) if not be.check_files(self.files) else None
        if self.board is not None:
            self.parts, self.unmatched = be.match_parts(self.board)
            for p in self.parts:
                o = old.get(p["ref"])
                if o:
                    for k in ("use", "power", "tj", "role", "shape_user"):
                        p[k] = o[k]
                    if o["shape_user"] and p.get("box") is not None:
                        p["shape"] = o["shape"]
            self.cell = max(self.cell, 0.1)
        else:
            self.parts, self.unmatched = [], []
        self.board_changed.emit()
        self.parts_changed.emit()

    def problems(self):
        """!
        @brief Blocking problems of step 1.
        @return list of text lines.
        """
        return be.check_files(self.files) if self.files else ["No folder or ZIP chosen"]

    def complete(self):
        """!
        @brief Step 1 is complete.
        @return bool
        """
        return not self.problems() and self.board is not None

    def heat_sources(self):
        """!
        @brief The parts ticked as heat sources.
        @return list of part dicts.
        """
        return [p for p in self.parts if p["use"]]

    def part(self, ref):
        """!
        @brief A part by designator.
        @param ref Designator.
        @return dict or None.
        """
        return next((p for p in self.parts if p["ref"] == ref), None)

    def select(self, ref):
        """!
        @brief Select a part (table row and preview follow).
        @param ref Designator or None.
        @return None
        """
        self.selected = ref
        self.selection_changed.emit()

    def make_previous(self):
        """!
        @brief Build the stored import that the Import command meets (prototype: from the same board with edits, or from a summary file).
        @return None
        """
        if self.previous_mode == "none" or self.board is None:
            self.previous = None
        elif self.previous_mode == "demo":
            self.previous = be.demo_previous(be.build_record(self.name, self.board, self.files, self.parts, self.mapping, self.cell))
        else:
            self.previous = json.loads(Path(self.previous_mode).read_text())["record"]


# ------------------------------------------------------------------------------------------------------------------------------------ preview
class Preview(QWidget):
    """!
    @brief Zoomable preview of the board: copper, outline, holes, paste openings, parts (mouse wheel zooms, drag pans, double click resets, click selects).
    """

    clicked = Signal(float, float, bool)

    def __init__(self, session, theme, mode):
        """!
        @brief Create the preview.
        @param session Session.
        @param theme "light" or "dark".
        @param mode "layers", "parts" or "model".
        """
        super().__init__()
        self.sx, self.theme, self.mode = session, theme, mode
        self.c = th.colors(theme)
        self.show_layers = {"copper": True, "outline": True, "holes": True, "paste": True, "sources": True}
        self.side, self.cell = "top", 0.0
        self.zoom, self.pan, self._press, self._moved, self._last = 1.0, QPointF(0, 0), None, False, None
        self.images = {}
        self.setMinimumSize(380, 380)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)
        self.setToolTip("Preview of the board. Mouse wheel zooms, drag pans, double click shows all. In the Parts step a click on a paste opening selects its part (Ctrl+click adds the opening to the selected part).")
        session.board_changed.connect(self.rebuild)
        session.selection_changed.connect(self.update)
        session.parts_changed.connect(self.update)
        self.rebuild()

    def rebuild(self):
        """!
        @brief Make the images of the layers from the session board.
        @return None
        """
        self.images = {}
        b = self.sx.board
        if b is None:
            self.update()
            return
        cols = {"Top copper": self.c["copper"], "Bottom copper": "#4f86c6" if self.theme == "dark" else "#2f6db3"}
        for fn, cov in b["copper"]:
            self.images[fn] = self._rgba(np.clip(cov, 0, 1), QColor(cols.get(fn, "#8e6fd0")))
        if b["outline"] is not None:
            self.images["outline"] = self._rgba(b["outline"].astype(float), QColor("#ffd60a" if self.theme == "dark" else "#be8200"))
        self.update()

    @staticmethod
    def _rgba(cov, color):
        """!
        @brief A colour image whose alpha is a coverage array.
        @param cov Float array 0..1.
        @param color QColor.
        @return QImage (a copy, so the array may go away).
        """
        rgba = np.zeros(cov.shape + (4,), np.uint8)
        rgba[..., 0], rgba[..., 1], rgba[..., 2] = color.red(), color.green(), color.blue()
        rgba[..., 3] = np.clip(cov * 255, 0, 255).astype(np.uint8)
        return QImage(rgba.data, cov.shape[1], cov.shape[0], 4 * cov.shape[1], QImage.Format_RGBA8888).copy()

    def _geometry(self):
        """!
        @brief Scale and origin of the current view (pixels per mm; top-left pixel of the board).
        @return tuple (scale, ox, oy).
        """
        b = self.sx.board
        s0 = min((self.width() - 20) / b["w"], (self.height() - 20) / b["h"])
        s = s0 * self.zoom
        return s, (self.width() - b["w"] * s) / 2 + self.pan.x(), (self.height() - b["h"] * s) / 2 + self.pan.y()

    def to_px(self, x, y):
        """!
        @brief Board millimetres to widget pixels.
        @param x X (mm).
        @param y Y (mm).
        @return QPointF.
        """
        b = self.sx.board
        s, ox, oy = self._geometry()
        return QPointF(ox + (x - b["box"][0]) * s, oy + (b["box"][3] - y) * s)

    def from_px(self, p):
        """!
        @brief Widget pixels to board millimetres.
        @param p QPointF.
        @return tuple (x, y) in mm.
        """
        b = self.sx.board
        s, ox, oy = self._geometry()
        return b["box"][0] + (p.x() - ox) / s, b["box"][3] - (p.y() - oy) / s

    def paintEvent(self, ev):
        """!
        @brief Paint the board.
        @param ev Paint event.
        @return None
        """
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(self.c["canvas"]))
        b = self.sx.board
        if b is None:
            p.setPen(QColor(self.c["muted"]))
            p.drawText(self.rect(), Qt.AlignCenter, "No board yet: complete the file list.")
            p.end()
            return
        s, ox, oy = self._geometry()
        rect = QRectF(ox, oy, b["w"] * s, b["h"] * s)
        p.fillRect(rect, QColor(self.c["board"]).darker(150))
        if self.show_layers["copper"]:
            for fn, _ in reversed(b["copper"]):                                 # bottom first, the selected layer at full strength
                p.setOpacity(1.0 if fn == self.sx.sel_layer or self.mode != "layers" and fn == "Top copper" else 0.35)
                p.drawImage(rect, self.images[fn])
        p.setOpacity(1.0)
        if self.show_layers["outline"] and "outline" in self.images:
            p.drawImage(rect, self.images["outline"])
        if self.mode == "model" and self.cell:
            p.setPen(QPen(th.qcolor(self.c["solver_grid"]), 1))
            x0, y0, x1, y1 = b["box"]
            for k in range(int((x1 - x0) / self.cell) + 2):
                p.drawLine(self.to_px(x0 + k * self.cell, y0), self.to_px(x0 + k * self.cell, y1))
            for k in range(int((y1 - y0) / self.cell) + 2):
                p.drawLine(self.to_px(x0, y0 + k * self.cell), self.to_px(x1, y0 + k * self.cell))
        if self.show_layers["holes"]:
            p.setBrush(Qt.NoBrush)
            for (x, y, d, plated) in b["holes"]:
                p.setPen(QPen(QColor(self.c["via"]) if d <= 0.5 else QColor("#ff9ec4"), 1.2))
                r = max(d * s / 2, 1.6)
                p.drawEllipse(self.to_px(x, y), r, r)
        if self.mode == "parts":
            self._paint_parts(p)
        p.setPen(QColor(self.c["muted"]))
        p.drawText(10, self.height() - 8, f"{b['w']:.1f} x {b['h']:.1f} mm   zoom {self.zoom:.1f}x")
        p.end()

    def _paint_parts(self, p):
        """!
        @brief Paste openings (matched white, unmatched red), the shapes of the heat sources and of the selected part.
        @param p QPainter.
        @return None
        """
        owner = {gid: q["ref"] for q in self.sx.parts for gid in q["groups"]}
        sel = self.sx.part(self.sx.selected) if self.sx.selected else None
        sel_ids = set(sel["groups"]) if sel else set()
        if self.show_layers["paste"]:
            for g in self.sx.board["groups"][self.side]:
                for pad in g["pads"]:
                    bb = pad["bbox"]
                    r = QRectF(self.to_px(bb[0], bb[3]), self.to_px(bb[2], bb[1]))
                    if g["id"] not in owner:
                        p.setPen(QPen(QColor("#ff4d4d"), 1.6))
                        p.setBrush(QColor(255, 77, 77, 90))
                    else:
                        p.setPen(QPen(QColor(self.c["accent"]) if g["id"] in sel_ids else QColor("#d9d9d9"), 1.6 if g["id"] in sel_ids else 1))
                        p.setBrush(QColor(255, 255, 255, 70))
                    p.drawRect(r)
        for q in self.sx.parts:
            poly = be.shape_polygon(q)
            if poly and q["use"] and q["side"] == self.side and self.show_layers["sources"]:
                p.setPen(QPen(QColor(self.c["heater"]), 1.5, Qt.DashLine))
                p.setBrush(Qt.NoBrush)
                p.drawPolygon(QPolygonF([self.to_px(x, y) for x, y in poly]))
        if sel and sel.get("box") is not None:
            p.setPen(QPen(QColor(self.c["heater"]), 2.2))
            p.setBrush(QColor(255, 91, 79, 55))
            p.drawPolygon(QPolygonF([self.to_px(x, y) for x, y in be.shape_polygon(sel)]))
            other = "box" if sel["shape"] == "hull" else "hull"
            alt = sel["hull"] if other == "hull" else None
            if other == "box":
                bb = sel["box"]
                alt = [(bb[0], bb[1]), (bb[2], bb[1]), (bb[2], bb[3]), (bb[0], bb[3])]
            if alt is not None:
                p.setPen(QPen(QColor("#33d6a6"), 1.8, Qt.DotLine))
                p.setBrush(Qt.NoBrush)
                p.drawPolygon(QPolygonF([self.to_px(x, y) for x, y in alt]))
            f = QFont(self.font())
            f.setBold(True)
            p.setFont(f)
            p.setPen(QColor(self.c["text"]))
            p.drawText(self.to_px(sel["box"][0], sel["box"][3]) + QPointF(-4, -6), f"{sel['ref']}  {sel['package'][:14]}")

    def wheelEvent(self, ev):
        """!
        @brief Zoom about the pointer.
        @param ev Wheel event.
        @return None
        """
        if self.sx.board is None:
            return
        pos = ev.position()
        before = self.from_px(pos)
        self.zoom = float(np.clip(self.zoom * 1.25 ** (ev.angleDelta().y() / 120.0), 1.0, 40.0))
        after = self.to_px(*before)
        self.pan += pos - after                                              # keep the point under the pointer fixed
        self.update()

    def mousePressEvent(self, ev):
        """!
        @brief Start a click or a drag.
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
        @brief A release without a drag is a click on the board.
        @param ev Mouse event.
        @return None
        """
        if self._press is not None and not self._moved and self.sx.board is not None:
            x, y = self.from_px(ev.position())
            self.clicked.emit(x, y, bool(ev.modifiers() & Qt.ControlModifier))
        self._press = None

    def mouseDoubleClickEvent(self, ev):
        """!
        @brief Show the whole board again.
        @param ev Mouse event.
        @return None
        """
        self.zoom, self.pan = 1.0, QPointF(0, 0)
        self.update()


# ------------------------------------------------------------------------------------------------------------------------------------ step 1
class Step1(QWidget):
    """!
    @brief Step 1, files and layers: source, file table with editable function, stack-up, preview.
    """

    def __init__(self, sx, theme, window):
        """!
        @brief Build the page.
        @param sx Session.
        @param theme "light" or "dark".
        @param window The import window (for the file dialogs).
        """
        super().__init__()
        self.sx, self.theme, self.win = sx, theme, window
        lay = QHBoxLayout(self)
        left = QVBoxLayout()
        row = QHBoxLayout()
        row.addWidget(QLabel("Folder or ZIP"))
        self.src = QLineEdit()
        self.src.setToolTip("A folder or a ZIP archive with the Gerber files, the Excellon drill files and, optionally, the placement (pick and place) file of the same board. Press Enter to read it.")
        self.src.returnPressed.connect(lambda: self.win.open_path(self.src.text()))
        row.addWidget(self.src, 1)
        for text, tip, fn in (("Folder…", "Choose a folder of fabrication files.", self._folder), ("ZIP…", "Choose a ZIP archive of fabrication files.", self._zip)):
            b = QPushButton(text)
            b.setToolTip(tip)
            b.clicked.connect(fn)
            row.addWidget(b)
        left.addLayout(row)
        self.box = QGroupBox("Files found")
        gl = QVBoxLayout(self.box)
        note = QLabel("The function of each file was detected from its Gerber X2 attributes, then from its name. Check it and change it when it is wrong.")
        note.setWordWrap(True)
        th.hint(note)
        gl.addWidget(note)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Use", "File", "Size", "Function", "Detected from"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setMinimumHeight(260)
        self.table.setToolTip("One row per file. Untick a file to leave it out, or change its function. The models read copper, outline and drills; paste and placement give the parts; mask and legend are not used.")
        self.table.itemSelectionChanged.connect(self._row_selected)
        gl.addWidget(self.table)
        self.problem = QLabel("")
        self.problem.setWordWrap(True)
        gl.addWidget(self.problem)
        left.addWidget(self.box)
        g2 = QGroupBox("Stack-up")
        f = QFormLayout(g2)
        self.layers_label = QLabel("")
        self.layers_label.setToolTip("Number of copper layers: the copper files that are in use. Change a function in the table when the set is incomplete.")
        f.addRow("Copper layers", self.layers_label)
        tpl = QComboBox()
        tpl.addItems(["Typical stack-up of the program", "Edit in the Stack-up tab after the import"])
        tpl.setToolTip("Dielectric thicknesses of the program's typical stack-up (not a fabricator table). The files do not carry them; the Gerber job file does the board thickness when it is present.")
        f.addRow("Dielectrics", tpl)
        w = QComboBox()
        w.addItems(["0.5 oz", "1 oz", "2 oz", "3 oz"])
        w.setCurrentText("1 oz")
        w.setToolTip("Copper weight (1 oz is 35 µm): it sets the sheet conductance and the heat capacity of the imported copper. Not in the Gerber copper files.")
        f.addRow("Copper weight", w)
        n = QLabel("The heat capacity of the copper is set at import from the weight and from the coverage of every cell.")
        n.setWordWrap(True)
        th.hint(n)
        f.addRow(n)
        left.addWidget(g2)
        lay.addLayout(left, 11)
        right = QVBoxLayout()
        bar = QHBoxLayout()
        self.preview = Preview(sx, theme, "layers")
        for key, label in (("copper", "Copper"), ("outline", "Outline"), ("holes", "Holes")):
            c = QCheckBox(label)
            c.setChecked(True)
            c.setToolTip(f"Show or hide: {label.lower()}. The layer selected in the table is drawn at full strength.")
            c.toggled.connect(lambda on, k=key: (self.preview.show_layers.__setitem__(k, on), self.preview.update()))
            bar.addWidget(c)
        bar.addStretch(1)
        right.addLayout(bar)
        right.addWidget(self.preview, 1)
        cap = QLabel("Preview: the selected copper layer at full strength. Yellow rings are holes up to 0.5 mm (vias), pink rings larger ones. Wheel zooms, drag pans.")
        cap.setWordWrap(True)
        th.hint(cap)
        right.addWidget(cap)
        lay.addLayout(right, 9)
        sx.board_changed.connect(self.refresh)
        self.refresh()

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

    def _row_selected(self):
        """!
        @brief The layer of the selected row is the one drawn at full strength.
        @return None
        """
        r = self.table.currentRow()
        if 0 <= r < len(self.sx.files) and self.sx.files[r]["func"] in be.COPPER:
            self.sx.sel_layer = self.sx.files[r]["func"]
            self.preview.update()

    def refresh(self):
        """!
        @brief Fill the table and the messages from the session (the table is not rebuilt when only the board changed).
        @return None
        """
        sx = self.sx
        if self.table.rowCount() != len(sx.files) or any(self.table.item(i, 1) is None or self.table.item(i, 1).text() != f["name"] for i, f in enumerate(sx.files)):
            self._fill()
        self.src.setText(sx.source_text)
        self.box.setTitle(f"Files found ({len(sx.files)})")
        probs = sx.problems()
        c = th.colors(self.theme)
        if probs:
            self.problem.setText(f'<span style="color:{c["heater"]}">' + "<br>".join(html.escape(t) for t in probs) + "</span>")
        else:
            warn = "" if any(f["use"] and f["func"] == "Board outline / profile" for f in sx.files) else " No board outline: the box of the copper is used."
            self.problem.setText(f'<span style="color:{c["muted"]}">Step 1 is complete.{html.escape(warn)}</span>')
        self.layers_label.setText(str(sum(1 for f in sx.files if f["use"] and f["func"] in be.COPPER)))

    def _fill(self):
        """!
        @brief Rebuild the file table.
        @return None
        """
        t = self.table
        t.blockSignals(True)
        t.setRowCount(len(self.sx.files))
        for r, f in enumerate(self.sx.files):
            it = QTableWidgetItem()
            it.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            it.setCheckState(Qt.Checked if f["use"] else Qt.Unchecked)
            t.setItem(r, 0, it)
            for c, v in ((1, f["name"]), (2, f"{f['size'] / 1000:.1f} kB"), (4, f["how"])):
                item = QTableWidgetItem(v)
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                t.setItem(r, c, item)
            cb = QComboBox()
            cb.addItems(be.FUNCTIONS)
            cb.setCurrentText(f["func"])
            cb.setToolTip("What the file is. Inner copper layers are numbered from the top.")
            cb.currentTextChanged.connect(lambda txt, i=r: self._func(i, txt))
            t.setCellWidget(r, 3, cb)
        t.cellChanged.connect(self._use) if not getattr(self, "_wired", False) else None
        self._wired = True
        hh = t.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.Fixed)
        t.setColumnWidth(3, 190)
        hh.setSectionResizeMode(4, QHeaderView.Stretch)
        t.blockSignals(False)

    def _func(self, i, text):
        """!
        @brief The user changed the function of file i.
        @param i Row.
        @param text New function.
        @return None
        """
        self.sx.files[i]["func"] = text
        self.sx.files[i]["use"] = text != "Ignore"
        self.win.reload_later()

    def _use(self, r, c):
        """!
        @brief The user ticked or unticked a file.
        @param r Row.
        @param c Column.
        @return None
        """
        if c == 0 and r < len(self.sx.files):
            self.sx.files[r]["use"] = self.table.item(r, 0).checkState() == Qt.Checked
            self.win.reload_later()


# ------------------------------------------------------------------------------------------------------------------------------------ step 2
class Step2(QWidget):
    """!
    @brief Step 2, parts: placement and paste to heat sources, power table, shape, preview with clicks.
    """

    def __init__(self, sx, theme, window):
        """!
        @brief Build the page.
        @param sx Session.
        @param theme "light" or "dark".
        @param window The import window.
        """
        super().__init__()
        self.sx, self.theme, self.win, self._building = sx, theme, window, False
        lay = QHBoxLayout(self)
        left = QVBoxLayout()
        self.info = QLabel("")
        self.info.setWordWrap(True)
        left.addWidget(self.info)
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(["Heat source", "Part", "Package", "Openings", "Size (mm)", "Position (mm)", "Power", "Tj max", "Role"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setToolTip("The parts of the placement file. Tick a part to make it a heat source and give it a power. Click a row, or a paste opening in the preview, to select a part.")
        self.table.itemSelectionChanged.connect(self._row)
        left.addWidget(self.table, 1)
        g = QGroupBox("Shape of the heat source of the selected part")
        gl = QVBoxLayout(g)
        self.r_box, self.r_hull = QRadioButton("Bounding box of the paste openings"), QRadioButton("Convex hull of the paste openings")
        self.r_box.setToolTip("A rectangle around all the openings of the part: the power spreads over the gaps between pads too. Drawn solid red when chosen, dotted green when not.")
        self.r_hull.setToolTip("The smallest convex polygon around the openings: follows the pads of a part with a tab.")
        grp = QButtonGroup(g)
        grp.addButton(self.r_box)
        grp.addButton(self.r_hull)
        self.r_box.toggled.connect(self._shape)
        self.r_hull.toggled.connect(self._shape)
        gl.addWidget(self.r_box)
        gl.addWidget(self.r_hull)
        self.suggest = QLabel("")
        self.suggest.setWordWrap(True)
        th.hint(self.suggest)
        gl.addWidget(self.suggest)
        left.addWidget(g)
        row = QHBoxLayout()
        for text, tip, fn in (("Make selected a heat source", "Tick the selected part as a heat source.", self._make_selected),
                              ("All parts with a power", "Tick every part that already has a power.", self._all_power), ("All matched parts", "Tick every part that has a paste opening (0 W until you give a power).", self._all_matched)):
            b = QPushButton(text)
            b.setToolTip(tip)
            b.clicked.connect(fn)
            row.addWidget(b)
        left.addLayout(row)
        lay.addLayout(left, 13)
        right = QVBoxLayout()
        bar = QHBoxLayout()
        self.preview = Preview(sx, theme, "parts")
        self.side = QComboBox()
        self.side.addItems(["Top side", "Bottom side"])
        self.side.setToolTip("Which side's paste openings are shown and clickable.")
        self.side.currentIndexChanged.connect(lambda i: (setattr(self.preview, "side", "top" if i == 0 else "bottom"), self.preview.update()))
        bar.addWidget(self.side)
        for key, label in (("copper", "Copper"), ("paste", "Paste openings"), ("sources", "Heat sources")):
            c = QCheckBox(label)
            c.setChecked(True)
            c.toggled.connect(lambda on, k=key: (self.preview.show_layers.__setitem__(k, on), self.preview.update()))
            bar.addWidget(c)
        bar.addStretch(1)
        right.addLayout(bar)
        right.addWidget(self.preview, 1)
        cap = QLabel("Preview: white squares are matched paste openings, <b>red ones match no part</b>. Click an opening to select its part; click a red one to create a heat source from it; "
                     "Ctrl+click a red one to add it to the selected part. Dashed red: heat sources.")
        cap.setWordWrap(True)
        th.hint(cap)
        right.addWidget(cap)
        lay.addLayout(right, 9)
        self.preview.clicked.connect(self._clicked)
        sx.parts_changed.connect(self.rebuild)
        sx.selection_changed.connect(self._sync_selection)
        self.rebuild()

    def rebuild(self):
        """!
        @brief Rebuild the table from the session parts.
        @return None
        """
        sx = self.sx
        self._building = True
        t = self.table
        t.setRowCount(0)
        order = sorted(sx.parts, key=lambda q: (not q["use"], -q["power"], not q["groups"], q["ref"]))
        t.setRowCount(len(order))
        for k, q in enumerate(order):
            it = QTableWidgetItem()
            it.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            it.setCheckState(Qt.Checked if q["use"] else Qt.Unchecked)
            t.setItem(k, 0, it)
            size = "-" if q["box"] is None else f"{q['box'][2] - q['box'][0]:.1f} x {q['box'][3] - q['box'][1]:.1f}"
            vals = {1: q["ref"], 2: q["package"].replace("_Metric", "")[:22], 3: str(len(q["groups"])), 4: size, 5: f"{q['x']:.2f}, {q['y']:.2f}"}
            for c, v in vals.items():
                item = QTableWidgetItem(v)
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                if c == 1:
                    item.setToolTip(q["match"])
                    if not q["groups"]:
                        item.setForeground(QColor(th.colors(self.theme)["muted"]))
                t.setItem(k, c, item)
            sp = spin(0, 1000, q["power"], 3, "W", "Power the part dissipates, in W. Worst case: all of it enters the board. From the datasheet or the Power Calculator.")
            sp.setEnabled(q["box"] is not None)
            sp.valueChanged.connect(lambda v, ref=q["ref"]: self._set(ref, "power", v))
            t.setCellWidget(k, 6, sp)
            tj = spin(0, 300, q["tj"], 0, "°C", "Highest junction temperature of the datasheet (0: none). The result reports the margin.")
            tj.valueChanged.connect(lambda v, ref=q["ref"]: self._set(ref, "tj", v))
            t.setCellWidget(k, 7, tj)
            cb = QComboBox()
            cb.addItems(["Component", "Source"])
            cb.setCurrentText(q["role"])
            cb.setToolTip("Component: a package with a junction (θ, Tj limit, optional heatsink on top). Source: only a heated area on the board.")
            cb.currentTextChanged.connect(lambda v, ref=q["ref"]: self._set(ref, "role", v))
            t.setCellWidget(k, 8, cb)
        hh = t.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeToContents)
        t.cellChanged.connect(self._tick) if not getattr(self, "_wired", False) else None
        self._wired = True
        self._building = False
        n_pos = sum(1 for q in sx.parts if q["groups"])
        by_ref = sum(1 for q in sx.parts if q["match"].startswith("matched by designator"))
        how = f"{by_ref} by designator (TO.C in the paste file), {n_pos - by_ref} by position" if sx.board is not None else ""
        self.info.setText(f"<b>{len(sx.parts)} parts</b>: {n_pos} with a paste opening ({how}); {len(sx.parts) - n_pos} with none. "
                          f"<span style='color:{th.colors(self.theme)['heater']}'>{len(sx.unmatched)} paste group(s) match no part (red in the preview).</span>")
        self._sync_selection()

    def _row(self):
        """!
        @brief A table row was selected.
        @return None
        """
        if self._building:
            return
        r = self.table.currentRow()
        if r >= 0 and self.table.item(r, 1):
            self.sx.selected = self.table.item(r, 1).text()
            self._shape_controls()
            self.preview.update()

    def _sync_selection(self):
        """!
        @brief Select the table row of the session's selected part.
        @return None
        """
        self._building = True
        for r in range(self.table.rowCount()):
            if self.table.item(r, 1) and self.table.item(r, 1).text() == self.sx.selected:
                self.table.selectRow(r)
        self._building = False
        self._shape_controls()
        self.preview.update()

    def _shape_controls(self):
        """!
        @brief Set the shape radios and the suggestion text for the selected part.
        @return None
        """
        q = self.sx.part(self.sx.selected) if self.sx.selected else None
        for r in (self.r_box, self.r_hull):
            r.blockSignals(True)
        ok = q is not None and q["box"] is not None
        self.r_box.setEnabled(ok)
        self.r_hull.setEnabled(ok and q["hull"] is not None)
        self.r_box.setChecked(ok and q["shape"] == "box")
        self.r_hull.setChecked(ok and q["shape"] == "hull")
        for r in (self.r_box, self.r_hull):
            r.blockSignals(False)
        if ok:
            self.suggest.setText(f"{q['ref']}: box {q['box_area']:.1f} mm², hull {q['hull_area']:.1f} mm². The program suggests the <b>{q['suggested']}</b> "
                                 f"({'hull clearly smaller than the box' if q['suggested'] == 'hull' else 'the hull is not much smaller'}); " + ("you chose another." if q["shape_user"] else "you can always change it."))
        else:
            self.suggest.setText("Select a part with a paste opening." if q is None else f"{q['ref']} has no paste opening: click a red one in the preview with Ctrl to add it.")

    def _shape(self, on):
        """!
        @brief The user chose a shape.
        @param on The toggled radio is now on.
        @return None
        """
        q = self.sx.part(self.sx.selected) if self.sx.selected else None
        if on and q is not None and q["box"] is not None:
            q["shape"] = "hull" if self.r_hull.isChecked() else "box"
            q["shape_user"] = q["shape"] != q["suggested"]
            self._shape_controls()
            self.preview.update()

    def _set(self, ref, key, v):
        """!
        @brief A cell editor changed a value; a power above 0 makes the part a heat source.
        @param ref Designator.
        @param key "power", "tj" or "role".
        @param v New value.
        @return None
        """
        q = self.sx.part(ref)
        q[key] = v
        if key == "power" and v > 0 and not q["use"]:
            q["use"] = True
            self.sx.parts_changed.emit()
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
            q = self.sx.part(self.table.item(r, 1).text())
            q["use"] = self.table.item(r, 0).checkState() == Qt.Checked and q["box"] is not None
            self.preview.update()
            self.win.update_nav()

    def _make_selected(self):
        """!
        @brief Tick the selected part.
        @return None
        """
        q = self.sx.part(self.sx.selected) if self.sx.selected else None
        if q is not None and q["box"] is not None:
            q["use"] = True
            self.sx.parts_changed.emit()

    def _all_power(self):
        """!
        @brief Tick every part with a power.
        @return None
        """
        for q in self.sx.parts:
            q["use"] = q["use"] or (q["power"] > 0 and q["box"] is not None)
        self.sx.parts_changed.emit()

    def _all_matched(self):
        """!
        @brief Tick every part with an opening.
        @return None
        """
        for q in self.sx.parts:
            q["use"] = q["use"] or q["box"] is not None
        self.sx.parts_changed.emit()

    def _clicked(self, x, y, ctrl):
        """!
        @brief A click on the preview: select the part of an opening, create a heat source from a red one, or add it to the selected part (Ctrl).
        @param x X (mm).
        @param y Y (mm).
        @param ctrl True when Ctrl was held.
        @return None
        """
        sx = self.sx
        g = be.group_at(sx.board, x, y)
        if g is None:
            return
        owner = next((q for q in sx.parts if g["id"] in q["groups"]), None)
        if owner is not None:
            sx.select(owner["ref"])
            return
        sel = sx.part(sx.selected) if sx.selected else None
        if ctrl and sel is not None:
            sel["groups"].append(g["id"])
            sel["match"] = "by position + picked by hand"
            be.refresh_shape(sx.board, sel)
            sx.unmatched.remove(g["id"])
            sx.parts_changed.emit()
        else:
            q = be.new_part_from_group(sx.board, sx.parts, g["id"])
            sx.unmatched.remove(g["id"])
            sx.selected = q["ref"]
            sx.parts_changed.emit()
        self.win.update_nav()


# ------------------------------------------------------------------------------------------------------------------------------------ step 3
class Step3(QWidget):
    """!
    @brief Step 3, model: copper mapping, mask pixel, cell and memory verdict, vias, result, warnings, grid preview.
    """

    def __init__(self, sx, theme, window):
        """!
        @brief Build the page.
        @param sx Session.
        @param theme "light" or "dark".
        @param window The import window.
        """
        super().__init__()
        self.sx, self.theme, self.win = sx, theme, window
        lay = QHBoxLayout(self)
        left = QVBoxLayout()
        g = QGroupBox("Copper mapping")
        gl = QVBoxLayout(g)
        tips = {"faces": ("Faces from the heat flow, on the reduced sheet (recommended)", "Each cell face takes the conductance of the copper pattern across it, computed from the flow. Within about 5 % of the pixel reference on 108 test cases of real copper."),
                "fill": ("Fill fraction per cell (as for a drawn zone)", "The mean copper fraction of the cell, as a drawn zone's fill. 10 to 30 % too cool on real copper: for comparison only."),
                "lambda": ("Lambda 0.5 (fast)", "A quick blend of the series and parallel limits. Better than the fill, not as good as the faces.")}
        self.radios = {}
        grp = QButtonGroup(g)
        for key, (text, tip) in tips.items():
            r = QRadioButton(text)
            r.setToolTip(tip)
            r.setChecked(key == "faces")
            r.toggled.connect(lambda on, k=key: on and setattr(sx, "mapping", k))
            grp.addButton(r)
            gl.addWidget(r)
            self.radios[key] = r
        f = QFormLayout()
        self.pix = spin(0.01, 1.0, 0.05, 3, "mm", "Pixel of the copper masks. Auto: a third of the thinnest line of the files, so that no track is lost.")
        self.pix.valueChanged.connect(lambda v: self.refresh())
        row = QHBoxLayout()
        row.addWidget(self.pix, 1)
        a = QPushButton("Auto")
        a.setToolTip("Choose the pixel from the thinnest line of the copper files.")
        a.clicked.connect(self._auto_pix)
        row.addWidget(a)
        f.addRow("Mask pixel", row)
        gl.addLayout(f)
        left.addWidget(g)
        g = QGroupBox("Grid and memory")
        f = QFormLayout(g)
        self.cell = spin(0.1, 20, 1.0, 2, "mm", "Cell of the solver grid. The mask is reduced to this grid by the mapping above.")
        self.cell.valueChanged.connect(self._cell)
        row = QHBoxLayout()
        row.addWidget(self.cell, 1)
        a = QPushButton("Auto")
        a.setToolTip("A cell of about a 50th of the board side, at least 0.5 mm.")
        a.clicked.connect(self._auto_cell)
        row.addWidget(a)
        f.addRow("Cell size", row)
        self.mem = QLabel("")
        self.mem.setWordWrap(True)
        self.mem.setToolTip("Memory verdict of the memory guard (pcbthermal.memory.check) before anything is drawn: the unknowns of the model and the masks of the import, against the limit of Preferences.")
        f.addRow(self.mem)
        left.addWidget(g)
        g = QGroupBox("Vias from the plated drills")
        f = QFormLayout(g)
        self.via_max = spin(0.1, 5, 0.5, 2, "mm", "Largest diameter of a plated hole that is a via. Larger plated holes are component holes: a lead is not modelled.")
        self.via_max.valueChanged.connect(lambda v: self.refresh())
        f.addRow("Vias up to", self.via_max)
        fill = QComboBox()
        fill.addItems(["Open", "Resin plug (0.3 W/m·K)", "Conductive paste (8 W/m·K)", "Electroplated copper"])
        fill.setToolTip("What fills the barrel: the library of Preferences, as for a drawn via.")
        f.addRow("Via fill", fill)
        self.vias = QLabel("")
        th.hint(self.vias)
        f.addRow(self.vias)
        left.addWidget(g)
        g = QGroupBox("Result")
        f = QFormLayout(g)
        self.newname = QLineEdit()
        self.newname.setToolTip("Name of the new project. In the prototype nothing is created: a summary is written instead.")
        f.addRow("New project", self.newname)
        n = QLabel("Saved as project format 2 (embedded masks, names and SHA-256 of the source files, never their path). A program older than this version refuses to open it.")
        n.setWordWrap(True)
        th.hint(n)
        f.addRow(n)
        left.addWidget(g)
        left.addStretch(1)
        lay.addLayout(left, 9)
        right = QVBoxLayout()
        right.addWidget(QLabel("<b>Warnings</b> (the import still runs)"))
        self.wl = WarningList()
        self.wl.setMinimumHeight(200)
        self.wl.setMaximumHeight(240)
        right.addWidget(self.wl)
        self.preview = Preview(sx, theme, "model")
        right.addWidget(self.preview, 1)
        cap = QLabel("Preview: the solver grid of the cell chosen on the left, over the copper.")
        th.hint(cap)
        right.addWidget(cap)
        lay.addLayout(right, 11)
        sx.board_changed.connect(self.refresh)
        sx.parts_changed.connect(self.refresh)
        self.refresh()

    def _auto_pix(self):
        """!
        @brief Mask pixel from the thinnest line.
        @return None
        """
        t = self.sx.board and self.sx.board["thinnest_line"]
        self.pix.setValue(max(0.01, round(t / 3, 3)) if t else 0.05)

    def _auto_cell(self):
        """!
        @brief Cell from the board size.
        @return None
        """
        if self.sx.board:
            self.cell.setValue(max(0.5, round(max(self.sx.board["w"], self.sx.board["h"]) / 50.0, 2)))

    def _cell(self, v):
        """!
        @brief The cell changed.
        @param v New cell (mm).
        @return None
        """
        self.sx.cell = v
        self.preview.cell = v
        self.refresh()

    def refresh(self):
        """!
        @brief Update the memory verdict, the via counts and the warnings.
        @return None
        """
        sx, b = self.sx, self.sx.board
        self.newname.setText(self.newname.text() or f"{sx.name}.pcbt.json")
        if b is None:
            self.mem.setText("No board yet.")
            self.wl.set_warnings([])
            return
        self.preview.cell = self.cell.value()
        prob = Problem.new(b["w"], b["h"], layers=max(2, b["n_layers"]))
        v = memory.check(prob, ["fvm"], self.cell.value(), base=memory.BASE_DEFAULT, refuse="return", quiet=True)[0]
        c = th.colors(self.theme)
        col = {"ok": "#66bb6a" if self.theme == "dark" else "#2e7d32", "slow": "#ffb74d" if self.theme == "dark" else "#b26a00", "refuse": c["heater"]}[v.verdict]
        px = (b["w"] / self.pix.value()) * (b["h"] / self.pix.value())
        raster = b["n_layers"] * px * 55 / memory.GB
        self.mem.setText(f'<span style="color:{col}">FVM: {v.unknowns} unknowns, about {v.estimate / memory.GB:.2f} GB of {v.limit / memory.GB:.1f} GB ({v.verdict})<br>'
                         f'Import masks: {b["n_layers"]} layers x {int(b["w"] / self.pix.value())} x {int(b["h"] / self.pix.value())} pixels, about {raster:.2f} GB while they exist (55 bytes per pixel per layer)</span>')
        plated = [h for h in b["holes"] if h[3]]
        nv = sum(1 for h in plated if h[2] <= self.via_max.value())
        self.vias.setText(f"{nv} vias, {len(plated) - nv} component holes kept out of the models; {len(b['holes']) - len(plated)} non-plated holes ignored.")
        n_pos = sum(1 for q in sx.parts if q["groups"])
        warnings = ["Lumped and Analytic models read imported copper from the cell fill and run about 1 to 16 % cool (6 % on average in the study windows).",
                    "The cell model of imported copper is approximate to a few percent, up to about 8 %; isolated diagonal copper on a coarse grid is the largest known error.",
                    "A time simulation of an imported board is 7 to 20 % fast at cells of 0.5 and 1.0 mm; 0.25 mm gives a few percent.",
                    "No physical measurement of an imported board exists yet: the accuracy is against another model of the same physics."]
        if any(q["match"].startswith("matched by position") for q in sx.parts):
            warnings.insert(3, f"The paste layer names no parts: {n_pos} of {len(sx.parts)} parts matched by position (approximate).")
        if not sx.heat_sources():
            warnings.insert(0, "No heat source is defined: the board will have no power until you add one.")
        self.wl.set_warnings(warnings)


# ------------------------------------------------------------------------------------------------------------------------------------ re-import dialog
class ReimportDialog(QDialog):
    """!
    @brief What to do when the project already holds an import: replace, update after a layout revision, add files, or cancel.
    """

    def __init__(self, old_rec, new_rec, theme, parent=None):
        """!
        @brief Build the dialog and compute the comparison with the stored import.
        @param old_rec Stored import record.
        @param new_rec Record of the new files and parts.
        @param theme "light" or "dark".
        @param parent Parent widget.
        """
        super().__init__(parent)
        self.old, self.new, self.theme = old_rec, new_rec, theme
        self.setWindowTitle("The project already has an imported board")
        self.resize(900, 640)
        c = th.colors(theme)
        self.diff = be.diff_parts(old_rec["parts"], new_rec["parts"])
        self.sources = be.classify_sources(old_rec, new_rec)
        same, reasons = be.same_board(old_rec, new_rec)
        lay = QVBoxLayout(self)
        ident = sum(1 for s in self.sources if s["status"] == "identical")
        intro = QLabel(f"The open project holds an import of <b>{html.escape(old_rec['name'])}</b> ({len(old_rec['sources'])} files, {len(old_rec['parts'])} parts). "
                       f"Of the {len(self.sources)} functions in the new set, {ident} are byte-identical to the stored files. What do you want to do?")
        intro.setWordWrap(True)
        lay.addWidget(intro)
        self.warn = QLabel("")
        self.warn.setWordWrap(True)
        if not same:
            self.warn.setText(f'<span style="color:{c["heater"]}"><b>This looks like a different board:</b> ' + "; ".join(html.escape(r) for r in reasons) +
                              ". Replacing it will lose the powers of parts that are not in the new files. Consider a new project instead.</span>")
        lay.addWidget(self.warn)
        self.radios = {}
        grp = QButtonGroup(self)
        texts = {"replace": ("Replace the previous import", "Copper, drills and outline are replaced. Parts with the same designator keep their power, Tj max, role and shape edits. Parts that disappeared are listed below and removed only if you confirm."),
                 "update": ("Update after a layout revision", "Like replace, plus a table of what changed: moved, new, removed and resized parts. Nothing is lost silently."),
                 "add": ("Add files to the existing import", "A missing layer, a drill file, a placement file or an extra paste layer. Existing data are untouched; files that claim a function the import already has are shown to choose.")}
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
            t.setColumnCount(4)
            t.setHorizontalHeaderLabels(["Function", "Stored import", "New file", "Choose"])
            rows = [s for s in self.sources if s["status"] != "only stored"]
            t.setRowCount(len(rows))
            for k, s in enumerate(rows):
                for c, v in ((0, s["function"]), (1, s["old"]["name"] if s["old"] else "-"), (2, s["new"]["name"] if s["new"] else "-")):
                    t.setItem(k, c, QTableWidgetItem(v))
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
            n_conf = len(self.combos)
            self.note.setText(f"{sum(1 for s in rows if s['status'] == 'added')} function(s) added, {n_conf} conflict(s) to choose. Existing parts, powers and copper are not touched.")
        else:
            t.setColumnCount(4)
            t.setHorizontalHeaderLabels(["Part", "Change", "Detail", "Kept from the stored import" if mode != "replace" else "Action"])
            rows = [d for d in self.diff if d["change"] != "kept"] if mode == "update" else [d for d in self.diff if d["change"] == "removed"]
            t.setRowCount(len(rows))
            for k, d in enumerate(rows):
                kept = ""
                if d["old"] and d["new"] and d["old"].get("power_w"):
                    kept = f"{d['old']['power_w']:g} W, Tj {d['old']['tj_max_c']:g} °C, {d['old']['role']}"
                for c, v in ((0, d["ref"]), (1, d["change"]), (2, d["detail"])):
                    t.setItem(k, c, QTableWidgetItem(v))
                if d["change"] == "removed":
                    it = QTableWidgetItem("Remove this part")
                    it.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                    it.setCheckState(Qt.Unchecked)
                    it.setToolTip("Unticked: the part stays in the project as an orphan until you confirm.")
                    t.setItem(k, 3, it)
                    self.checks[d["ref"]] = it
                else:
                    t.setItem(k, 3, QTableWidgetItem(kept or "nothing to keep"))
            n_keep = sum(1 for d in self.diff if d["old"] and d["new"] and d["old"].get("power_w"))
            counts = {k: sum(1 for d in self.diff if d["change"] == k) for k in ("new", "removed", "moved", "resized", "moved and resized")}
            self.note.setText(f"{n_keep} part(s) keep their power and settings. New {counts['new']}, removed {counts['removed']}, moved {counts['moved'] + counts['moved and resized']}, "
                              f"resized {counts['resized'] + counts['moved and resized']}. Removed parts stay as orphans unless ticked.")
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


# ------------------------------------------------------------------------------------------------------------------------------------ stepper
class Stepper(QWidget):
    """!
    @brief The header of the hybrid layout: numbered round markers joined by a line (current in the accent, finished with a check mark, locked muted); a click jumps to a reachable step.
    """

    step_clicked = Signal(int)

    def __init__(self, theme, states):
        """!
        @brief Create the stepper.
        @param theme "light" or "dark".
        @param states Function returning a list of (state, tooltip) per step; state is "current", "done", "ready" or "locked".
        """
        super().__init__()
        self.c, self.states = th.colors(theme), states
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
        @brief Paint markers, labels and the joining lines with the theme tokens.
        @param ev Paint event.
        @return None
        """
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        st = self.states()
        r = 15
        f = QFont(self.font())
        slots = self._slots()
        for i, (slot, (state, _)) in enumerate(zip(slots, st)):
            cx, cy = slot.left() + 8 + r, self.height() / 2
            # The line to the next marker: accent once this step is finished, border colour otherwise
            if i + 1 < len(slots):
                p.setPen(QPen(QColor(self.c["accent"] if state == "done" else self.c["border"]), 2))
                p.drawLine(QPointF(cx + r + 150, cy), QPointF(slots[i + 1].left() + 8 - 6, cy))
            accent, border = QColor(self.c["accent"]), QColor(self.c["border"])
            if state == "current":
                p.setPen(Qt.NoPen)
                p.setBrush(accent)
            elif state == "done":
                p.setPen(QPen(accent, 2))
                p.setBrush(QColor(self.c["base"]))
            else:
                p.setPen(QPen(border, 2))
                p.setBrush(QColor(self.c["alt"]))
            p.drawEllipse(QPointF(cx, cy), r, r)
            mark = QColor("#ffffff") if state == "current" else accent if state == "done" else QColor(self.c["muted"])
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
            p.setPen(QColor(self.c["text"] if state in ("current", "done") else self.c["muted"] if state == "locked" else self.c["text"]))
            p.drawText(QRectF(cx + r + 8, cy - 14, 150, 28), Qt.AlignVCenter | Qt.AlignLeft, STEP_TITLES[i])
        p.end()

    def _at(self, pos):
        """!
        @brief The step under a point.
        @param pos QPointF.
        @return int index or -1.
        """
        return next((i for i, s in enumerate(self._slots()) if s.contains(pos)), -1)

    def mousePressEvent(self, ev):
        """!
        @brief A click on a reachable marker jumps to the step.
        @param ev Mouse event.
        @return None
        """
        i = self._at(ev.position())
        if i >= 0 and self.states()[i][0] != "locked":
            self.step_clicked.emit(i)

    def event(self, ev):
        """!
        @brief Tooltip of the step under the pointer (why it is locked, or what it is).
        @param ev Event.
        @return bool
        """
        if ev.type() == QEvent.ToolTip:
            i = self._at(ev.pos().toPointF())
            if i >= 0:
                QToolTip.showText(ev.globalPos(), self.states()[i][1], self)
            else:
                QToolTip.hideText()
            return True
        return super().event(ev)

    def tip_for(self, i):
        """!
        @brief Position of a step (to show its tooltip from a test or a screenshot script).
        @param i Step index.
        @return QPoint inside the step's slot.
        """
        s = self._slots()[i]
        return s.center().toPoint()


# ------------------------------------------------------------------------------------------------------------------------------------ windows
class ImportWindow(QDialog):
    """!
    @brief The import window; the subclasses give the layout (tabs, wizard or hybrid). The pages and the behaviour are the same.
    """

    layout_name = "base"

    def __init__(self, session, theme, board_label=""):
        """!
        @brief Build the window.
        @param session Session (the board may be loaded already).
        @param theme "light" or "dark".
        @param board_label Text that says which board is shown (a banner).
        """
        super().__init__()
        self.sx, self.theme = session, theme
        self.c = th.colors(theme)
        self.setWindowTitle(f"Import Gerber files ({self.layout_name} layout, prototype)")
        self.resize(1320, 900)
        self.confirm = lambda title, text: QMessageBox.question(self, title, text) == QMessageBox.Yes
        self.notify = lambda title, text: QMessageBox.information(self, title, text)
        self.ask_reimport = lambda dlg: dlg.exec() == QDialog.Accepted
        self.last_summary = None
        lay = QVBoxLayout(self)
        banner = QLabel(f"<b>PROTOTYPE, {self.layout_name} layout.</b> The files, layers, parts and the memory verdict are real; the Import button writes a summary instead of creating the project. {html.escape(board_label)}")
        banner.setWordWrap(True)
        banner.setStyleSheet(f"background: {self.c['alt']}; color: {self.c['text']}; border: 1px solid {self.c['border']}; padding: 6px 10px; border-radius: 4px;")
        lay.addWidget(banner)
        self.pages = [Step1(session, theme, self), Step2(session, theme, self), Step3(session, theme, self)]
        self.body = lay
        self._build()
        self._reload_timer = QTimer(self)
        self._reload_timer.setSingleShot(True)
        self._reload_timer.timeout.connect(self._do_reload)
        session.parts_changed.connect(self.update_nav)
        session.board_changed.connect(self.update_nav)
        self.update_nav()

    # -- shared behaviour
    def open_path(self, path):
        """!
        @brief Read a folder or ZIP chosen by the user.
        @param path Folder or ZIP path.
        @return None
        """
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.sx.open(path)
        except (OSError, ValueError, KeyError) as e:
            self.notify("Cannot read the files", str(e))
        finally:
            QApplication.restoreOverrideCursor()

    def reload_later(self):
        """!
        @brief Read the board again soon (after a function or use change; several changes in a row cost one read).
        @return None
        """
        self._reload_timer.start(50)

    def _do_reload(self):
        """!
        @brief Read the board again.
        @return None
        """
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.sx.reload()
        finally:
            QApplication.restoreOverrideCursor()

    def can_import(self):
        """!
        @brief Import is allowed once step 1 is complete.
        @return bool
        """
        return self.sx.complete()

    def do_import(self):
        """!
        @brief The Import command: warn when no heat source is defined, ask what to do when the project already has an import, write the summary (the prototype's stand-in for the project).
        @return dict, the summary written, or None when cancelled.
        """
        sx = self.sx
        if not self.can_import():
            return None
        if not sx.heat_sources() and not self.confirm("No heat source defined", "No part is ticked as a heat source in step 2, so the imported board will have no power. Import anyway?"):
            return None
        rec = be.build_record(sx.name, sx.board, sx.files, sx.parts, sx.mapping, sx.cell)
        sx.make_previous()
        mode, changes, merged = "new project", [], rec
        if sx.previous is not None:
            dlg = ReimportDialog(sx.previous, rec, self.theme, self)
            if not self.ask_reimport(dlg):
                return None
            res = be.apply_reimport(dlg.mode, sx.previous, rec, dlg.remove_refs(), dlg.file_choice())
            mode, changes, merged = dlg.mode, res["changes"], res["record"]
        summary = {"prototype": True, "mode": mode, "layout": self.layout_name, "changes": changes, "record": merged,
                   "counts": {"heat_sources": len(sx.heat_sources()), "parts": len(sx.parts), "holes": len(sx.board["holes"]), "unmatched_openings": len(sx.unmatched)}}
        sx.out_dir.mkdir(parents=True, exist_ok=True)
        path = sx.out_dir / f"import_summary_{self.layout_name}.json"
        path.write_text(json.dumps(summary, indent=1, default=float))
        self.last_summary = summary
        self.notify("Prototype: import done", f"Mode: {mode}. Summary written to {path}. In the program this would create the project (or change the open one, as one undo step).")
        return summary

    def update_nav(self):
        """!
        @brief Refresh the buttons of the layout.
        @return None
        """

    def _build(self):
        """!
        @brief Put the pages and the buttons in the window (layout specific).
        @return None
        """
        raise NotImplementedError


class TabsWindow(ImportWindow):
    """!
    @brief Layout A: three tabs and one Import button (enabled when step 1 is complete; warns when no heat source is defined).
    """

    layout_name = "tabs"

    def _build(self):
        """!
        @brief Tabs and the bottom row.
        @return None
        """
        self.tabs = QTabWidget()
        for page, title in zip(self.pages, STEP_TITLES):
            self.tabs.addTab(page, f"Step {STEP_TITLES.index(title) + 1}: {title}")
        self.body.addWidget(self.tabs, 1)
        row = QHBoxLayout()
        self.status = QLabel("")
        th.hint(self.status)
        row.addWidget(self.status, 1)
        self.help_btn, self.close_btn, self.import_btn = QPushButton("Help"), QPushButton("Close"), QPushButton("Import")
        self.import_btn.setObjectName("primary")
        self.import_btn.setToolTip("Build a new project from the files as set in the three steps. Enabled when step 1 is complete; warns if no heat source is defined.")
        self.import_btn.clicked.connect(self.do_import)
        self.close_btn.clicked.connect(self.reject)
        for b in (self.help_btn, self.close_btn, self.import_btn):
            row.addWidget(b)
        self.body.addLayout(row)

    def update_nav(self):
        """!
        @brief Import enabled when step 1 is complete; status line.
        @return None
        """
        if not hasattr(self, "import_btn"):
            return
        self.import_btn.setEnabled(self.can_import())
        self.status.setText("Step 1 is complete: Import is available." if self.can_import() else "Import is disabled: " + "; ".join(self.sx.problems()))


class SteppedWindow(ImportWindow):
    """!
    @brief Base of the layouts with a stack of pages and Back / Next buttons (wizard and hybrid).
    """

    def _stack_and_nav(self):
        """!
        @brief The page stack and the bottom row with Back, Next and Import.
        @return None
        """
        self.stack = QStackedWidget()
        for p in self.pages:
            self.stack.addWidget(p)
        self.body.addWidget(self.stack, 1)
        row = QHBoxLayout()
        self.status = QLabel("")
        th.hint(self.status)
        row.addWidget(self.status, 1)
        self.help_btn, self.close_btn = QPushButton("Help"), QPushButton("Close")
        self.early_btn = QPushButton("Import now")
        self.early_btn.setToolTip("Import with what is set so far, before the last step (the later steps keep their defaults). Available once step 1 is complete; warns if no heat source is defined.")
        self.back_btn, self.next_btn = QPushButton("Back"), QPushButton("Next")
        self.next_btn.setObjectName("primary")
        self.close_btn.clicked.connect(self.reject)
        self.early_btn.clicked.connect(self.do_import)
        self.back_btn.clicked.connect(lambda: self.go(self.step - 1))
        self.next_btn.clicked.connect(self._next)
        for b in (self.help_btn, self.close_btn, self.early_btn, self.back_btn, self.next_btn):
            row.addWidget(b)
        self.body.addLayout(row)
        self.step = 0

    def _next(self):
        """!
        @brief Next, or Import on the last step.
        @return None
        """
        if self.step == 2:
            self.do_import()
        else:
            self.go(self.step + 1)

    def reachable(self, i):
        """!
        @brief Whether a step can be opened now.
        @param i Step index.
        @return bool
        """
        return i == 0 or self.sx.complete()

    def go(self, i):
        """!
        @brief Show step i if it is reachable.
        @param i Step index.
        @return None
        """
        if 0 <= i < 3 and self.reachable(i):
            self.step = i
            self.stack.setCurrentIndex(i)
            self.sx.visited.add(i)
            self.update_nav()

    def update_nav(self):
        """!
        @brief Back / Next / Import buttons and the status line.
        @return None
        """
        if not hasattr(self, "next_btn"):
            return
        last = self.step == 2
        self.back_btn.setEnabled(self.step > 0)
        self.next_btn.setText("Import" if last else "Next")
        self.next_btn.setEnabled(self.can_import() if last or self.step == 0 else True)
        if self.step == 0:
            self.next_btn.setEnabled(self.sx.complete())
        self.early_btn.setVisible(not last)
        self.early_btn.setEnabled(self.can_import())
        self.status.setText("" if self.can_import() else "Next is disabled: " + "; ".join(self.sx.problems()))
        self._update_chrome()

    def _update_chrome(self):
        """!
        @brief Update the step indicator (layout specific).
        @return None
        """


class WizardWindow(SteppedWindow):
    """!
    @brief Layout B: a modal-style wizard, a text step indicator on top, Back / Next / Import at the bottom.
    """

    layout_name = "wizard"

    def _build(self):
        """!
        @brief Indicator, stack, buttons.
        @return None
        """
        self.ind = QLabel("")
        self.ind.setToolTip("Where you are in the three steps.")
        self.body.addWidget(self.ind)
        self._stack_and_nav()
        self.update_nav()

    def _update_chrome(self):
        """!
        @brief Bold the current step in the indicator.
        @return None
        """
        parts = [(f"<b>{i + 1} {t}</b>" if i == self.step else f"<span style='color:{self.c['muted']}'>{i + 1} {t}</span>") for i, t in enumerate(STEP_TITLES)]
        self.ind.setText("  ›  ".join(parts))


class HybridWindow(SteppedWindow):
    """!
    @brief Layout C (hybrid): a stepper header with clickable numbered markers and a one-line subtitle, Back / Next (Import on the last step), and Import now once step 1 is complete.
    """

    layout_name = "hybrid"

    def _build(self):
        """!
        @brief Stepper, subtitle, stack, buttons.
        @return None
        """
        self.stepper = Stepper(self.theme, self.step_states)
        self.stepper.step_clicked.connect(self.go)
        self.body.addWidget(self.stepper)
        self.subtitle = QLabel("")
        th.hint(self.subtitle)
        self.body.addWidget(self.subtitle)
        self._stack_and_nav()
        self.update_nav()

    def step_states(self):
        """!
        @brief State and tooltip of every step for the stepper.
        @return list of (state, tooltip).
        """
        sx = self.sx
        out = []
        for i, t in enumerate(STEP_TITLES):
            if i == self.step:
                out.append(("current", f"Step {i + 1}: {t}. You are here."))
            elif not self.reachable(i):
                out.append(("locked", f"Locked: step 1 is not complete. {'; '.join(sx.problems())}."))
            elif i == 0:
                out.append(("done", "Step 1: files and layers are complete. Click to go back."))
            elif i == 1 and sx.heat_sources():
                out.append(("done", f"Step 2: {len(sx.heat_sources())} heat source(s) defined. Click to open."))
            else:
                out.append(("ready", f"Step {i + 1}: {t}. Click to open."))
        return out

    def _update_chrome(self):
        """!
        @brief Repaint the stepper and set the subtitle.
        @return None
        """
        self.stepper.update()
        self.subtitle.setText(STEP_SUBTITLES[self.step])
        self.early_btn.setToolTip("Import with what is set so far; the later steps keep their defaults. " + ("" if self.sx.heat_sources() else "No heat source is defined yet: you will be asked to confirm."))


LAYOUTS = {"tabs": TabsWindow, "wizard": WizardWindow, "hybrid": HybridWindow}


def create_window(layout, session, theme, label=""):
    """!
    @brief Make the window of a layout.
    @param layout "tabs", "wizard" or "hybrid".
    @param session Session.
    @param theme "light" or "dark".
    @param label Text that says which board is shown.
    @return ImportWindow
    """
    return LAYOUTS[layout](session, theme, label)


__all__ = ["time"]
