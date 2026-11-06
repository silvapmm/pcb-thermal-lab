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

import gc
import html
import logging
import threading

import numpy as np
from PySide6.QtCore import QEvent, QEventLoop, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QImage, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog, QFormLayout, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                               QMessageBox, QPushButton, QRadioButton, QScrollArea, QSizePolicy, QStackedWidget, QTableWidget, QTableWidgetItem, QToolTip, QVBoxLayout, QWidget)

from ..gerber import GerberError
from ..memory import MemoryGuardError
from . import theme as th
from .import_session import BOM, COPPER, COPPER_BOTTOM, COPPER_TOP, GEOMETRY, PLACEMENT, ROLES, UNIQUE, ImportSession
from ..gerber import parts as parts_mod
from .panels import WarningList

log = logging.getLogger(__name__)

STEP_TITLES = ["Files and layers", "Parts", "Model"]


def _plain_box(parent, icon, title, text, buttons):
    """!
    @brief A message box whose text is never read as rich text (a reader error quotes a file name, and a name such as `a<b>.gbr` would be markup).
    @param parent Parent widget.
    @param icon QMessageBox icon.
    @param title Window title.
    @param text Message.
    @param buttons Standard buttons.
    @return int the button pressed.
    """
    box = QMessageBox(icon, title, text, buttons, parent)
    box.setTextFormat(Qt.PlainText)
    return box.exec()


def _plain_tip(text):
    """!
    @brief A tooltip that shows text from the files as it is: Qt reads a tooltip that looks like markup as rich text, so a designator or a package name such as `<b>` or
           `<img src=...>` would be rendered; the text is escaped and its line breaks kept.
    @param text Plain text (may hold line breaks).
    @return str rich-text tooltip that displays exactly `text`.
    """
    return "<p style='white-space:pre'>" + html.escape(str(text)) + "</p>"


class _Cancelled(Exception):
    """!@brief The window was closed while a slow call ran off the GUI thread: the caller stops and the window closes when the call has ended."""
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
        self.show_layers = {"copper": True, "outline": True, "holes": True, "paste": True, "sources": True, "labels": True}
        self.hover = None                                            # Designator of the part under the pointer (step 2)
        self.setMouseTracking(True)
        self.selected = COPPER_TOP                                   # Role of the layer drawn at full strength
        self.zoom, self.pan, self._press, self._moved, self._last = 1.0, QPointF(0, 0), None, False, None
        self._images = {}                                            # (role, theme name, id of the array) -> QImage
        self.setMinimumSize(360, 340)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

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
        strip = self._legend_height()                                # The drill legend has a strip of its own under the board, so it never covers it when the whole board is shown
        s = min((self.width() - 20) / b.width, (self.height() - 20 - strip) / b.height) * self.zoom
        return s, (self.width() - b.width * s) / 2 + self.pan.x(), (self.height() - strip - b.height * s) / 2 + self.pan.y()

    def _legend_rows(self):
        """!
        @brief The drill legend as rows of entries that fit the width of the preview (the entries run left to right and wrap).
        @return list of rows; a row is a list of (kind, text, width_px). Empty when the legend is off or the board has no holes.
        """
        if self.mode != "parts" or not self.show_layers.get("holes") or self.session.board() is None:
            return []
        classes = self.hole_classes()
        f = QFont(self.font())
        f.setPixelSize(11)
        fm = QFontMetricsF(f)
        items = [(k, f"{d:.2f} mm {k} x{n}") for k, d, n in classes[:8]] + ([("", f"+ {len(classes) - 8} more")] if len(classes) > 8 else [])
        rows, row, used = [], [], 0.0
        for kind, text in items:
            w = fm.horizontalAdvance(text) + 24
            if row and used + w > self.width() - 16:
                rows.append(row)
                row, used = [], 0.0
            row.append((kind, text, w))
            used += w
        return rows + ([row] if row else [])

    def _legend_height(self) -> int:
        """!
        @brief Height (pixels) of the strip under the board that the legend takes (0 without a legend).
        @return int
        """
        rows = self._legend_rows()
        return 17 * len(rows) + 8 + 14 if rows else 0

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
            if self.show_layers["holes"]:
                self._paint_legend(p, c)
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
            # An exposed-pad part: where the part is (the hull of its pads) is a thin dashed outline without power, so that a 3 mm square is not read as a misplaced part
            outer = sx.part_hull(sel)
            if outer:
                # Review: in the muted colour and 1 px wide, on the outer edges of the pins (the hull touches them), the outline vanished at every zoom. It is drawn in the
                # text colour (the strongest contrast of either theme), 1.6 px, and pushed 4 px out of the pins so that it never lies on an opening
                pts = [self.to_px(x, y) for x, y in outer]
                gx, gy = sum(q.x() for q in pts) / len(pts), sum(q.y() for q in pts) / len(pts)
                grown = []
                for q in pts:
                    dx, dy = q.x() - gx, q.y() - gy
                    d = max((dx * dx + dy * dy) ** 0.5, 1e-9)
                    grown.append(QPointF(q.x() + 4.0 * dx / d, q.y() + 4.0 * dy / d))
                p.setPen(QPen(QColor(c["text"]), 2.4, Qt.DashLine))
                p.setBrush(Qt.NoBrush)
                p.drawPolygon(QPolygonF(grown))
            fill = QColor(c["heater"])
            fill.setAlpha(55)
            p.setPen(QPen(QColor(c["accent"]), 2.2))
            p.setBrush(fill)
            p.drawPolygon(QPolygonF([self.to_px(x, y) for x, y in sel.polygon_mm]))
        hov = sx.part(self.hover) if self.hover and self.hover != self.selected_part else None
        if hov is not None and hov.polygon_mm:
            p.setPen(QPen(QColor(c["accent"]), 1.2, Qt.DotLine))
            p.setBrush(Qt.NoBrush)
            p.drawPolygon(QPolygonF([self.to_px(x, y) for x, y in hov.polygon_mm]))
        if self.show_layers["labels"] and self.session.board() is not None:
            self._paint_labels(p, c)

    # -- labels, legend and hover of step 2
    LABEL_MIN_PX, LABEL_MAX_PX = 7.0, 14.0

    def label_pixels(self, text: str, width_px: float, height_px: float):
        """!
        @brief The pixel size of the label of a part, or None when it does not fit.
        @details The text is scaled to the part: as large as the width and the height of the part allow, at most `LABEL_MAX_PX`, so it grows with the zoom; below `LABEL_MIN_PX` it is hidden.
        @param text Designator.
        @param width_px Width of the part on the screen (pixels).
        @param height_px Height of the part on the screen (pixels).
        @return float pixel height of the font, or None.
        """
        f = QFont(self.font())
        f.setPixelSize(10)
        w10 = max(QFontMetricsF(f).horizontalAdvance(text), 1.0)
        size = min(self.LABEL_MAX_PX, 10.0 * width_px / w10, height_px / 1.15)
        return size if size >= self.LABEL_MIN_PX else None

    def hole_classes(self) -> list:
        """!
        @brief The drill classes of the board for the legend: kind (via, component hole or non-plated), diameter (mm) and how many.
        @return list of (kind, diameter, count), vias first, then component holes, then non-plated, by diameter.
        """
        b = self.session.board()
        out = {}
        for h in (b.holes if b else []):
            kind = "non-plated" if not h.plated else "via" if h.diameter <= self.session.via_max_mm else "component hole"
            out[(kind, round(h.diameter, 2))] = out.get((kind, round(h.diameter, 2)), 0) + 1
        order = {"via": 0, "component hole": 1, "non-plated": 2}
        return [(k, d, n) for (k, d), n in sorted(out.items(), key=lambda kv: (order[kv[0][0]], kv[0][1]))]

    def part_at(self, x: float, y: float):
        """!
        @brief What lies under a point of the board: the part of a paste opening, a red opening, or a part whose heat-source polygon holds the point.
        @param x X (mm, Gerber frame).
        @param y Y (mm).
        @return tuple ("part", designator), ("unmatched", None) or None.
        """
        sx = self.session
        i = parts_mod.opening_at(sx.openings(), x, y, self.side)
        if i is not None:
            des = sx.owner_of_opening(i)
            return ("part", des) if des else ("unmatched", None)
        best = None
        for q in sx.parts():
            if q.side == self.side and q.polygon_mm:
                xs, ys = [a[0] for a in q.polygon_mm], [a[1] for a in q.polygon_mm]
                area = (max(xs) - min(xs)) * (max(ys) - min(ys))
                if min(xs) <= x <= max(xs) and min(ys) <= y <= max(ys) and (best is None or area < best[0]):
                    best = (area, q.designator)
        return ("part", best[1]) if best else None

    def hover_text(self, x: float, y: float):
        """!
        @brief The tooltip of the object under a point: designator, package, source and power of a part, the meaning of a red opening, or the kind and diameter of a hole.
        @param x X (mm, Gerber frame).
        @param y Y (mm).
        @return str or None when nothing is there.
        """
        sx = self.session
        hit = self.part_at(x, y)
        if hit and hit[0] == "part":
            q = sx.part(hit[1])
            if q is not None:
                pkg = q.footprint or q.from_file.get("package", "") or "-"
                state = "heat source" if sx.is_source(q) else "not a heat source"
                return f"{q.designator}\nPackage: {pkg}\nSource: {sx.source_label(q)}\nPower: {q.power:g} W ({state})"
        if hit and hit[0] == "unmatched":
            return "Paste opening that matches no part.\nClick it to make a heat source; Ctrl+click adds it to the selected part."
        if self.show_layers["holes"] and self.session.board() is not None:
            s = self._geometry()[0]
            for h in self.session.board().holes:
                if (h.x - x) ** 2 + (h.y - y) ** 2 <= max(h.diameter / 2, 4.0 / s) ** 2:
                    kind = "non-plated hole" if not h.plated else "via" if h.diameter <= self.session.via_max_mm else "component hole"
                    return f"{kind}, drill {h.diameter:.2f} mm"
        return None

    def _paint_legend(self, p, c):
        """!
        @brief The drill legend in a strip above the zoom text, under the board: a ring in the colour of the class, the diameter, the kind and the count, in rows that wrap with the width.
        @param p QPainter.
        @param c Colour table of the theme.
        @return None
        """
        rows = self._legend_rows()
        if not rows:
            return
        f = QFont(self.font())
        f.setPixelSize(11)
        p.setFont(f)
        top = self.height() - 22 - (17 * len(rows) + 8) + 8
        for r, row in enumerate(rows):
            x, y = 8.0, top + 17 * r + 8.5
            for kind, text, w in row:
                if kind:
                    tone = "muted" if kind == "non-plated" else "via" if kind == "via" else "warn"
                    p.setPen(QPen(QColor(c[tone]), 1.4))
                    p.setBrush(Qt.NoBrush)
                    p.drawEllipse(QPointF(x + 4, y), 4, 4)
                p.setPen(QColor(c["text"]))
                p.drawText(QPointF(x + 12, y + 4), text)
                x += w

    def _paint_labels(self, p, c):
        """!
        @brief The designators of all the parts of the side shown (centred on the part, scaled with the zoom, larger parts first, a label that overlaps one already drawn or does not fit is left out),
               a "?" on the paste openings that match no part, and the diameter of the holes that are large enough on the screen; the selected and the hovered part are always labelled.
        @param p QPainter.
        @param c Colour table of the theme.
        @return None
        """
        sx = self.session
        taken = []
        bg = QColor(c["canvas"])
        bg.setAlpha(150)

        def put(text, cx, cy, size, tone, bold=False, force=False):
            """!
            @brief Draw one centred label unless it collides with an earlier one.
            @param text Label.
            @param cx Centre x (pixels).
            @param cy Centre y (pixels).
            @param size Font pixel size.
            @param tone Colour token.
            @param bold True for the selected part.
            @param force True to draw even over another label.
            @return None
            """
            f = QFont(self.font())
            f.setPixelSize(max(int(round(size)), 6))
            f.setBold(bold)
            fm = QFontMetricsF(f)
            r = QRectF(cx - fm.horizontalAdvance(text) / 2 - 1, cy - fm.height() / 2, fm.horizontalAdvance(text) + 2, fm.height())
            if not force and any(r.intersects(t) for t in taken):
                return
            taken.append(r)
            p.setFont(f)
            p.fillRect(r, bg)
            p.setPen(QColor(c[tone]))
            p.drawText(r, Qt.AlignCenter, text)

        entries = []
        for q in sx.parts():
            if q.side != self.side or not q.polygon_mm:
                continue
            xs, ys = [a[0] for a in q.polygon_mm], [a[1] for a in q.polygon_mm]
            entries.append(((max(xs) - min(xs)) * (max(ys) - min(ys)), q, (min(xs), min(ys), max(xs), max(ys))))
        entries.sort(key=lambda t: -t[0])
        special = []
        for _, q, bb in entries:
            tl, br = self.to_px(bb[0], bb[3]), self.to_px(bb[2], bb[1])
            cx, cy = (tl.x() + br.x()) / 2, (tl.y() + br.y()) / 2
            if q.designator in (self.selected_part, self.hover):
                special.append((q, cx, cy, br.x() - tl.x(), br.y() - tl.y()))
                continue
            size = self.label_pixels(q.designator, br.x() - tl.x(), br.y() - tl.y())
            if size is not None:
                put(q.designator, cx, cy, size, "text")
        owned = sx.owned_indices()
        for i, o in enumerate(sx.openings()):
            if o.side == self.side and i not in owned:
                tl, br = self.to_px(o.bbox[0], o.bbox[3]), self.to_px(o.bbox[2], o.bbox[1])
                if self.label_pixels("?", br.x() - tl.x(), br.y() - tl.y()) is not None:
                    put("?", (tl.x() + br.x()) / 2, (tl.y() + br.y()) / 2, 9, "bad")
        if self.show_layers["holes"]:
            s = self._geometry()[0]
            for h in self.session.board().holes:
                if h.diameter * s / 2 >= 11:                        # Only when the ring is large enough to carry its diameter
                    pt = self.to_px(h.x, h.y)
                    put(f"{h.diameter:.2f}", pt.x(), pt.y(), 9, "muted")
        for q, cx, cy, w, h in special:                             # The selected and the hovered part: always, on top
            put(q.designator, cx, cy, max(self.label_pixels(q.designator, w, h) or 0.0, 11.0), "text", bold=q.designator == self.selected_part, force=True)

    def hover_at(self, ev):
        """!
        @brief Hover in step 2: highlight the part under the pointer and show its tooltip.
        @param ev Mouse move event.
        @return None
        """
        x, y = self.from_px(ev.position())
        hit = self.part_at(x, y)
        now = hit[1] if hit and hit[0] == "part" else None
        if now != self.hover:
            self.hover = now
            self.update()
        text = self.hover_text(x, y)
        if text:
            QToolTip.showText(ev.globalPosition().toPoint(), _plain_tip(text), self)     # designators and packages come from the files: never rich text
        else:
            QToolTip.hideText()

    def leaveEvent(self, ev):
        """!
        @brief The pointer left the preview: drop the hover highlight.
        @param ev Leave event.
        @return None
        """
        if self.hover is not None:
            self.hover = None
            self.update()
        super().leaveEvent(ev)

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
        if self.mode == "parts" and not (ev.buttons() & Qt.LeftButton) and self.session.board() is not None:
            self.hover_at(ev)
            return
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
        self.source.returnPressed.connect(lambda: self.win.open_path(self.source.text()))
        row.addWidget(self.source, 1)
        for text, fn in (("Folder…", self._folder), ("ZIP…", self._zip), ("Files…", self._files)):
            b = QPushButton(text)
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
        self.layers_label.setTextFormat(Qt.PlainText)                       # File names and file text are never read as rich text
        self.layers_label.setToolTip("Number of copper layers (the copper files in use) and the typical stack-up of the program for that count: typical values, check your fabricator's stack-up. "
                                     "The files do not carry the dielectrics; edit them in the Stack-up tab after the import.")
        f.addRow("Copper layers", self.layers_label)
        self.outline_label = QLabel("")
        self.outline_label.setWordWrap(True)
        self.outline_label.setTextFormat(Qt.PlainText)
        self.outline_label.setToolTip("Size and area of the board outline (the profile layer). Without an outline the box of the copper is used.")
        f.addRow("Outline", self.outline_label)
        self.drill_label = QLabel("")
        self.drill_label.setWordWrap(True)
        self.drill_label.setTextFormat(Qt.PlainText)
        self.drill_label.setToolTip("Plated holes up to 0.5 mm are vias and are imported; larger plated holes are component holes (a lead is not modelled); non-plated holes are ignored.")
        f.addRow("Drills", self.drill_label)
        # The CAD tool that wrote the files (profiles.detect_profile): a plain-text line, coloured when it needs a check, and a list to change it (replaces only the profile tier)
        self.tool_row = QWidget()
        tl = QHBoxLayout(self.tool_row)
        tl.setContentsMargins(0, 0, 0, 0)
        self._tool_filling = False
        self.tool_label = QLabel("")
        self.tool_label.setTextFormat(Qt.PlainText)                         # the text is built from table names only; never rich
        self.tool_label.setWordWrap(True)
        self.tool_label.setToolTip("The program that wrote the files.")
        self.tool_pick = QComboBox()
        self.tool_pick.setToolTip("Change the CAD tool: it replaces only the file-name rules (the X2 attributes, the Excellon header and your own choice of a function still win).")
        self.tool_pick.addItem("Automatic (detected)", None)
        self.tool_pick.currentIndexChanged.connect(self._tool_changed)
        tl.addWidget(self.tool_label, 1)
        tl.addWidget(self.tool_pick)
        tl.addStretch(1)
        self.tool_row.setVisible(False)
        f.addRow(self.tool_row)
        # The bill of materials (a file with the function BOM): what was read from it, as plain text; hidden when no BOM file is in use
        self.bom_label = QLabel("")
        self.bom_label.setTextFormat(Qt.PlainText)                          # built from counts and the variant names of the file
        self.bom_label.setWordWrap(True)
        self.bom_label.setVisible(False)
        f.addRow(self.bom_label)
        left.addWidget(g)
        lay.addLayout(left, 11)
        right = QVBoxLayout()
        bar = QHBoxLayout()
        self.preview = Preview(self.session)
        self.layer_pick = QComboBox()
        self.layer_pick.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.layer_pick.setMinimumContentsLength(14)
        self.layer_pick.currentTextChanged.connect(self._layer_picked)
        bar.addWidget(self.layer_pick)
        for key, label in (("copper", "Copper"), ("outline", "Outline"), ("holes", "Holes")):
            c = QCheckBox(label)
            c.setChecked(True)
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
            if f.use and f.detected.confidence == "low" and f.detected.kind != "unknown" and not (clash or f.error):
                t.item(i, 4).setForeground(QColor(c["alert"]))              # A role guessed from the name alone: check it
            t.item(i, 0).setCheckState(Qt.Checked if f.use else Qt.Unchecked)
            cb = t.cellWidget(i, 3)
            if cb.currentText() != f.role:
                cb.blockSignals(True)
                cb.setCurrentText(f.role)
                cb.blockSignals(False)
            t.item(i, 4).setText(f.how + (f"; {f.error}" if f.error else ""))
        self._filling = False
        self._refresh_tool(c)
        self._refresh_bom(c)
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

    def _refresh_tool(self, c):
        """!
        @brief Show the CAD-tool line and its list for the files read (hidden before a set is read).
        @param c Colour table of the theme.
        @return None
        """
        sx = self.session
        text, check, tip = sx.profile_line()
        self.tool_row.setVisible(bool(text))
        if not text:
            return
        self.tool_label.setText(text)
        self.tool_label.setToolTip(tip)
        self.tool_label.setStyleSheet(f"color: {c['alert'] if check else c['text']};")      # the alert token when the detection needs a check
        self._tool_filling = True
        if self.tool_pick.count() <= 1:
            for key, name in sx.profile_keys():
                self.tool_pick.addItem(name if key != "unknown" else "None (generic rules)", key)
        self.tool_pick.setCurrentIndex(max(0, self.tool_pick.findData(sx.user_profile)))
        self._tool_filling = False

    def _refresh_bom(self, c):
        """!
        @brief Show the BOM line (counts, sections, not fitted, assembly variant) when a BOM file is in use.
        @param c Colour table of the theme.
        @return None
        """
        text, check, tip = self.session.bom_line()
        self.bom_label.setVisible(bool(text))
        self.bom_label.setText(text)
        self.bom_label.setToolTip(tip)
        self.bom_label.setStyleSheet(f"color: {c['alert'] if check else c['text']};")

    def _tool_changed(self, _):
        """!
        @brief The user chose another CAD tool: the name rules are applied again to the files whose function the user did not choose.
        @param _ Ignored (the combo index).
        @return None
        """
        if self._tool_filling or self.session.profile_result is None:
            return
        self.session.set_profile(self.tool_pick.currentData())
        self.win.refresh()
        self.win.reload_later()

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
    @details The pre-selection from the paste layer is always editable: every number, the tick, the shape (exposed pad or tab where the part has one, convex hull, box) and the openings of a part (a click on a
             red opening makes a part, Ctrl+click adds it to the selected part).
    """

    COLS = ["Heat source", "Part", "Package", "Source", "Openings", "Size (mm)", "Position (mm)", "Power", "Tj max", "Role", "BOM"]
    HEADERS = ["Heat\nsource", "Part", "Package", "Source", "Open-\nings", "Size\n(mm)", "Position\n(mm)", "Power\n(W)", "Tj max\n(°C)", "Role", "BOM\n(guess)"]
    BOM_COL = 10

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
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setToolTip("The parts of the files. Tick a part to make it a heat source and give it a power in W. The Source column says how the part was found: X3 component layer, "
                              "paste TO.C + placement, by position (approx.), paste only, or placement only (no opening); hold the pointer on the Source cell for what it means. Click a row, or a part or paste opening in the preview, to select it.")
        self.table.itemSelectionChanged.connect(self._row)
        self.table.cellChanged.connect(self._tick)
        left.addWidget(self.table, 1)
        g = QGroupBox("Shape of the heat source of the selected part")
        gl = QVBoxLayout(g)
        self.radios = {}
        grp = QButtonGroup(g)
        for key, text, tip in (("exposed", "Exposed pad or tab (suggested for QFN, DFN, SOT-223, DPAK)", "The hull of the dominant group of paste openings: the exposed thermal pad of a QFN or DFN or the tab of a SOT-223 or DPAK. "
                                "These packages put almost all their heat through that pad and the datasheet θJC(bottom) is measured to it, so the whole power goes there (worst case: the leads, "
                                "which carry a few per cent, are left out). Give the part θ = θJC(bottom): its junction is then the hottest point under the pad plus θ times the power. "
                                "The outline of the part is drawn dashed. A single tab is this choice too. Enabled only for a part whose paste has such a pad."),
                               ("hull", "Convex hull of the paste openings (suggested for other parts)", "The smallest convex polygon around the openings: the area of the pads of the part. For a part with an exposed pad or a tab it spreads the heat "
                                "over a body that does not carry it and reads the junction 10 to 40 % cooler."),
                               ("box", "Bounding box of the paste openings", "A rectangle around all the openings: the power spreads over the gaps between pads too.")):
            r = QRadioButton(text)
            r.setToolTip(tip)
            r.toggled.connect(lambda on, k=key: on and self._shape(k))
            grp.addButton(r)
            gl.addWidget(r)
            self.radios[key] = r
        self.suggest = QLabel("")
        self.suggest.setWordWrap(True)
        self.suggest.setTextFormat(Qt.PlainText)                            # it quotes a designator of the files
        th.hint(self.suggest)
        gl.addWidget(self.suggest)
        left.addWidget(g)
        row = QHBoxLayout()
        for text, fn in (("Make selected a heat source", self._make_selected), ("All parts with a power", self._all_power), ("All matched parts", self._all_matched)):
            b = QPushButton(text)
            b.clicked.connect(fn)
            row.addWidget(b)
        self.bom_roles_btn = QPushButton("Use the BOM roles")
        self.bom_roles_btn.setToolTip("Set the Role (Component or Source) of every part whose Role you have not set to the role the BOM suggests from the designator, the footprint and the value. "
                                      "It is a guess from the names; parts it calls connectors, capacitors, test points or unknown keep their Role. Nothing is applied until you press this.")
        self.bom_roles_btn.clicked.connect(self._use_bom_roles)
        self.bom_roles_btn.setVisible(False)
        row.addWidget(self.bom_roles_btn)
        left.addLayout(row)
        lay.addLayout(left, 16)
        right = QVBoxLayout()
        bar = QGridLayout()                                          # Two rows of three, so that the right column stays narrow and the table gets the width
        self.preview = Preview(self.session, "parts")
        self.side = QComboBox()
        self.side.addItems(["Top side", "Bottom side"])
        self.side.currentIndexChanged.connect(lambda i: (setattr(self.preview, "side", "top" if i == 0 else "bottom"), self.preview.update()))
        bar.addWidget(self.side, 0, 0)
        for n, (key, label) in enumerate((("copper", "Copper"), ("paste", "Paste openings"), ("sources", "Heat sources"),
                                ("labels", "Labels"), ("holes", "Holes"))):
            c = QCheckBox(label)
            c.setChecked(True)
            c.toggled.connect(lambda on, k=key: (self.preview.show_layers.__setitem__(k, on), self.preview.update()))
            bar.addWidget(c, (n + 1) // 3, (n + 1) % 3)
        bar.setColumnStretch(3, 1)
        right.addLayout(bar)
        right.addWidget(self.preview, 1)
        cap = QLabel("White squares are matched paste openings, <b>red ones match no part</b>. Click an opening to select its part; click a red one to create a heat source from it; "
                     "Ctrl+click a red one to add it to the selected part. Dashed: heat sources; solid accent: the selected part.")
        cap.setWordWrap(True)
        th.hint(cap)
        right.addWidget(cap)
        self.warn = QLabel("")
        self.warn.setWordWrap(True)
        self.warn.setToolTip("What the matching found about the files: a placement file that does not fit, parts matched by position (the paste file gives no designators), differences between the X3 layer and the placement file.")
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
            vals = {1: p.designator, 2: (p.footprint or p.from_file.get("package", "")), 3: sx.source_label(p), 4: str(nop or p.from_file.get("n_openings", 0)), 5: size,
                    6: f"{pos[0]:.0f}, {pos[1]:.0f}" if pos else "-"}
            if p.from_file.get("heat_source") is False:
                vals[3] += f" ({p.from_file.get('mount', 'not SMD')})"
            note = sx.shape_note(p)
            if p.shape == "exposed" and not orphan:
                vals[3] += "; " + note
            for col, text in vals.items():
                item = QTableWidgetItem(text)
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                if not has or orphan:
                    item.setForeground(QColor(c["muted"]))
                if col == 6 and pos:                                 # The column shows whole millimetres to stay narrow; the tooltip has the exact position
                    item.setToolTip(f"Centre of the part: x {pos[0]:.2f} mm, y {pos[1]:.2f} mm (Gerber frame)")
                if col in (2, 3):                                    # These two columns share the spare width and may be cut: the full text is in the tooltip
                    item.setToolTip(_plain_tip(sx.source_explanation(p) + (" " + self._shape_tip(p, note) if note else "") if col == 3 else text))      # the package name comes from the files
                t.setItem(k, col, item)
            sp = _spin(0, 1000, p.power, 3, "W", "Power the part dissipates, in W. Worst case: all of it enters the board. From the datasheet or the Power Calculator.")
            sp.setSuffix("")                                         # The unit is in the header, so the column can be narrow
            sp.setFixedWidth(sp.minimumSizeHint().width())          # As narrow as the widest value (1000.000) in the font of the platform: a fixed 76 px cut it with the 13 px macOS font
            sp.setEnabled(has and not orphan)
            sp.valueChanged.connect(lambda v, d=p.designator: self._set(d, power=v))
            t.setCellWidget(k, 7, sp)
            tj = _spin(0, 300, float(p.edits.get("tj_max", 0.0)), 0, "°C", "Highest junction temperature of the datasheet (0: none). The result reports the margin.")
            tj.setSuffix("")
            tj.setFixedWidth(tj.minimumSizeHint().width())
            tj.valueChanged.connect(lambda v, d=p.designator: self._set(d, tj_max=v))
            t.setCellWidget(k, 8, tj)
            cb = QComboBox()
            cb.addItems(["Component", "Source"])
            cb.setFixedWidth(int(cb.fontMetrics().horizontalAdvance("Component")) + 36)    # The text and the arrow, in the font of the platform; the combo's own size hint is 40 px wider
            cb.setCurrentText(p.edits.get("role", "Component"))
            cb.setToolTip("Component: a package with a junction (theta, Tj limit, optional heatsink on top). Source: only a heated area on the board.")
            cb.currentTextChanged.connect(lambda v, d=p.designator: self._set(d, role=v))
            t.setCellWidget(k, 9, cb)
            bom_text = sx.bom_proposal_text(p)
            bi = QTableWidgetItem(bom_text)
            bi.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            bi.setToolTip(self._bom_tip(p, bom_text))
            if bom_text in ("not fitted", "not in BOM"):
                bi.setForeground(QColor(c["alert"]))
            elif not has or orphan:
                bi.setForeground(QColor(c["muted"]))
            t.setItem(k, self.BOM_COL, bi)
        # Fit the table to the window: the package and the source take the spare width, the numeric columns are as narrow as their content, and the horizontal scroll bar
        # appears only when even that does not fit (a window narrower than about 900 pixels)
        hh = t.horizontalHeader()
        hh.setMinimumSectionSize(44)
        hh.setStretchLastSection(False)
        for col in range(len(self.COLS)):
            hh.setSectionResizeMode(col, QHeaderView.Stretch if col in (2, 3) else QHeaderView.ResizeToContents)
        t.setTextElideMode(Qt.ElideRight)
        has_bom = sx.bom_set() is not None
        t.setColumnHidden(self.BOM_COL, not has_bom)                 # without a BOM the table is the one it always was
        self.bom_roles_btn.setVisible(has_bom)
        self._building = False
        counts = sx.parts_info().get("counts", {})
        n_open = len(sx.openings())
        self.info.setText(f"<b>{len(parts)} parts</b> ({', '.join(f'{v} {k}' for k, v in counts.items() if v) or 'none found'}); {n_open} paste openings, "
                          + (f"<span style='color:{c['bad']}'>{len(sx.unmatched())} match no part (red in the preview).</span>" if sx.unmatched() else "0 match no part."))
        match = sx.bom_match()
        if match is not None:
            self.info.setText(self.info.text() + "<br>" + html.escape(
                f"BOM: {match['in_bom']} of these parts are in it, {len(match['not_in_bom'])} are not, {len(match['bom_only'])} of its designators have no part here, "
                f"{len(match['not_fitted'])} of these parts are marked not fitted (they stay as you set them)."))
        fr = sx.frame_proposal()
        self.frame_box.setVisible(bool(fr))
        if fr:
            self.frame_text.setText(f"<span style='color:{c['alert']}'>" + html.escape(
                (f"The positions of the placement file differ from the Gerber files by {fr['dx']:+.2f}, {fr['dy']:+.2f} mm: with this offset {fr['best'] * 100:.0f} % of the SMD parts sit on their openings "
                 f"instead of {fr['given'] * 100:.0f} %." if fr.get("propose") else
                 "The placement file and the Gerber files do not fit (another origin beyond 10 mm, a rotation, a mirror or a unit): the parts matched by position are not reliable.")) + "</span>")
            self.accept_btn.setVisible(bool(fr.get("propose")))
            self.accept_btn.setEnabled(sx.offset_answer != "accepted")
        self.warn.setText("<br>".join(f"<span style='color:{c['alert']}'>{html.escape(w)}</span>" for w in sx.parts_warnings()))
        if self.selected is not None and sx.part(self.selected) is None:
            self.selected = None
        self._sync_selection()
        self.preview.selected_part = self.selected
        self.preview.update()

    def _bom_tip(self, p, text):
        """!
        @brief The tooltip of a cell of the BOM column.
        @param p ImportPart.
        @param text Text of the cell.
        @return str
        """
        b = p.from_file.get("bom") or {}
        if text == "not fitted":
            return "The BOM marks this part as not fitted (DNP, DNI, NF, NM, DNF or a Fitted column with No). Nothing is unticked or changed: tick it only if you want to simulate it anyway."
        if text == "not in BOM":
            return "The placement file has this part but the BOM does not name it."
        extra = ", ".join(f"{k} {b[k]}" for k in ("mpn", "lcsc", "qty") if b.get(k))
        if text == "unknown":
            return "The names (designator, footprint, value) do not decide the role, or a word in them can mean two things (SMA): choose the Role yourself." + (f" BOM: {extra}." if extra else "")
        if text:
            return ("A guess from the designator, the footprint and the value, in English and KiCad-style names; it is only a suggestion and is not applied until you press Use the BOM roles."
                    + (f" BOM: {extra}." if extra else ""))
        return ""

    def _use_bom_roles(self):
        """!
        @brief Apply the roles the BOM suggests to the parts whose Role the user has not set.
        @return None
        """
        n = self.session.use_bom_roles()
        self.refresh()
        self.win.status.setText(f"Role set from the BOM guess for {n} part(s)." if n else "No part to set: the roles are already yours, or the BOM suggests no Component or Source.")

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
            pad = sx.default_shape(p) == "exposed"
            self.suggest.setText(f"{p.designator}: {sx.shape_note(p)}." + (" Pad or tab found; its outline is dashed." if pad else ""))

    def _shape_tip(self, p, note):
        """!
        @brief The sentence of the Source tooltip about the heat-source shape of a part.
        @param p ImportPart.
        @param note Text of `ImportSession.shape_note`.
        @return str
        """
        if p.shape == "exposed":
            return (f"Heat source: {note}. The paste of this part has an exposed pad or a tab (openings of at least half the area of the largest, holding a quarter of the paste, "
                    "spanning at most three quarters of the part and lying together as one pad), which carries almost all the heat; the whole power goes there (worst case: the leads carry a few "
                    "per cent). Choose another shape below to spread it over the pads.")
        return f"Heat source: {note}."

    def _shape(self, kind):
        """!
        @brief The user chose a shape.
        @param kind "hull", "box" or "exposed".
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
        if des is None:                                              # Not on an opening: a click inside the outline of a part also selects it
            hit = self.preview.part_at(x, y)
            des = hit[1] if hit and hit[0] == "part" else None
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
        self.note = QLabel("")
        self.note.setWordWrap(True)
        self.note.setTextFormat(Qt.PlainText)
        th.hint(self.note)
        f.addRow(self.note)
        self.mem.setToolTip("Memory verdict of the memory guard before anything is drawn: the unknowns of the model grid and the masks of the import, against the limit of Preferences.")
        f.addRow(self.mem)
        left.addWidget(g)
        g = QGroupBox("Layers and vias")
        f = QFormLayout(g)
        self.layers_label = QLabel("")
        self.layers_label.setWordWrap(True)
        self.layers_label.setTextFormat(Qt.PlainText)
        self.layers_label.setToolTip("The copper layers come from the functions of the files (step 1: the file list is the only place to change them).")
        f.addRow("Copper layers", self.layers_label)
        self.via_max = _spin(0.1, 5, self.session.via_max_mm, 2, "mm", "Largest diameter of a plated hole that is a via. Larger plated holes are component holes: a lead is not modelled.")
        self.via_max.valueChanged.connect(self._via)
        f.addRow("Vias up to", self.via_max)
        self.vias = QLabel("")
        self.vias.setTextFormat(Qt.PlainText)
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
        self.note.setText(self.session.auto_note)                           # the memory limit made Auto leave the 1 mm cap of imported copper

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
                       f"Of the {len(self.sources)} functions in the new set, {ident} are byte-identical to the stored files."
                       # Review: the commonest case (the same folder chosen again) gave no hint that the files bring nothing new, so the user expected a change
                       + (" <b>Every file is the same as the stored one:</b> the copper, holes and parts will not change; only what you changed in step 2 is applied."
                          if self.sources and ident == len(self.sources) else "") + " What do you want to do?")
        intro.setWordWrap(True)
        lay.addWidget(intro)
        self.intro = intro
        self.warn = QLabel("")
        self.warn.setWordWrap(True)
        if not same:
            self.warn.setText(f'<span style="color:{c["bad"]}"><b>This looks like a different board:</b> ' + "; ".join(html.escape(r) for r in reasons) +
                              ". Replacing it makes orphans of the parts that are not in the new files (kept with their power, not heating). Consider a new project instead.</span>")
        lay.addWidget(self.warn)
        self.radios = {}
        grp = QButtonGroup(self)
        texts = {"replace": ("Replace the previous import", "Copper, drills and outline are replaced. Parts with the same designator keep their power, Tj max, role and shape edits, and the values you "
                             "changed in the editor; a power, tick, Tj max or role you changed in step 2 of this window wins. Heaters, zones, heatsinks and vias you drew stay, and so does the stack-up when the layer count is the same. "
                             "Parts that disappeared stay as orphans (not heating) unless you tick them to remove."),
                 "update": ("Update after a layout revision", "Like replace, plus a table of what changed: moved, new, removed, resized and rotated parts. Nothing is lost silently."),
                 "add": ("Add files to the existing import", "A placement file, an extra paste layer or a component layer: their new parts are added and the stored parts keep everything. "
                         "The stored copper, outline and vias are not touched, so a copper, outline or drill file is not taken here: use Replace or Update for it. "
                         "Files that claim a function the import already has are shown to choose.")}
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
        foot = QLabel("The result is one undo step. What you changed in the editor after the import (powers and other part fields, heaters, zones, heatsinks and vias you drew, via fills, "
                      "the stack-up when the layer count is the same) is kept, and the status bar says what. Results of earlier runs stay in the project and are marked outdated; "
                      "run again after the import.")
        foot.setWordWrap(True)
        th.hint(foot)
        lay.addWidget(foot)
        bb = QDialogButtonBox(QDialogButtonBox.Cancel)
        self.go = bb.addButton("Continue", QDialogButtonBox.AcceptRole)
        self.go.setObjectName("primary")
        self.go.setToolTip("Apply the chosen command to the project as one undo step.")
        self.different = not same
        if self.different:
            # A different board: Enter must not replace the import; Cancel is the default and Continue is one click away
            self.go.setDefault(False)
            self.go.setAutoDefault(False)
            cancel = bb.button(QDialogButtonBox.Cancel)
            cancel.setAutoDefault(True)
            cancel.setDefault(True)
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
        if not hasattr(self, "go") or not any(r.isChecked() for r in self.radios.values()):
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
                if s["function"] in GEOMETRY and s["status"] in ("added", "changed"):
                    t.setItem(k, 3, QTableWidgetItem("not taken: use Replace or Update"))    # the stored masks, outline and vias stay as they are
                elif s["status"] == "added":
                    t.setItem(k, 3, QTableWidgetItem("added"))
                elif s["status"] == "identical":
                    t.setItem(k, 3, QTableWidgetItem("identical, nothing to do"))
                else:
                    cb = QComboBox()
                    cb.addItems(["Keep the stored file", "Use the new file"])
                    cb.setCurrentIndex(1)                       # the user added these files to change the import: the new one is the default (the stored file is one click away)
                    cb.setToolTip("Two files claim this function and they differ. The new file is the default; choose the stored one to leave it as it is.")
                    t.setCellWidget(k, 3, cb)
                    self.combos[self.session.choice_key(s)] = cb
            geo = sum(1 for s in rows if s["function"] in GEOMETRY and s["status"] in ("added", "changed"))
            n_added = sum(1 for s in rows if s["status"] == "added" and s["function"] not in GEOMETRY)
            self.note.setText(f"{n_added} function(s) added, {len(self.combos)} conflict(s) to choose. "
                              "The stored copper, outline, vias and existing parts are not touched."
                              + (f" {geo} copper, outline or drill file(s) are not taken: they change the board, use Replace or Update." if geo else "")
                              + ("" if n_added + len(self.combos) else " Nothing to add: every file is identical to the stored one or changes the board itself; "
                                 "choose Replace or Update to apply it."))
            # A Continue that can only do nothing used to close the window and leave the project as it was: the user took that for a failure
            self.go.setEnabled(n_added + len(self.combos) > 0)
        else:
            self.go.setEnabled(True)
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
                QToolTip.showText(ev.globalPos(), "<p>" + html.escape(self.states()[i][1]) + "</p>", self)   # file names in the text are escaped
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
        if existing is not None and getattr(existing, "cad_profile", None):
            self.session.reuse_profile = existing.cad_profile.get("key")      # a re-import keeps the stored CAD profile
        self.step = 0
        self.problem = None                                   # The Problem built by Import (None until the import ran)
        self.record = None                                    # The ImportRecord to store in the project
        self.mode = "new"                                     # "new", or the re-import command "replace", "update" or "add"
        self.changes = []                                     # Text lines of what a re-import changed
        self.typed = set()                                    # Designators whose step-2 values (power, tick, Tj max, role) the user changed in a re-import
        self.ask_reimport = lambda dlg: dlg.exec() == QDialog.Accepted
        # The questions are attributes so that a test (or a script) can answer them without a modal box
        self.confirm = lambda title, text: _plain_box(self, QMessageBox.Question, title, text, QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes
        self.notify = lambda title, text: _plain_box(self, QMessageBox.Information, title, text, QMessageBox.Ok)
        self.setWindowTitle("Import Gerber board")
        self.resize(1280, 820)
        lay = QVBoxLayout(self)
        self.stepper = Stepper(self.step_states)
        self.stepper.step_clicked.connect(self.go)
        lay.addWidget(self.stepper)
        self.subtitle = QLabel("")
        th.hint(self.subtitle)
        lay.addWidget(self.subtitle)
        self.page1 = Step1Page(self)
        self.page2, self.page3 = Step2Page(self), Step3Page(self)
        self.pages = [self.page1, self.page2, self.page3]
        self.stack = QStackedWidget()
        for p in self.pages:
            # Each page scrolls inside the window: the two columns need about 970 x 610 pixels, more than an 800 x 600 screen (review)
            sc = QScrollArea()
            sc.setWidgetResizable(True)
            sc.setFrameShape(QFrame.NoFrame)
            sc.setWidget(p)
            self.stack.addWidget(sc)
        lay.addWidget(self.stack, 1)
        row = QHBoxLayout()
        self.status = QLabel("")
        self.status.setTextFormat(Qt.PlainText)                             # it lists file names
        th.hint(self.status)
        row.addWidget(self.status, 1)
        self.help_btn, self.close_btn = QPushButton("Help"), QPushButton("Close")
        self.early_btn = QPushButton("Import now")
        self.back_btn, self.next_btn = QPushButton("Back"), QPushButton("Next")
        self.next_btn.setObjectName("primary")
        self.next_btn.setMinimumWidth(90)
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
        # A slow call of the session runs in a worker thread (_in_thread); while it runs nothing else may touch the session (review: the reload timer, a theme switch and a
        # close of the window reached it from the GUI thread during the run)
        self._busy = False
        self._close_asked = False
        self._recolour_asked = False
        # Features that must act before the session is released register here, before exec(): `fn(window, result)`, run once by done(), in order, without a veto
        self.before_close = []
        # Review: Enter in the path field also pressed the first auto-default button (Folder..., a file chooser), and Enter in a number field of step 3 would press Import.
        # No button of this window acts on Enter; the fields act on it themselves (the path field reads the path)
        for btn in self.findChildren(QPushButton):
            btn.setAutoDefault(False)
            btn.setDefault(False)
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
        self._busy = True                                     # a pending re-read (reload) waits for the end of this call
        # Review: the cyclic garbage collector runs in whichever thread allocates; in the worker it destroyed Qt objects of closed windows off the GUI thread (a segmentation
        # fault in the test battery). It is held until the call has ended, so that a collection happens on the GUI thread only (reference counting still frees the rest).
        # No explicit collect here: called from a slot of this window it could destroy the window itself when nothing but a cycle holds it
        gc_was_on = gc.isenabled()
        gc.disable()
        t.start()
        tick.start()
        try:
            if t.is_alive():
                loop.exec()
        finally:
            tick.stop()
            t.join()
            if gc_was_on:
                gc.enable()
            self._busy = False
            self.setEnabled(True)
        if self._close_asked:
            # The user closed the window during the call: the result is dropped and the window closes now that the session is no longer in use
            QTimer.singleShot(0, self.reject)
            raise _Cancelled()
        if self._recolour_asked:
            self._recolour_asked = False
            QTimer.singleShot(0, self._recolour)
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
        # The hooks for "new files" run here, in the GUI thread, before the worker starts (the worker has the garbage collector off and must not drop Qt objects)
        self.session.run_before_release("new_files")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            # Listing and hashing the files is off the GUI thread too (a folder of thousands of files, a large ZIP)
            self._in_thread(lambda: (self.session.set_files(source), self.session.load()))
        except _Cancelled:
            return
        except (OSError, ValueError, GerberError) as exc:
            self.notify("Cannot read the files", str(exc))
        finally:
            QApplication.restoreOverrideCursor()
        # Another board: the automatic cell and the project name of step 3 are taken again from it
        self._cell_set = False
        self._take_stored_settings()
        if self.existing is not None and self.session.files and self.session.take_stored_roles(getattr(self.existing, "settings", None)):
            self.reload()                                       # a file the user had given a function (or left out) keeps it
        if self.existing is not None and self.session.files:
            self.session.take_stored_parts(self.existing)       # step 2 shows the powers the project has: what Replace and Update keep, and what the user may change
        self.page3.newname.blockSignals(True)
        self.page3.newname.setText("")
        self.page3.newname.blockSignals(False)
        self.refresh()

    def _take_stored_settings(self):
        """!
        @brief A re-import starts from the model settings of the stored import (copper mapping, cell, largest via hole, a pixel the user typed, the offset accepted for the same
               placement file), not from the automatic ones.
        @details The new session has no powers yet, so its automatic cell differs from the one the user ended with; without this a re-import of the very same files silently
                 changed the cell and the pixel of the copper masks. The user can still change them in step 3.
        @return None
        """
        st = getattr(self.existing, "settings", None) or {}
        sx = self.session
        if st.get("mapping") in ("faces", "lambda", "fill"):
            sx.mapping = st["mapping"]
        for key, attr in (("via_max_mm", "via_max_mm"), ("cell_mm", "cell_mm")):
            v = st.get(key)
            if isinstance(v, (int, float)) and v > 0:
                setattr(sx, attr, float(v))
        if isinstance(st.get("cell_mm"), (int, float)) and st["cell_mm"] > 0:
            self._cell_set = True                              # step 3 keeps the stored cell instead of proposing a new one
        # Review: the pixel the user typed and the offset the user accepted for the placement file were dropped too (the masks or the parts changed with the very same files)
        if st.get("pixel_user") and isinstance(st.get("pixel_mm"), (int, float)) and st["pixel_mm"] > 0:
            sx.pixel_mm = float(st["pixel_mm"])
        off = st.get("offset_mm")
        if isinstance(off, (list, tuple)) and len(off) == 2 and any(abs(float(v)) > 0 for v in off):
            stored = sorted(f.sha256 for f in getattr(self.existing, "files", []) if f.function == PLACEMENT)
            now = sorted(f.sha256 for f in sx.used() if f.role == PLACEMENT)
            if stored and stored == now:                      # only for the same placement file: a new one is checked again by the frame check of step 2
                sx.offset, sx.offset_answer, sx._parts_dirty = (float(off[0]), float(off[1])), "accepted", True

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
        if self._busy:
            self.reload_later()                               # a slow call is running: read again after it
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self._in_thread(self.session.load)
        except _Cancelled:
            return
        finally:
            QApplication.restoreOverrideCursor()
        self.refresh()

    def refresh(self):
        """!
        @brief Update the pages and the buttons from the session.
        @return None
        """
        self.page1.refresh()
        if self.step:
            self.pages[self.step].preview.update()            # a re-read that ended while another step is shown
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
                if not getattr(self, "_cell_set", False):
                    self.session.cell_mm, self._cell_set = self.session.auto_cell(), True
                self.page3.refresh()
        finally:
            QApplication.restoreOverrideCursor()
        return True

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
            elif i == 1 and not self._busy and sx.heat_sources():           # while a call runs the stepper is repainted: asking for the parts would build them in the GUI thread beside the worker
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
        if 0 <= i < len(STEP_TITLES) and self.reachable(i) and not self._busy:
            try:
                self._refresh_page(i)
            except _Cancelled:
                return
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
        except _Cancelled:
            return False
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
            self.mode, self.changes, self.record, self.typed = dlg.mode, res["changes"], res["record"], set(res.get("typed", ()))
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
            if self._busy:
                self._recolour_asked = True                   # the pages read the session: refreshed when the running call has ended
            else:
                self._recolour()
        super().changeEvent(ev)

    def _recolour(self):
        """!
        @brief Refill the pages whose labels carry theme colours.
        @return None
        """
        self.page1.refresh()
        if self.step == 1:
            self.page2.refresh()
        elif self.step == 2:
            self.page3.refresh()

    def reject(self):
        """!
        @brief Close, Escape or the close box of the window: while a slow call runs the window closes when it has ended (the call cannot be stopped half-way).
        @return None
        """
        if self._busy:
            self._close_asked = True
            self.status.setText("Closing when the reading in progress has ended...")
            return
        super().reject()

    def done(self, result):
        """!
        @brief Run the `before_close` hooks, release the archive and the caches when the window closes (never while a call of the session is running).
        @param result Dialog result code.
        @return None
        """
        if self._busy:
            self._close_asked = True
            return
        self._reload_timer.stop()                             # a closed window reads nothing again
        self.run_before_close(result)
        self.session.close()
        super().done(result)

    def run_before_close(self, result):
        """!
        @brief Run the `before_close` hooks once, in registration order, while the session still holds its files; there is no veto.
        @details An exception of a hook is logged and does not stop the next hook or the close. The unsaved-changes question lives in `MainWindow.closeEvent`, not here.
        @param result Dialog result code (QDialog.Accepted or Rejected).
        @return None
        """
        hooks, self.before_close = self.before_close, []
        for fn in hooks:
            try:
                fn(self, result)
            except Exception:
                log.exception("before_close hook %s failed", getattr(fn, "__name__", fn))


__all__ = ["ImportBoardWindow", "Preview", "ReimportDialog", "Stepper"]
