#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file warning_box.py
@brief The warnings as an accordion inside a 'Warnings (N)' box (design A2 and B2 of docs/mockups-261): one closed row per warning with a solid badge (amber triangle for an alert, grey circle for a note), a clean plain-text title, its text and a button below when opened.
@details Used by the Simulation settings dock (the live input warnings, with a 'Select heater U1' button in the opened warning) and by the Results summary (the notes
         of the run, no button). The rows start closed; the rows that the user opened stay open when the list is refreshed (the live check runs after every edit).
"""

import math

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFontMetricsF, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ..checks import warning_severity, warning_title
from . import theme as th
from .boxes import CollapsibleBox

ICON_GAP = 6          # Logical px between the expand arrow and the badge, and between the badge and the title (at least 5)
_ICON_CACHE = {}      # (severity, logical size, device pixel ratio, colour) -> QPixmap of the badge, drawn once


def badge_pixmap(severe, size, dpr, colour):
    """!
    @brief The solid badge of a warning: an amber triangle with '!' for an alert, a solid circle with 'i' for a note.
    @details Drawn with QPainter in the colour of a theme token (the caller passes it), the mark cut out of the solid shape so that no background colour is
             needed, at `size * dpr` physical pixels with the device pixel ratio set, and cached per (kind, size, ratio, colour).
    @param severe True for the alert triangle, False for the note circle.
    @param size Logical edge of the badge in px.
    @param dpr Device pixel ratio of the screen.
    @param colour Fill colour as '#rrggbb' (the `alert` token for an alert, the `muted` token for a note).
    @return QPixmap.
    """
    key = (bool(severe), size, round(dpr, 3), colour)
    pm = _ICON_CACHE.get(key)
    if pm is not None:
        return pm
    pm = QPixmap(math.ceil(size * dpr), math.ceil(size * dpr))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    s, c = float(size), size / 2.0
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(colour))
    if severe:
        path = QPainterPath()
        path.moveTo(c, 0.8)
        path.lineTo(s - 0.4, s - 1.2)
        path.lineTo(0.4, s - 1.2)
        path.closeSubpath()
        pen = QPen(QColor(colour), 1.2)
        pen.setJoinStyle(Qt.RoundJoin)                    # Rounded corners keep the small triangle solid
        p.setPen(pen)
        p.drawPath(path)
        p.setPen(Qt.NoPen)
        p.setCompositionMode(QPainter.CompositionMode_Clear)     # The mark is a hole in the solid shape: any background shows through
        p.drawRoundedRect(QRectF(c - 0.75, s * 0.38, 1.5, s * 0.28), 0.5, 0.5)
        p.drawEllipse(QPointF(c, s * 0.77), 0.85, 0.85)
    else:
        p.drawEllipse(QRectF(0.6, 0.6, s - 1.2, s - 1.2))
        p.setCompositionMode(QPainter.CompositionMode_Clear)
        p.drawEllipse(QPointF(c, s * 0.30), 0.95, 0.95)
        p.drawRoundedRect(QRectF(c - 0.8, s * 0.44, 1.6, s * 0.30), 0.6, 0.6)
    p.end()
    _ICON_CACHE[key] = pm
    return pm


class _HeadGlyphs(QWidget):
    """!
    @brief The expand arrow and the severity badge of a warning row, drawn beside a plain-text title.
    @details Not part of the rich text: the vertical position comes from the font metrics of the title (the centre of the lowercase letters of its first line,
             the ascent minus half the x-height), so that it holds for any font and any device pixel ratio, and the badge stays on the first line when the
             title wraps.
    """

    def __init__(self, severe, parent=None):
        """!
        @param severe True for the alert badge, False for the note badge.
        @param parent Qt parent.
        """
        super().__init__(parent)
        self.severe = bool(severe)
        self.open = False
        self.setAttribute(Qt.WA_TransparentForMouseEvents)    # A click goes to the row head
        self._geometry()

    def _geometry(self):
        """!
        @brief Compute sizes and the vertical centre from the font and fix the widget size.
        """
        fm = QFontMetricsF(self.font())
        self.size_px = max(10, round(fm.height() * 0.9))
        self.arrow_w = math.ceil(self.size_px * 0.6)
        # The centre of the lowercase letters of the first line, from the top of the title label
        self.centre_y = fm.ascent() - fm.xHeight() / 2.0
        self._width = self.arrow_w + ICON_GAP + self.size_px
        self._height = math.ceil(max(fm.height(), self.centre_y + self.size_px / 2.0 + 1))
        self.setFixedSize(self._width, self._height)

    def icon_token(self):
        """!
        @brief The theme token that colours the badge.
        @return str "alert" or "muted".
        """
        return "alert" if self.severe else "muted"

    def indent(self):
        """!
        @brief Logical width that the text of the opened warning is indented by (it lines up under the badge).
        @return int.
        """
        return self.arrow_w + ICON_GAP

    def set_state(self, severe=None, is_open=None):
        """!
        @brief Change the severity or the open state and redraw.
        @param severe New severity (None: keep).
        @param is_open New open state (None: keep).
        """
        if severe is not None:
            self.severe = bool(severe)
        if is_open is not None:
            self.open = bool(is_open)
        self.update()

    def paintEvent(self, event):
        """!
        @brief Draw the arrow (a small triangle in the text colour) and the badge, centred on the lowercase letters of the first line.
        @param event QPaintEvent.
        """
        dpr = self.devicePixelRatioF()
        snap = lambda v: round(v * dpr) / dpr              # Keep edges on physical pixels  # noqa: E731
        c = th.colors(th.current_name())
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        yc = snap(self.centre_y)
        a, h = self.arrow_w * 0.8, self.arrow_w * 0.9
        x0 = (self.arrow_w - a) / 2.0
        path = QPainterPath()
        if self.open:                                       # Pointing down
            path.moveTo(x0, yc - a * 0.35)
            path.lineTo(x0 + a, yc - a * 0.35)
            path.lineTo(x0 + a / 2.0, yc + a * 0.45)
        else:                                               # Pointing right
            path.moveTo(x0 + a * 0.1, yc - h / 2.0)
            path.lineTo(x0 + a * 0.1, yc + h / 2.0)
            path.lineTo(x0 + a * 0.1 + a * 0.8, yc)
        path.closeSubpath()
        p.setPen(Qt.NoPen)
        p.setBrush(self.palette().windowText())
        p.drawPath(path)
        pm = badge_pixmap(self.severe, self.size_px, dpr, c[self.icon_token()])
        p.drawPixmap(QPointF(self.arrow_w + ICON_GAP, snap(yc - self.size_px / 2.0)), pm)
        p.end()

    def changeEvent(self, event):
        """!
        @brief Recompute the sizes when the font changes and redraw when the palette changes.
        @param event QEvent.
        """
        super().changeEvent(event)
        if event.type() == QEvent.FontChange:
            self._geometry()
        if event.type() in (QEvent.FontChange, QEvent.PaletteChange):
            self.update()


class _Head(QWidget):
    """!
    @brief The clickable head of a warning row: the glyphs, then the plain-text title; a click or Space/Enter toggles the row.
    """

    clicked = Signal()

    def mousePressEvent(self, event):
        """!
        @brief A click on the head toggles the row.
        @param event QMouseEvent.
        """
        self.clicked.emit()

    def keyPressEvent(self, event):
        """!
        @brief Space and Enter toggle the row.
        @param event QKeyEvent.
        """
        if event.key() in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter):
            self.clicked.emit()
        else:
            super().keyPressEvent(event)


class _TopicRow(QWidget):
    """!
    @brief One warning: a row with its badge and title (a click or Space opens it) and, when open, the full text and an optional button that selects its element.
    """

    toggled = Signal(bool)

    def __init__(self, warning, open_=False, select=True, parent=None):
        """!
        @param warning The warning (CheckWarning with kind and index, or a plain string).
        @param open_ True when the row starts open.
        @param select True to offer the button that selects the element of the warning.
        @param parent Qt parent.
        """
        super().__init__(parent)
        self.warning = warning
        self.title = warning_title(warning)
        self.severe = warning_severity(warning) == "alert"
        self._open = open_
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 2)
        lay.setSpacing(2)
        self.head = _Head()
        self.head.setCursor(Qt.PointingHandCursor)
        self.head.setFocusPolicy(Qt.StrongFocus)
        self.head.clicked.connect(lambda: self.set_open(not self._open))
        hl = QHBoxLayout(self.head)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(ICON_GAP)
        self.glyphs = _HeadGlyphs(self.severe)
        hl.addWidget(self.glyphs, 0, Qt.AlignTop)
        # Plain text (a title names elements of the project: never read as markup); it wraps in a narrow dock, so nothing makes the dock scroll sideways
        self.title_label = QLabel(self.title)
        self.title_label.setTextFormat(Qt.PlainText)
        self.title_label.setWordWrap(True)
        self.title_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.title_label.setMinimumWidth(1)                   # A wrapped label's minimum is its longest word: the dock never grows because of a long title
        self.title_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        hl.addWidget(self.title_label, 1, Qt.AlignTop)
        lay.addWidget(self.head)
        self.text = QLabel(str(warning))
        self.text.setWordWrap(True)
        self.text.setTextFormat(Qt.PlainText)             # The text names elements of the project: never read as markup
        self.text.setContentsMargins(self.glyphs.indent(), 0, 0, 0)
        lay.addWidget(self.text)
        self.button = None
        kind, index = getattr(warning, "kind", None), getattr(warning, "index", None)
        if select and kind is not None and index is not None:
            self.button = QPushButton(self._button_text(kind))
            self.button.setToolTip("Select the element this warning is about.")
            self.button.clicked.connect(lambda: self.selected.emit(kind, index))
            lay.addWidget(self.button, 0, Qt.AlignLeft)
        self._apply()

    selected = Signal(str, int)

    @staticmethod
    def _button_text(kind):
        """!
        @brief The label of the select button.
        @param kind Element kind of the warning ("heater", "zone", "heatsink", "via").
        @return str.
        """
        return f"Select {kind}"

    def set_label_name(self, name):
        """!
        @brief Put the name of the element in the select button ("Select heater U1").
        @param name Element name, or "" to keep the plain label.
        """
        if self.button is not None and name:
            self.button.setText(f"Select {getattr(self.warning, 'kind', '')} {name}")

    def is_open(self):
        """!
        @brief Whether the text is shown.
        @return bool.
        """
        return self._open

    def set_open(self, is_open):
        """!
        @brief Open or close the row.
        @param is_open True to open.
        """
        if bool(is_open) != self._open:
            self._open = bool(is_open)
            self._apply()
            self.toggled.emit(self._open)

    def set_stale(self, stale):
        """!
        @brief Disable the select button while the list is out of date (its element numbers may belong to another element now).
        @param stale True when the design was edited and the check has not run again.
        """
        if self.button is not None:
            self.button.setEnabled(not stale)

    def _apply(self):
        """!
        @brief Draw the row again: badge and arrow state, accessible texts, and show or hide the text and the button.
        """
        self.glyphs.set_state(self.severe, self._open)
        # The badge is only a picture: the severity is also in the accessible name and in the tooltip, so that a colour or a shape is never the only carrier
        word = "Warning" if self.severe else "Note"
        self.head.setAccessibleName(f"{word}: {self.title}")
        self.head.setAccessibleDescription("open" if self._open else "closed")
        self.glyphs.setAccessibleName(word)
        self.head.setToolTip(f"{word}. Click to read it." if not self._open else f"{word}. Click to close it.")
        self.text.setVisible(self._open)
        if self.button is not None:
            self.button.setVisible(self._open)

    def changeEvent(self, event):
        """!
        @brief Redraw in the new colours when the palette changes.
        @param event QEvent.
        """
        super().changeEvent(event)
        if event.type() == QEvent.PaletteChange and hasattr(self, "text"):
            self._apply()


class WarningAccordion(QWidget):
    """!
    @brief The 'Warnings (N)' box: a list of closed rows with clean titles; hidden when there is no warning.
    """

    warning_clicked = Signal(str, int)

    def __init__(self, dock, select=True, parent=None):
        """!
        @param dock Key of the dock that holds the box (the state of the box is kept under it).
        @param select True for the live list of the Simulation dock (rows get the button that selects the element); False for the notes of a run.
        @param parent Qt parent.
        """
        super().__init__(parent)
        self.select = select
        self.warnings = []
        self.stale = False
        self.rows = []
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.box = CollapsibleBox("Warnings", dock, section="warnings")
        lay.addWidget(self.box)
        self.body = QVBoxLayout(self.box.body)
        self.body.setContentsMargins(4, 4, 0, 0)
        self.setVisible(False)

    def set_warnings(self, warnings, names=None):
        """!
        @brief Show a list of warnings, each as a closed row (a row the user had opened stays open when its title is the same).
        @param warnings List of warnings; those with attributes kind and index (checks.CheckWarning) get the select button when `select` is on.
        @param names Optional function (kind, index) -> element name, for the label 'Select heater U1'.
        """
        opened = {r.title for r in self.rows if r.is_open()}
        for r in self.rows:
            r.setParent(None)
            r.deleteLater()
        self.rows = []
        self.warnings = list(warnings)
        self.stale = False
        self.box.setTitle(f"Warnings ({len(self.warnings)})")
        for w in self.warnings:
            row = _TopicRow(w, warning_title(w) in opened, self.select)
            if names is not None and row.button is not None:
                row.set_label_name(names(row.warning.kind, row.warning.index))
            row.selected.connect(self._selected)
            self.body.addWidget(row)
            self.rows.append(row)
        self.setVisible(bool(self.warnings))

    def text(self):
        """!
        @brief The full text of every warning, for tests and for copying.
        @return str.
        """
        return "\n\n".join(str(w) for w in self.warnings)

    def _selected(self, kind, index):
        """!
        @brief Pass on a click on the select button of an opened warning.
        @param kind Element kind.
        @param index 0-based element index.
        """
        if not self.stale:
            self.warning_clicked.emit(kind, index)

    def set_stale(self):
        """!
        @brief Mark the list as out of date (the design was edited and not yet checked): the select buttons stop working.
        """
        if self.warnings and not self.stale:
            self.stale = True
            for r in self.rows:
                r.set_stale(True)

    def recolour(self):
        """!
        @brief Draw the rows again after a change of theme.
        """
        for r in self.rows:
            r._apply()
        self.box._apply()

    def set_max_height(self, height):
        """!
        @brief Kept for the callers of the old list: the box lives in the scrolled part of its dock and needs no height limit.
        @param height Ignored.
        """
