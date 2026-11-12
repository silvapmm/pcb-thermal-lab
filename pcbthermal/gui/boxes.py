#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file boxes.py
@brief Collapsible boxes whose title row is the button (design B2 of docs/mockups-261): the one style of Board settings, Simulation settings, Properties and the warnings.
@details The state of a box (open or collapsed) is kept by key, `<dock>/<section>`, in a store that the main window binds to its QSettings, so that the Properties
         form (rebuilt on every edit) and the next session find every box as it was left. Without a bound store (a panel built alone, a test) the state lives in memory.
"""

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import QPushButton, QVBoxLayout, QWidget

from . import theme as th

_memory = {}                       # State of the boxes when no QSettings is bound: key -> bool
_settings = None                   # The QSettings of the main window, or None


def set_store(settings):
    """!
    @brief Bind the store of the box states to a QSettings (None: back to memory).
    @param settings QSettings or None.
    """
    global _settings
    _settings = settings


def load_state(key, default=True):
    """!
    @brief Read the open state of a box.
    @param key State key, "<dock>/<section>".
    @param default Value when nothing is stored (True: open).
    @return bool True when the box is open.
    """
    if _settings is not None:
        v = _settings.value("boxes/" + key)
        if v is not None:
            return str(v).lower() in ("true", "1")
        return default
    return _memory.get(key, default)


def save_state(key, is_open):
    """!
    @brief Store the open state of a box.
    @param key State key, "<dock>/<section>".
    @param is_open True when the box is open.
    """
    if _settings is not None:
        _settings.setValue("boxes/" + key, bool(is_open))
    else:
        _memory[key] = bool(is_open)


class CollapsibleBox(QWidget):
    """!
    @brief A group of controls under a title row that is a button: click it (or press Space on it) to open or collapse the group.

    @details The row is bold, has a pointing hand and an accent underline when the box is open; a collapsed box shows a dashed line and an ellipsis after
             the title. The controls go in `body` (give it a layout). `title()` and `setTitle()` mimic QGroupBox.
    """

    toggled = Signal(bool)

    def __init__(self, title, dock="", section=None, tip="", default_open=True, parent=None):
        """!
        @param title Text of the title row.
        @param dock Key of the dock that holds the box ("board", "simulation", "properties", "summary").
        @param section Key of the section inside the dock (default: the title).
        @param tip Tooltip of the title row (short; empty: 'Open or collapse this box.').
        @param default_open State when nothing is stored.
        @param parent Qt parent.
        """
        super().__init__(parent)
        self._title = title
        self.key = f"{dock}/{section or title}"
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 2, 0, 4)
        lay.setSpacing(2)
        self.header = QPushButton()
        self.header.setFlat(True)
        self.header.setCursor(Qt.PointingHandCursor)
        self.header.setCheckable(True)
        self.header.setFocusPolicy(Qt.StrongFocus)
        self.header.setToolTip(tip or "Open or collapse this box.")
        lay.addWidget(self.header)
        self.body = QWidget()
        self.body.setObjectName("box_body")
        lay.addWidget(self.body)
        self._open = load_state(self.key, default_open)
        self.header.setChecked(self._open)
        self.header.toggled.connect(self.set_open)
        self._apply()

    def title(self):
        """!
        @brief The title text.
        @return str.
        """
        return self._title

    def setTitle(self, title):
        """!
        @brief Change the title text (for example the count of warnings).
        @param title New title.
        """
        self._title = title
        self._apply()

    def is_open(self):
        """!
        @brief Whether the body is shown.
        @return bool.
        """
        return self._open

    def set_open(self, is_open):
        """!
        @brief Open or collapse the box and remember it.
        @param is_open True to open.
        """
        is_open = bool(is_open)
        if is_open == self._open:
            return
        self._open = is_open
        if self.header.isChecked() != is_open:
            self.header.setChecked(is_open)
        save_state(self.key, is_open)
        self._apply()
        self.toggled.emit(is_open)

    def _apply(self):
        """!
        @brief Draw the title row and show or hide the body.
        """
        c = th.colors(th.current_name())
        self.body.setVisible(self._open)
        self.header.setText(self._title if self._open else f"{self._title}  …")
        # A screen reader reads the title and the state, not the ellipsis drawn after a collapsed title
        self.header.setAccessibleName(self._title)
        self.header.setAccessibleDescription("open" if self._open else "collapsed")
        # The look of the row: no frame, the accent underline when open, a dashed line when collapsed (colours from the theme tokens)
        line = f"2px solid {c['accent']}" if self._open else f"1px dashed {c['muted']}"
        self.header.setStyleSheet(
            f"QPushButton {{ text-align: left; font-weight: bold; color: {c['text']}; border: none; border-bottom: {line}; padding: 3px 2px; background: transparent; }}"
            f"QPushButton:hover {{ color: {c['accent_hover']}; }}"
            f"QPushButton:focus {{ color: {c['accent']}; }}")

    def changeEvent(self, event):
        """!
        @brief Redraw the title row when the palette changes (theme switch).
        @param event QEvent.
        """
        super().changeEvent(event)
        if event.type() == QEvent.PaletteChange and hasattr(self, "body"):
            self._apply()
