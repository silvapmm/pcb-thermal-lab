#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file warning_box.py
@brief The warnings as an accordion inside a 'Warnings (N)' box (design A2 and B2 of docs/mockups-261): one closed row with a clean title per warning, its text and a button below when opened.
@details Used by the Simulation settings dock (the live input warnings, with a 'Select heater U1' button in the opened warning) and by the Results summary (the notes
         of the run, no button). The rows start closed; the rows that the user opened stay open when the list is refreshed (the live check runs after every edit).
"""

import html

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from ..checks import warning_severity, warning_title
from . import theme as th
from .boxes import CollapsibleBox


class _TopicRow(QWidget):
    """!
    @brief One warning: a row with its title (a click or Space opens it) and, when open, the full text and an optional button that selects its element.
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
        self.severe = warning_severity(warning) == "high"
        self._open = open_
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 2)
        lay.setSpacing(2)
        self.head = QLabel()
        self.head.setWordWrap(True)                      # A narrow dock wraps the title: nothing makes the dock scroll sideways
        self.head.setTextFormat(Qt.RichText)
        self.head.setCursor(Qt.PointingHandCursor)
        self.head.setFocusPolicy(Qt.StrongFocus)
        self.head.setToolTip("Click to read the warning.")
        self.head.mousePressEvent = lambda e: self.set_open(not self._open)
        self.head.keyPressEvent = self._key
        lay.addWidget(self.head)
        self.text = QLabel(str(warning))
        self.text.setWordWrap(True)
        self.text.setTextFormat(Qt.PlainText)             # The text names elements of the project: never read as markup
        self.text.setContentsMargins(14, 0, 0, 0)
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

    def _key(self, event):
        """!
        @brief Space and Enter open or close the row.
        @param event Qt key event.
        """
        if event.key() in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter):
            self.set_open(not self._open)
        else:
            QLabel.keyPressEvent(self.head, event)

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
        @brief Draw the row: arrow, severity symbol and title in the theme colours, and show or hide the text and the button.
        """
        c = th.colors(th.current_name())
        symbol = f"<span style='color:{c['alert']}'>⚠</span>" if self.severe else f"<span style='color:{c['muted']}'>•</span>"
        self.head.setText(f"{'▾' if self._open else '▸'} {symbol} {html.escape(self.title)}")
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
