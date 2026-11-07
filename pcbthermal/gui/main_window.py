#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file main_window.py
@brief Main window: menus, tool bar, docks, board canvas, results and background simulation.
"""

import copy
import dataclasses
import json
import os
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QSettings, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QActionGroup, QIcon, QKeySequence
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QDialogButtonBox, QDockWidget,
                               QDoubleSpinBox, QFileDialog, QFormLayout, QFrame, QHBoxLayout, QLabel, QMainWindow,
                               QMenu, QMessageBox, QPushButton, QScrollArea, QSlider, QSpinBox, QStatusBar, QTabWidget, QToolBar,
                               QVBoxLayout, QWidget)

from .. import __version__
from .. import defaults
from .. import fvm, memory
from ..checks import check_input
from ..examples import example_board
from ..model import reference_problem
from . import theme as th
from .elided import clamp_to_screen
from .calculator import PowerCalculator
from .import_session import editor_part_values, reimport_summary, sync_add_heaters
from .import_window import ImportBoardWindow
from .help import AboutDialog, GuideWindow, open_guide_in_browser
from .preferences import PreferencesDialog
from .canvas import BoardView
from . import compute
from .compute import ProcessWorker
from . import package_actions
from .document import Document
from .panels import BoardPanel, ElementList, Inspector, SolverPanel, WarningList
from .profile_page import ProfilePage
from .stackup import StackupPage
from . import tips
from .results_view import ResultsView
import shiboken6
from .display import OPEN_TIP, DisplayButton, DisplayPopover, DisplayState
from . import layerchoice
from .layerchoice import LayerChoice

FILE_FILTER = "PCB Thermal projects and packages (*.pcbt.json *.json *.pcbtz);;All files (*)"


TAB_BOARD, TAB_STACKUP, TAB_PROFILE, TAB_RESULTS = 0, 1, 2, 3     # Order of the main tabs


class NewBoardDialog(QDialog):
    """!
    @brief Dialog asking for the size and layers of a new board.
    """

    def __init__(self, parent=None):
        """!
        @param parent Qt parent.
        """
        super().__init__(parent)
        self.setWindowTitle("New board")
        f = QFormLayout(self)
        self.w, self.h = QDoubleSpinBox(), QDoubleSpinBox()
        nb = defaults.load()["new_board"]
        for s, v in ((self.w, nb["width_mm"]), (self.h, nb["height_mm"])):
            s.setRange(5, 1000)
            s.setValue(v)
            s.setSuffix(" mm")
        self.layers = QSpinBox()
        self.layers.setRange(1, 12)
        self.layers.setValue(int(nb["layers"]))
        f.addRow("Width", self.w)
        f.addRow("Height", self.h)
        f.addRow("Copper layers", self.layers)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        f.addRow(bb)


BACKGROUND_IMPORTED_TIP = ("A background image is for tracing a board by hand; this project comes from Gerber files, "
                           "which already give the exact copper.")


class BackgroundDialog(QDialog):
    """!
    @brief Place a photo or layout image under the board (file, position and size; the opacity of the map over it is the Underlay opacity).
    """

    def __init__(self, cfg, board_mm, parent=None, imported=False):
        """!
        @param cfg Current background dict or None.
        @param board_mm Board size (width, height) in mm, used by "Fit to board".
        @param parent Qt parent.
        @param imported True when the project comes from Gerber files: no image can be chosen, only the one already stored can be removed.
        """
        super().__init__(parent)
        self.setWindowTitle("Background image")
        self.board_mm = board_mm
        cfg = cfg or {}
        self.path = cfg.get("path", "")
        # The opacity of an older project is not edited here any more (the Underlay controls own it); the stored value is kept as it was
        self._stored_opacity = cfg.get("opacity")
        f = QFormLayout(self)
        self.file_label = QLabel(os.path.basename(self.path) or "no image")
        choose = QPushButton("Choose image…")
        choose.setToolTip("Pick a PNG, JPEG or BMP image.")
        choose.clicked.connect(self._choose)
        self.remove_btn = QPushButton("Remove image")
        self.remove_btn.setToolTip("Remove the image from the project (the file stays).")
        self.remove_btn.clicked.connect(self._remove)
        row = QHBoxLayout()
        row.addWidget(self.file_label, 1)
        row.addWidget(choose)
        row.addWidget(self.remove_btn)
        if imported:
            # A Gerber project already has the exact copper: an image can only be removed
            choose.setEnabled(False)
            choose.setToolTip(BACKGROUND_IMPORTED_TIP)
        f.addRow(row)
        self.x, self.y, self.w, self.h = (QDoubleSpinBox() for _ in range(4))
        for s, k, d in ((self.x, "x_mm", 0.0), (self.y, "y_mm", 0.0), (self.w, "w_mm", board_mm[0]),
                        (self.h, "h_mm", board_mm[1])):
            s.setRange(-2000, 4000)
            s.setDecimals(2)
            s.setSuffix(" mm")
            s.setValue(cfg.get(k, d))
        fit = QPushButton("Fit to board")
        fit.clicked.connect(self._fit)
        for label, w in (("X", self.x), ("Y", self.y), ("Width", self.w), ("Height", self.h)):
            f.addRow(label, w)
        f.addRow(fit)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        f.addRow(bb)

    def _choose(self):
        """!
        @brief Pick an image file.
        """
        p, _ = QFileDialog.getOpenFileName(self, "Background image", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if p:
            self.path = p
            self.file_label.setText(os.path.basename(p))

    def _remove(self):
        """!
        @brief Forget the image (the dialog then stores no background when accepted).
        """
        self.path = ""
        self.file_label.setText("no image")

    def _fit(self):
        """!
        @brief Stretch the image over the whole board.
        """
        self.x.setValue(0)
        self.y.setValue(0)
        self.w.setValue(self.board_mm[0])
        self.h.setValue(self.board_mm[1])

    def config(self):
        """!
        @brief The chosen placement.
        @return Dict stored in the project view, or None if no image was chosen.
        """
        if not self.path:
            return None
        out = {"path": self.path, "x_mm": self.x.value(), "y_mm": self.y.value(), "w_mm": self.w.value(), "h_mm": self.h.value()}
        if self._stored_opacity is not None:
            out["opacity"] = self._stored_opacity           # An old project keeps its value (the initial opacity of the map over the image)
        return out


class _FooterLimiter(QObject):
    """!
    @brief Keeps the footer of a dock (Run button, progress, warnings) from taking a low dock: the warning list gets a quarter of the height.
    """

    def __init__(self, host, footer):
        """!
        @param host Widget that holds the scroll area and the footer.
        @param footer The footer widget; its WarningList children are limited.
        """
        super().__init__(host)
        self.footer = footer

    def eventFilter(self, obj, event):
        """!
        @brief On a resize of the dock content, set the maximum height of its warning lists.
        @param obj Watched widget.
        @param event Qt event.
        @return False always (the event continues).
        """
        if event.type() == QEvent.Resize:
            for w in self.footer.findChildren(WarningList):
                w.set_max_height(obj.height() // 4)
        return False


class MainWindow(QMainWindow):
    """!
    @brief The application window.
    """

    def __init__(self, doc=None, settings=None):
        """!
        @param doc Optional Document to edit (default: a new empty board).
        @param settings Optional QSettings (tests pass a temporary one so real preferences are untouched).
        """
        th.fix_number_locale()                                  # Decimal point everywhere, before any spin box exists
        super().__init__()
        self.settings = settings or QSettings("PMS Labs", "PCB Thermal Lab")
        self.theme_name = self.settings.value("theme", "dark")
        self.doc = doc or Document()
        self.sim, self.worker, self._stale, self._guide = None, None, False, None
        self._edits, self._run_edits = 0, None                 # Edit counter, and its value when the running simulation started

        self.canvas = BoardView(self.doc, self.theme_name)
        self.display = DisplayState(self)                  # How the maps are drawn: one choice for the Results maps, the Animation and the board
        self.results = ResultsView(self.theme_name, display=self.display)
        self._underlay_key = None                          # Path of the image whose stored opacity was already taken as the initial one
        self.tabs = QTabWidget()
        self.tabs.addTab(self.canvas, "Board")
        self.stackup_page = StackupPage(self.doc, self.theme_name)
        # The pages are in scroll areas: the minimum width of a tab widget is that of its widest page (about 810 px for the Stack-up,
        # Power profile and Results pages, more with the advanced stack-up table), and the main window took it from the side docks, which
        # opened about 200 px wide at 1280 x 800 and 105 px at 1100 x 700. A page narrower than its controls now scrolls instead
        self.tabs.addTab(self._scrolled(self.stackup_page), "Stack-up")
        self.profile_page = ProfilePage(self.doc, self.theme_name)
        self.tabs.addTab(self._scrolled(self.profile_page), "Power profile")
        self.tabs.addTab(self._scrolled(self.results), "Results")
        self.setCentralWidget(self.tabs)

        self.board_panel = BoardPanel(self.doc)
        self.stackup_page.add_parameters(self.board_panel.stack_box, self.board_panel.materials_box)
        self.elements = ElementList(self.doc)
        self.inspector = Inspector(self.doc)
        self.solver_panel = SolverPanel(self.doc)
        self._build_docks()
        self._build_actions()
        self._build_toolbar()
        self.setStatusBar(QStatusBar())
        self.coord_label = QLabel("")
        self.version_label = QLabel(f"v{__version__}")
        self.version_label.setToolTip("PCB Thermal Lab version")
        self.defaults_label = QLabel("")
        self.defaults_label.setToolTip("The program is using your own defaults and libraries (Preferences).")
        self.statusBar().addPermanentWidget(self.defaults_label)
        self.statusBar().addPermanentWidget(self.coord_label)
        self.statusBar().addPermanentWidget(self.version_label)
        self._show_defaults_state()
        QTimer.singleShot(0, lambda: self._show_defaults_state(startup=True))        # The message waits until the window has finished starting (other messages come first)

        self.canvas.selection_changed.connect(self._on_canvas_selection)
        self.canvas.cursor_moved.connect(lambda x, y: self.coord_label.setText(f"x {x:7.2f} mm   y {y:7.2f} mm"))
        self.canvas.message.connect(lambda m: self.statusBar().showMessage(m))
        self.doc.edit_refused.connect(lambda m: self.statusBar().showMessage(m, 8000))   # once: a second connection drew the message twice
        self.canvas.element_created.connect(self._on_created)
        self.canvas.card_clicked.connect(self._open_model_menu)
        self.elements.selection_requested.connect(self._on_list_selection)
        self.board_panel.draw_outline_requested.connect(lambda: self.tool_actions["outline"].setChecked(True))
        self.solver_panel.run_requested.connect(self.run_simulation)
        self.solver_panel.cancel_requested.connect(self.cancel_simulation)
        self.solver_panel.checks.warning_clicked.connect(self._select_from_warning)
        self.results.animation.compute_requested.connect(self.compute_animation)
        self.tabs.currentChanged.connect(self._suggest_animation)
        self._check_timer = QTimer(self)                      # Re-check the design shortly after the last edit
        self._check_timer.setSingleShot(True)
        self._check_timer.setInterval(350)
        self._check_timer.timeout.connect(self._update_checks)
        self.doc.changed.connect(self._on_doc_changed)
        self.doc.state_changed.connect(self._update_title)
        self._checks_key = None                               # (models, cell) the live checks were last scheduled for
        self.doc.state_changed.connect(self._on_options_changed)
        self.doc.state_changed.connect(lambda: self.canvas.__setattr__("solver_cell", self.doc.options.cell_mm))

        th.apply_theme(QApplication.instance(), self.theme_name)
        self._refresh_icons()
        self._refresh_layers()
        self._update_title()
        self.resize(1480, 900)
        geo = self.settings.value("geometry")
        if geo:
            self.restoreGeometry(geo)
        # A saved geometry from a larger screen (or a damaged settings file) must not give a window bigger than this screen
        clamp_to_screen(self)
        # The arrangement of the docks the user left is restored too, when the window is first shown (before that the dock sizes are not applied)
        self._saved_state = self.settings.value("window_state")
        self._docks_sized = False
        self.snap_combo.setToolTip("Grid distance the drawn and dragged elements snap to (off = free placement).")
        tips.apply(self)
        self.canvas.set_tool("select")

    # ------------------------------------------------------------------ construction
    @staticmethod
    def _scrolled(page):
        """!
        @brief Put a page of the central tabs in a scroll area, so that its width does not set the minimum width of the tabs.
        @param page The page widget.
        @return QScrollArea holding the page (resized with the view while the view is larger than the page's minimum).
        """
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.NoFrame)
        area.setWidget(page)
        return area

    def _dock(self, title, widget, area, scroll=True, footer=None, label=None):
        """!
        @brief Add a titled dock widget.
        @param title Dock key: the object name under which saved window layouts store the dock (never changes).
        @param widget Content widget.
        @param area Qt dock area.
        @param scroll True to put the widget in a scroll area (panels of fields); False for a list that scrolls by itself.
        @param footer Optional widget kept below the scroll area, always visible (the Run button of the Simulation panel).
        @param label Title shown in the title bar and the View menu (default: title).
        @return The QDockWidget.
        """
        d = QDockWidget(label or title, self)
        d.setObjectName(title)                                  # The object name stays the old title: saved window layouts are keyed by it
        if scroll:
            # The panels grew taller with their boxes: a scroll area keeps every field reachable when the dock is short (a clipped panel hid "Position and size")
            area_widget = QScrollArea()
            area_widget.setWidgetResizable(True)
            area_widget.setFrameShape(QFrame.NoFrame)
            # A dock narrower than its fields scrolls sideways instead of squeezing the rows on top of each other (they overlapped with the bar always off)
            area_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            area_widget.setWidget(widget)
            if footer is not None:
                host = QWidget()
                hl = QVBoxLayout(host)
                hl.setContentsMargins(0, 0, 0, 0)
                hl.setSpacing(0)
                hl.addWidget(area_widget, 1)
                hl.addWidget(footer)
                area_widget.setMinimumHeight(120)           # The settings keep a usable strip (they scroll); the footer never takes the whole dock
                host.installEventFilter(_FooterLimiter(host, footer))
                area_widget = host
            d.setWidget(area_widget)
        else:
            d.setWidget(widget)
        d.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.addDockWidget(area, d)
        return d

    def _build_docks(self):
        """!
        @brief Create the left and right docks.
        """
        self.dock_board = self._dock("Board", self.board_panel, Qt.LeftDockWidgetArea, label="Board settings")
        self.dock_elements = self._dock("Elements", self.elements, Qt.LeftDockWidgetArea, scroll=False)
        self.splitDockWidget(self.dock_board, self.dock_elements, Qt.Vertical)
        self.dock_sim = self._dock("Simulation", self.solver_panel, Qt.RightDockWidgetArea, footer=self.solver_panel.footer, label="Simulation settings")
        self.dock_inspector = self._dock("Properties", self.inspector, Qt.RightDockWidgetArea)
        self.splitDockWidget(self.dock_sim, self.dock_inspector, Qt.Vertical)
        # The widths are set in showEvent (_size_docks): before the window is shown resizeDocks has no effect and the docks started about 110 px wide

    STATE_VERSION = 2                       # Version of the saved dock arrangement (restoreState refuses another)
    DOCK_MIN_LEFT = 300                     # Narrowest usable width in pixels of the Board and Elements docks
    DOCK_MIN_RIGHT = 340                    # Narrowest usable width in pixels of the Simulation and Properties docks

    def _size_docks(self):
        """!
        @brief Give the side docks a readable width for the window size (first start, or no saved arrangement).

        @note Before this the docks opened about 110 px wide at the default window size, so every field of the Board,
              Simulation and Properties panels was cut off.
        """
        w = max(self.width(), 800)
        # The widest panels need about 300 (Board) and 340 px (Properties of a heatsink) plus a scroll bar
        left = int(min(max(0.21 * w, 305), 440))              # Board panel and element list
        right = int(min(max(0.24 * w, 355), 480))             # Simulation settings and Properties
        self.resizeDocks([self.dock_board, self.dock_sim], [left, right], Qt.Horizontal)
        h = max(self.height(), 600)
        self.resizeDocks([self.dock_board, self.dock_elements], [int(0.62 * h), int(0.38 * h)], Qt.Vertical)
        self.resizeDocks([self.dock_sim, self.dock_inspector], [int(0.45 * h), int(0.55 * h)], Qt.Vertical)

    def _first_layout(self):
        """!
        @brief Restore the saved dock arrangement, or give the docks their default widths when there is none (or it cannot be read).
        """
        try:
            # The version number invalidates the states saved before the minimum widths existed (they may hold collapsed docks)
            restored = bool(self._saved_state) and self.restoreState(self._saved_state, self.STATE_VERSION)
        except (TypeError, ValueError):                          # A hand-edited settings file can hold text where the state was
            restored = False
        if not restored:
            self._size_docks()
            self._schedule_dock_minimums()
            return
        # restoreState brings back where the docks are and which are shown, but not always their sizes: those are applied from the saved numbers
        sizes = self.settings.value("dock_sizes")
        try:
            bw, sw, bh, eh, sh, ih = (int(v) for v in sizes)
        except (TypeError, ValueError):
            self._size_docks()
            self._schedule_dock_minimums()
            return
        # Sizes saved from a collapsed or much larger window are stale: below the minimum, or wider than the window can hold
        if bw < self.DOCK_MIN_LEFT or sw < self.DOCK_MIN_RIGHT or bw + sw > 0.8 * self.width() or min(bh, eh, sh, ih) < 60:
            self._size_docks()
        else:
            self.resizeDocks([self.dock_board, self.dock_sim], [bw, sw], Qt.Horizontal)
            self.resizeDocks([self.dock_board, self.dock_elements], [bh, eh], Qt.Vertical)
            self.resizeDocks([self.dock_sim, self.dock_inspector], [sh, ih], Qt.Vertical)
        self._schedule_dock_minimums()

    def _schedule_dock_minimums(self):
        """!
        @brief Check the dock widths now and again shortly after, when the window system has settled the window size.

        @note The window manager may still change the frame after the first show (a window larger than the screen is cut to the
              visible area), which squeezes the docks after _first_layout has run.
        """
        self._ensure_dock_minimums()
        QTimer.singleShot(250, self._ensure_dock_minimums)

    def _ensure_dock_minimums(self):
        """!
        @brief Widen a docked panel that is narrower than its fields need (a floating or hidden dock is left alone).
        """
        for dock, side in ((self.dock_board, self.DOCK_MIN_LEFT), (self.dock_elements, self.DOCK_MIN_LEFT),
                           (self.dock_sim, self.DOCK_MIN_RIGHT), (self.dock_inspector, self.DOCK_MIN_RIGHT)):
            if dock.isVisible() and not dock.isFloating() and dock.width() < side:
                self.resizeDocks([dock], [side], Qt.Horizontal)

    def showEvent(self, e):
        """!
        @brief Lay out the docks the first time the window is shown (saved arrangement or default widths).
        @param e QShowEvent.
        """
        super().showEvent(e)
        if not self._docks_sized:
            self._docks_sized = True
            QTimer.singleShot(0, self._first_layout)         # After the first layout pass: during showEvent the dock layout ignores the sizes

    def _act(self, text, slot=None, shortcut=None, checkable=False, checked=False, tip=""):
        """!
        @brief Create an action.
        @param text Menu text.
        @param slot Callable connected to triggered/toggled.
        @param shortcut Key sequence string or QKeySequence.StandardKey.
        @param checkable True for toggle actions.
        @param checked Initial state.
        @param tip Tooltip and status tip.
        @return QAction.
        """
        a = QAction(text, self)
        if shortcut:
            a.setShortcut(QKeySequence(shortcut))
        a.setCheckable(checkable)
        a.setChecked(checked)
        if tip:
            a.setToolTip(tip)
            a.setStatusTip(tip)
        if slot:
            (a.toggled if checkable else a.triggered).connect(slot)
        return a

    def _build_actions(self):
        """!
        @brief Create all actions and menus.
        """
        self.a_new = self._act("New board…", self.new_board, QKeySequence.New)
        self.a_open = self._act("Open…", self.open_file, QKeySequence.Open)
        self.a_save = self._act("Save", self.save_file, QKeySequence.Save)
        self.a_saveas = self._act("Save as…", self.save_file_as, QKeySequence.SaveAs)
        self.a_export_pkg = self._act("Export package…", lambda: package_actions.export_package(self),
                                      tip="Save a copy of the project as one .pcbtz package")
        self.a_ex_ref = self._act("Reference board (100 × 100 mm, 2 layers)", lambda: self._load_problem(reference_problem(), "reference"))
        self.a_ex_4l = self._act("Example 4-layer board (vias, heatsink, 2 heaters)", lambda: self._load_problem(example_board(), "example-4layer"))
        self.a_export_all = self._act("Export results to a folder…", self.export_results)
        self.a_export_txt = self._act("Export report (TXT)…", self.export_report)
        self.a_export_json = self._act("Export summary (JSON)…", self.export_summary)
        self.a_quit = self._act("Quit", self.close, QKeySequence.Quit)
        if not self.a_quit.shortcuts():
            self.a_quit.setShortcut(QKeySequence("Ctrl+Q"))     # Some platform themes (offscreen, minimal Linux) bind no Quit key

        self.a_undo = self.doc.stack.createUndoAction(self, "Undo")
        self.a_undo.setShortcut(QKeySequence.Undo)
        self.a_redo = self.doc.stack.createRedoAction(self, "Redo")
        # Both usual redo keys on every platform (Windows lists Ctrl+Y first, macOS Ctrl+Shift+Z): one action, two keys, no other action has them
        self.a_redo.setShortcuts([QKeySequence("Ctrl+Shift+Z"), QKeySequence("Ctrl+Y")])
        self.a_delete = self._act("Delete", lambda: self.doc.delete(self.canvas.selected_elements()), "Del")
        # Backspace (the key labelled delete on a Mac keyboard) is the second key of the same action, so the menu shows it and the canvas needs no branch
        self.a_delete.setShortcuts([QKeySequence("Del"), QKeySequence("Backspace")])
        self.a_dup = self._act("Duplicate", lambda: self.canvas.set_selection(
            self.doc.duplicate(self.canvas.selected_elements())), "Ctrl+D")
        self.a_selall = self._act("Select all on layer", self._select_all, QKeySequence.SelectAll)

        self.a_fit = self._act("Fit board", self.canvas.fit, "Ctrl+0", tip="Zoom to show the whole board (Ctrl+0)")
        self.a_zin = self._act("Zoom in", lambda: self.canvas.zoom(1.25), QKeySequence.ZoomIn)
        self.a_zin.setShortcuts([QKeySequence("Ctrl++"), QKeySequence("Ctrl+=")])   # Ctrl+= is the same key without Shift on most keyboards
        self.a_zout = self._act("Zoom out", lambda: self.canvas.zoom(0.8), QKeySequence.ZoomOut)
        self.a_grid = self._act("Grid", self._toggle_grid, "G", True, True, "Show the drawing grid (G)")
        self.a_sgrid = self._act("Solver grid", self._toggle_solver_grid, "Shift+G", True, False,
                                 "Show the solver cells (Shift+G)")
        self.a_overlay = self._act("Temperature map on the board", self._toggle_overlay, "T", True, False,
                                   "Show the temperature map on the board (T)")
        self.a_overlay.setEnabled(False)                       # Until a result exists; _update_map_button keeps the state and the tooltip
        # The keyboard route to the Display popover (the toolbar button takes no focus): opened active, with the keyboard in its controls
        self.a_display = self._act("Display settings…", lambda: self._toggle_display_popover(activate=True), "D",
                                   tip="Open the Display panel (D)")
        # The keyboard route to the model menu of the card of the map (the card itself answers the mouse only)
        self.a_model = self._act("Model of the map…", self._key_model_menu, "M",
                                 tip="Choose the model shown by the map (M)")
        self.a_imported = self._act("Imported copper", self.canvas.set_show_imported_copper, None, True, True,
                                    "Draw the imported copper under the elements")
        self.a_labels = self._act("Element names", self.canvas.set_show_labels, None, True, True,
                                  "Write the element names on the board")
        self.a_bg = self._act("Background image…", self.set_background,
                              tip="Place an image under the board to trace it")
        self.a_theme = self._act("Light / dark theme", self.toggle_theme, "Ctrl+Shift+T")

        self.a_run = self._act("Run simulation", self.run_simulation, "F5", tip="Solve the selected models (F5)")
        self.a_calc = self._act("Power Calculator…", self.show_calculator,
                                tip="Find a part's power from a measured temperature")
        self.a_import = self._act("Import Gerber board…", self.show_import,
                                  tip="New project from Gerber, drill and placement files")
        self.a_cancel = self._act("Cancel calculation", self.cancel_simulation, "Ctrl+.", tip="Stop the running calculation (Ctrl+.)")

        self.a_prefs = self._act("Preferences…", self.show_preferences, "Ctrl+,",
                                 tip="Edit the libraries and the defaults")
        self.a_guide = self._act("User guide", self.show_guide, "F1", tip="Parameters, models and how to read the results")
        self.a_guide_web = self._act("User guide in the browser", open_guide_in_browser, tip="Open the user guide in the web browser")
        self.a_keys = self._act("Keyboard shortcuts", self.show_shortcuts)
        self.a_about = self._act("About PCB Thermal Lab", self.show_about)
        for n, key in enumerate(("Board", "Stack-up", "Power profile", "Results")):
            a = self._act(f"Show the {key} tab", lambda _=False, i=n: self.tabs.setCurrentIndex(i), f"Ctrl+{n + 1}")
            self.addAction(a)                                  # Active without a menu entry

        mb = self.menuBar()
        m = mb.addMenu("&File")
        for a in (self.a_new, self.a_open, self.a_import, None):
            m.addAction(a) if a else m.addSeparator()
        ex = m.addMenu("Open example")
        ex.addAction(self.a_ex_ref)
        ex.addAction(self.a_ex_4l)
        for a in (None, self.a_save, self.a_saveas, self.a_export_pkg, None, self.a_export_all, self.a_export_txt,
                  self.a_export_json, None, self.a_quit):
            m.addAction(a) if a else m.addSeparator()
        m = mb.addMenu("&Edit")
        for a in (self.a_undo, self.a_redo, None, self.a_dup, self.a_delete, self.a_selall, None, self.a_prefs):
            m.addAction(a) if a else m.addSeparator()
        m = mb.addMenu("&View")
        for a in (self.a_fit, self.a_zin, self.a_zout, None, self.a_grid, self.a_sgrid, self.a_overlay, self.a_display, self.a_model, self.a_imported, self.a_labels, None,
                  self.a_bg, self.a_theme):
            m.addAction(a) if a else m.addSeparator()
        for d in (self.dock_board, self.dock_elements, self.dock_sim, self.dock_inspector):
            m.addAction(d.toggleViewAction())
        m = mb.addMenu("&Simulation")
        m.addAction(self.a_run)
        m.addAction(self.a_cancel)
        m.addSeparator()
        m.addAction(self.a_calc)
        m = mb.addMenu("&Help")
        m.addAction(self.a_guide)
        m.addAction(self.a_guide_web)
        m.addAction(self.a_keys)
        m.addSeparator()
        m.addAction(self.a_about)
        self._hide_bare_key_hints()

    def _hide_bare_key_hints(self):
        """!
        @brief Keep the single-key shortcuts of the View menu (G, Shift+G, T, D, M) working but out of the menu text.

        On macOS the native menu prints a key without a modifier as a lone letter next to the entry ("Temperature on board  T"),
        which reads like a mnemonic or a wrong item. The keys stay on window-level actions that toggle the visible ones; the
        tool bar tooltips and the keyboard help still name them.
        """
        for a in (self.a_grid, self.a_sgrid, self.a_overlay, self.a_display, self.a_model):
            keys = a.shortcuts()
            a.setShortcuts([])
            hidden = QAction(a.text(), self)
            hidden.setShortcuts(keys)
            if a is self.a_overlay:
                hidden.triggered.connect(self._key_overlay)
                self._hidden_overlay_key = hidden
            elif a in (self.a_display, self.a_model):
                hidden.triggered.connect(a.trigger)          # Same route as the menu entry: the popover takes the keyboard
            else:
                hidden.triggered.connect(a.toggle)
            self.addAction(hidden)                              # Active in the whole window, in no menu

    def _build_toolbar(self):
        """!
        @brief Create the drawing tool bar.
        """
        tb = QToolBar("Tools")
        tb.setObjectName("tools")
        tb.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, tb)
        self.tool_group = QActionGroup(self)
        self.tool_group.setExclusive(True)
        self.tool_actions = {}
        for name, text, key in (("select", "Select", "S"), ("zone", "Copper zone", "Z"), ("heater", "Heater", "H"),
                                ("heatsink", "Heatsink (cooling)", "C"), ("via", "Via", "V"),
                                ("outline", "Board outline", "O")):
            a = self._act(text, lambda checked, n=name: checked and self._set_tool(n), key, True, name == "select",
                          f"{text} ({key})")
            self.tool_group.addAction(a)
            tb.addAction(a)
            self.tool_actions[name] = a
        tb.addSeparator()
        self.a_poly = self._act("Polygon mode", self._set_polygon_mode, "P", True, False,
                                "Draw by clicking vertices (double click or Enter to finish)")
        tb.addAction(self.a_poly)
        tb.addSeparator()
        tb.addWidget(QLabel(" Layer "))
        self.layer_choice = LayerChoice(self)                       # The one layer choice: the editor, every map and the map on the board
        self.doc.project_replaced.connect(self.layer_choice.reset)       # A new project starts on layer 1 (the layer is also the drawing layer)
        self.layer_context = "editor"
        self.layer_combo = QComboBox()
        # One width for every context: the longest entry ("Metal block (bottom)") fits, and the tool bar does not move when the list changes with the tab
        self.layer_combo.setMinimumWidth(self.layer_combo.fontMetrics().horizontalAdvance("Metal block (bottom)") + 36)     # + the arrow and the frame
        self.layer_combo.currentIndexChanged.connect(self._on_layer_changed)
        self.layer_combo.activated.connect(self._on_layer_changed)       # Also a pick of the entry already shown (the fallback layer): it then wins over a stored All
        tb.addWidget(self.layer_combo)
        # The map on the board (on and off) and how it is drawn (Display): Layer, Map, Display | Snap | Run
        tb.addAction(self.a_overlay)
        self.display_button = DisplayButton()
        self.display_button.setToolTip(OPEN_TIP)
        self.display_button.setObjectName("displayButton")
        self.display_button.clicked.connect(self._toggle_display_popover)
        tb.addWidget(self.display_button)
        self.display_popover = DisplayPopover(self.display, self)
        self.display_popover.addAction(self._hidden_overlay_key)    # The key T keeps working while the popover is the active window
        self.display.changed.connect(self._on_display_changed)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.results.tabs.currentChanged.connect(self._on_tab_changed)
        self._popover_filter_on = False                             # The application-level filter of the popover is installed only while it is open
        # When Qt deletes the popover (with its window) the filter goes with it, so no deferred route finds a dead object
        self.display_popover.destroyed.connect(self._on_popover_destroyed)
        tb.addSeparator()
        tb.addWidget(QLabel(" Snap "))
        self.snap_combo = QComboBox()
        for label, v in (("off", 0), ("0.1 mm", 0.1), ("0.5 mm", 0.5), ("1 mm", 1.0), ("2.5 mm", 2.5), ("5 mm", 5.0)):
            self.snap_combo.addItem(label, v)
        self.snap_combo.setCurrentIndex(3)
        self.snap_combo.currentIndexChanged.connect(lambda _i: self.canvas.set_snap(self.snap_combo.currentData()))
        tb.addWidget(self.snap_combo)
        for a in (self.a_fit, self.a_grid, self.a_sgrid):
            tb.addAction(a)
        # The map on the board follows the Temperature tab: its model and colour limits (the colour map is the shared display choice)
        t = self.results.temp
        t.model.currentIndexChanged.connect(self._overlay_follow_results)
        t.auto.toggled.connect(self._overlay_follow_results)
        for w in (t.vmin, t.vmax):
            w.valueChanged.connect(self._overlay_follow_results)
        tb.addSeparator()
        tb.addAction(self.a_run)
        self.toolbar = tb

    def _refresh_icons(self):
        """!
        @brief Paint the icons for the current theme.
        """
        for name, a in self.tool_actions.items():
            a.setIcon(th.tool_icon(name, self.theme_name))
        self.a_poly.setIcon(th.tool_icon("polygon", self.theme_name))
        self.a_fit.setIcon(th.tool_icon("fit", self.theme_name))
        self.a_grid.setIcon(th.tool_icon("grid", self.theme_name))
        self.a_sgrid.setIcon(th.tool_icon("solver_grid", self.theme_name))
        self.a_run.setIcon(th.tool_icon("run", self.theme_name))
        self.a_overlay.setIcon(th.tool_icon("map", self.theme_name))
        self.display_button.set_theme(self.theme_name)
        self.display_button.set_dot(self.display.active())
        self.display_popover.apply_theme(self.theme_name)
        self._refresh_display_context()
        logo = Path(__file__).resolve().parents[2] / "ico" / "pcb-board.png"
        if logo.exists():
            self.setWindowIcon(QIcon(str(logo)))

    # ------------------------------------------------------------------ canvas glue
    def _set_tool(self, name):
        """!
        @brief Activate a tool.
        @param name Tool name.
        """
        self.tabs.setCurrentIndex(0)
        self.canvas.set_tool(name)

    def _set_polygon_mode(self, on):
        """!
        @brief Switch between rectangle and polygon drawing.
        @param on True for polygon mode.
        """
        self.canvas.polygon_mode = on

    def _toggle_grid(self, on):
        """!
        @brief Show or hide the drawing grid.
        @param on True to show.
        """
        self.canvas.show_grid = on
        self.canvas.viewport().update()

    def _toggle_solver_grid(self, on):
        """!
        @brief Show or hide the FVM mesh.
        @param on True to show.
        """
        self.canvas.show_solver_grid = on
        self.canvas.solver_cell = self.doc.options.cell_mm
        self.canvas.viewport().update()

    def _update_map_button(self):
        """!
        @brief Set the state of the map button (and of its menu entry and key): greyed until a result exists and while it is outdated, with the reason in the tooltip.
        """
        a = self.a_overlay
        if self.sim is None:
            tip, ok = "Run a simulation first", False
        elif self._stale:
            tip, ok = "The result is outdated: run the simulation again", False
        else:
            tip, ok = "Show the temperature map on the board (T)", True
        a.setEnabled(ok)
        a.setToolTip(tip)
        a.setStatusTip(tip)
        self._map_button_tip = tip
        if not ok and a.isChecked():
            a.blockSignals(True)
            a.setChecked(False)
            a.blockSignals(False)
            self.canvas.clear_overlay()
            self._editor_apply_underlay(False)

    def _open_model_menu(self, pos, keyboard=False):
        """!
        @brief The model name of the card of the map was clicked (or the key M pressed): list the models of the current result and change the model of the Temperature tab.
        @details It is the same control as the Model box of Results - Temperature (no second list). A model that cannot be drawn on this board stays listed, greyed, with the
                 reason as its tooltip. The menu is a popup (Qt keeps it on the screen), so the keyboard focus returns to the board when it closes. One menu at a time:
                 the previous one is deleted, and an entry finds its model by key when it is chosen (the list may have been rebuilt by a new run meanwhile).
        @param pos QPoint in global coordinates where the menu opens.
        @param keyboard True when opened from the keyboard: the entry of the current model is made active, so the arrows and Enter work at once.
        """
        from .fieldscale import overlay_refusal

        t = self.results.temp
        if self.sim is None or not t.model.count():
            self.statusBar().showMessage("Run a simulation first: the list holds the models of the result.")
            return
        old = getattr(self, "_model_menu", None)
        if old is not None and shiboken6.isValid(old):
            old.close()
            old.deleteLater()                          # Deferred: an entry being triggered still finishes
        menu = QMenu(self)
        menu.setObjectName("modelMenu")
        menu.setToolTipsVisible(True)                  # The reason of a greyed model is its tooltip (a QMenu hides tooltips by default)
        current = None

        def choose(key):
            """!
            @brief Show a model in the Temperature tab (the map on the board follows it).
            @param key Model key.
            """
            if shiboken6.isValid(t.model):
                k = t.model.findData(key)
                if k >= 0:
                    t.model.setCurrentIndex(k)

        for i in range(t.model.count()):
            key = t.model.itemData(i)
            act = menu.addAction(t.model.itemText(i))
            act.setCheckable(True)
            act.setChecked(i == t.model.currentIndex())
            why = overlay_refusal(self.sim.results[key], self.doc.problem) if key in self.sim.results else None
            if why:
                act.setEnabled(False)
                act.setToolTip(why)
                act.setText(f"{t.model.itemText(i)} (not drawn on an outline board)")
            else:
                act.triggered.connect(lambda _=False, k=key: choose(k))      # The map on the board follows the Temperature tab
                if i == t.model.currentIndex():
                    current = act
        self._model_menu = menu
        menu.aboutToHide.connect(lambda: self.canvas.setFocus() if shiboken6.isValid(self.canvas) else None)
        menu.popup(pos)
        if keyboard and current is not None:
            menu.setActiveAction(current)

    def _key_model_menu(self):
        """!
        @brief The key M (View - Model of the map…): open the model list from the keyboard, under the card of the map on the board when it is shown.
        """
        hit = self.canvas.card_hit_rect() if self.tabs.currentIndex() == TAB_BOARD else None
        if hit is not None:
            pos = self.canvas.viewport().mapToGlobal(hit.bottomLeft().toPoint())
        else:
            pos = self.mapToGlobal(self.rect().center())
        self._open_model_menu(pos, keyboard=True)

    def _key_overlay(self):
        """!
        @brief The key T: toggle the map on the board, or say in the status bar why it cannot be shown.
        """
        if self.a_overlay.isEnabled():
            self.a_overlay.toggle()
        else:
            self.statusBar().showMessage(getattr(self, "_map_button_tip", "Run a simulation first"))

    def _toggle_overlay(self, on):
        """!
        @brief Paint or remove the temperature result on the board.
        @details The map is the one the Temperature tab shows (same model, colour limits and colour map, so both show the same numbers) on the layer chosen in the
                 toolbar, with the cells off the outline transparent, a colour bar and the card of the model with the hottest and coolest point. A model that cannot
                 be drawn on this board (the stretched map of the Lumped or Analytic on an outline board) leaves only the card with that note. It is not drawn while
                 the result is outdated.
        @param on True to paint.
        """
        from .fieldscale import MODEL_SHORT, extreme_points, inside_mask, overlay_refusal, results_limits

        self._editor_apply_underlay(bool(on))
        if not on or self.sim is None or self._stale:
            self.canvas.clear_overlay()
            if on:
                # Nothing to paint: say why and leave the button off
                self.statusBar().showMessage("Run a simulation first." if self.sim is None else
                                             "The result is outdated (the design changed): run the simulation again to paint it on the board.")
                self.a_overlay.blockSignals(True)
                self.a_overlay.setChecked(False)
                self.a_overlay.blockSignals(False)
                self._editor_apply_underlay(False)
            return
        cfg = self.results.temp.current_field()
        res = self.results.temp._result() or self.sim.reference     # The model shown in the Results tab
        short = MODEL_SHORT.get(res.model, str(res.model))
        note = overlay_refusal(res, self.doc.problem)
        if note:
            self.canvas.clear_overlay()
            self.canvas.set_overlay_card(f"{short}: not drawn on an outline board (stretched map)")
            self.statusBar().showMessage(note)
            return
        layer = min(self.canvas.layer, res.T.shape[0] - 1)
        field = res.T[layer]
        nodes = res.grid == "nodes"
        mask = inside_mask(self.doc.problem, field.shape, res.dx, res.dy)
        vmin, vmax = (cfg[4], cfg[5]) if cfg else (None, None)
        # The limits by the rule of the Results map (Auto range over the samples on the board only), passed explicitly so the canvas does not rescale
        vmin, vmax = results_limits(field, self.doc.problem, res.dx, res.dy, vmin is None or vmax is None, vmin, vmax)
        self.canvas.set_overlay(field, res.dx, res.dy, cmap=self.display.cmap, vmin=vmin, vmax=vmax,
                                opacity=self.display.value(), nodes=nodes, mask=mask, smooth=self.display.view == "smooth")
        ext = extreme_points(field, mask, res.dx, res.dy, nodes)
        if ext is not None:
            self.canvas.set_overlay_card(short, ext["tmax"], ext["pmax"], ext["tmin"], ext["pmin"])
        else:
            self.canvas.set_overlay_card(short)

    def _editor_apply_underlay(self, overlay_on):
        """!
        @brief Show the background image on the canvas: always, except while a map is on the board and the Underlay is not Image.
        @param overlay_on True while the temperature map is painted on the board.
        """
        image = self.display.kind == "image"
        self.canvas.set_background_visible(not overlay_on or image)
        self.canvas.set_background_full(overlay_on and image)       # Faded twice otherwise (its own opacity, then the map's)

    def _on_display_changed(self, what):
        """!
        @brief The display choice changed (Display popover, or a new project): update the dot of the button and the map on the board.
        @param what Name of what changed ("underlay", "opacity", "view", "contour", "cmap" or "source").
        """
        self.display_button.set_dot(self.display.active())
        on = self.a_overlay.isChecked()
        if what == "opacity" and on:
            self.canvas.set_overlay_opacity(self.display.value())
        elif what in ("cmap", "view") and on:
            self._toggle_overlay(True)
        self._editor_apply_underlay(on)

    def _display_context(self):
        """!
        @brief Where the Display popover is opened from: the board, one of the maps, or a page without a map.
        @return One of display.CONTEXTS.
        """
        if self.tabs.currentIndex() == TAB_BOARD:
            return "editor"
        if self.tabs.currentIndex() == TAB_RESULTS:
            w = self.results.tabs.currentWidget()
            if w is self.results.temp:
                return "temperature"
            if w is self.results.grad:
                return "gradient"
            if w is self.results.animation:
                return "animation"
        return "other"

    def _refresh_display_context(self, *_):
        """!
        @brief The tab changed: the popover (open or not) shows the controls that apply there.
        @param _ Ignored (the value carried by the Qt signal).
        """
        if self.display_popover is not None and shiboken6.isValid(self.display_popover):
            self.display_popover.set_context(self._display_context())

    def _on_tab_changed(self, *_):
        """!
        @brief A tab of the window or of the Results changed (mouse, Ctrl+1 to Ctrl+4, keyboard): close the Display panel, then show its controls for the new tab.
        @param _ Ignored (the index carried by the Qt signal).
        """
        self._close_display_popover()
        self._refresh_display_context()
        self._apply_layer()

    def _toggle_display_popover(self, activate=False):
        """!
        @brief Open the Display popover under its button, or close it.
        @param activate True when opened from the menu (View - Display settings): the popover takes the keyboard so that its controls can be reached without a mouse.
        """
        if self.display_popover is None or not shiboken6.isValid(self.display_popover):
            return
        if self.display_popover.isVisible():
            self._close_display_popover()
            return
        self.display_popover.set_context(self._display_context())
        # A click outside the popover closes it: the filter watches every event of the application, so it is installed only while the popover is open
        # (installed for good it cost about 1.3 us per event and window, and a closed window kept it)
        QApplication.instance().installEventFilter(self)
        self._popover_filter_on = True
        self.display_popover.show_under(self.display_button, activate=activate)

    def _on_popover_destroyed(self, *_):
        """!
        @brief The popover was deleted by Qt: forget it and remove the application filter that watched for clicks.
        @param _ Ignored (the QObject carried by the signal).
        """
        if getattr(self, "_popover_filter_on", False):
            app = QApplication.instance()
            if app is not None:
                app.removeEventFilter(self)
            self._popover_filter_on = False
        self.display_popover = None

    def _close_display_popover(self):
        """!
        @brief Close the Display popover, applying an opacity edit that still waits for its pause, and give the keyboard back to the window when the popover had it.
        """
        if getattr(self, "_popover_filter_on", False):
            # Removed first and whatever the state of the popover: a filter must never outlive the window that owns it
            app = QApplication.instance()
            if app is not None:
                app.removeEventFilter(self)                          # Nothing to watch while the popover is closed
            self._popover_filter_on = False
        pop = getattr(self, "display_popover", None)
        # Idempotent and safe after Qt deleted the popover (its window closed or was deleted before a deferred call ran)
        if pop is None or not shiboken6.isValid(pop) or not pop.isVisible():
            return
        had_keyboard = QApplication.activeWindow() is pop
        pop.flush()
        pop.hide()
        if had_keyboard:
            self.activateWindow()

    def _in_display_popover(self, w):
        """!
        @brief True when a widget belongs to the Display popover, also through a window of its own (the open list of one of its combo boxes).
        @details `QWidget.isAncestorOf` stops at a window boundary, so the drop-down list of the Underlay or Colour map combo, which is a popup window, was taken for
                 a click outside and closed the popover before the entry could be chosen (found in the review).
        @param w QWidget.
        @return bool.
        """
        pop = getattr(self, "display_popover", None)
        if pop is None or not shiboken6.isValid(pop):
            return False
        while w is not None:
            if w is pop:
                return True
            w = w.parentWidget()
        return False

    def eventFilter(self, obj, event):
        """!
        @brief Close the Display popover on a click anywhere outside it and its button, and on Escape in the popover or in this window.
        @param obj Object that receives the event.
        @param event The event.
        @return True for the Escape that closed the popover (it does not also cancel a drawing on the canvas), False otherwise.
        """
        pop = getattr(self, "display_popover", None)
        if pop is not None and shiboken6.isValid(pop) and pop.isVisible() and isinstance(obj, QWidget):
            if event.type() == QEvent.MouseButtonPress:
                if not (self._in_display_popover(obj) or obj is self.display_button):
                    self._close_display_popover()
            elif (event.type() == QEvent.KeyPress and event.key() == Qt.Key_Escape and QApplication.activePopupWidget() is None
                  and (self._in_display_popover(obj) or obj.window() is self)):
                self._close_display_popover()
                return True
        return False

    def changeEvent(self, e):
        """!
        @brief Close the Display popover when the window loses the activation to anything but the popover (another application, another window).
        @param e QEvent.
        """
        super().changeEvent(e)
        if e.type() == QEvent.ActivationChange and not self.isActiveWindow() and getattr(self, "display_popover", None) is not None:
            # Decided after the change has settled: a click into the popover activates the popover itself, which must not close it
            QTimer.singleShot(0, self._close_popover_if_inactive)

    def _close_popover_if_inactive(self):
        """!
        @brief Close the Display popover when neither this window nor the popover (nor a list it opened) is the active window.
        """
        # A call queued by changeEvent can run after the window (and with it the popover) was deleted
        if not shiboken6.isValid(self) or not shiboken6.isValid(getattr(self, "display_popover", None)):
            return
        active = QApplication.activeWindow()
        if active is self or (active is not None and self._in_display_popover(active)) or QApplication.activePopupWidget() is not None:
            return
        self._close_display_popover()

    def _sync_underlay(self):
        """!
        @brief Tell the display choice what the project offers under the map (copper, and the image of a hand-drawn project).
        @details An image that appears for the first time brings its stored opacity (older projects) as the initial opacity of the map over it; the file format is unchanged.
        """
        cfg = self.doc.project.view.get("background")
        imported = self._is_imported()
        self.results.set_underlay_source(imported, cfg)
        key = None if imported or not cfg else cfg.get("path")
        if key is not None and key != self._underlay_key and cfg.get("opacity") is not None:
            self.display.set_opacity(cfg["opacity"] * 100.0)
        self._underlay_key = key
        if self.display_popover is not None and shiboken6.isValid(self.display_popover):
            self.display_popover.refresh()
        self._editor_apply_underlay(self.a_overlay.isChecked())

    def _overlay_follow_results(self, *_):
        """!
        @brief A control of the Temperature tab changed (model, Auto range, limits): paint the map on the board again with it, when the map is on.
        @param _ Ignored (the value carried by the Qt signal).
        """
        if self.a_overlay.isChecked() and not self.results.temp._updating:      # Not while the tab is being filled with a new simulation
            self._toggle_overlay(True)

    def _refresh_layers(self):
        """!
        @brief Rebuild the layer chooser from the board.
        """
        self._apply_layer(redraw_board=False)

    def _layer_ctx(self):
        """!
        @brief Where the toolbar Layer box is used now: the name of the context (editor, power profile page, or one of the Results maps).
        @return One of tips.LAYER_TIPS keys.
        """
        i = self.tabs.currentIndex()
        if i == TAB_PROFILE:
            return "profile page"
        if i == TAB_RESULTS:
            w = self.results.tabs.currentWidget()
            for name, tab in (("temperature", self.results.temp), ("gradient", self.results.grad), ("animation", self.results.animation),
                              ("profiles", self.results.profile), ("profiles", self.results.time_sim)):
                if w is tab:
                    return name
            return "results"
        return "editor"

    def _apply_layer(self, redraw_board=True):
        """!
        @brief Show the layer choice in the toolbar box, the editor, the map on the board and every tab.
        @details The box lists, by context, layers 1..n (editor, power profile page, Gradients, Animation, Profiles) or All layers, All (2 x 2), the layers and the metal
                 block of the result (Temperature). A tab that cannot show the stored choice shows the last single layer and a one-line note says so.
        @param redraw_board False while the board is being rebuilt (the caller draws the map).
        """
        n = self.doc.problem.board.layers
        ctx = self._layer_ctx()
        faces = self.results.temp.block_faces() if getattr(self, "sim", None) is not None else []
        kind = layerchoice.EXTENDED_CONTEXT if ctx == "temperature" else "single"
        value, note = self.layer_choice.effective(kind, n, faces)
        entries = layerchoice.items(kind, n, faces)
        box = self.layer_combo
        if [(box.itemText(i), box.itemData(i)) for i in range(box.count())] != entries:
            box.blockSignals(True)
            box.clear()
            for text, data in entries:
                box.addItem(text, data)
            box.blockSignals(False)
        box.blockSignals(True)
        box.setCurrentIndex(max(box.findData(value), 0))
        box.blockSignals(False)
        self.layer_context = ctx
        box.setToolTip(tips.LAYER_TIPS.get(ctx, tips.LAYER_TIPS["editor"]))
        single = self.layer_choice.single(n)
        changed = self.canvas.layer != single
        if changed:
            self.canvas.set_layer(single)                  # The drawing layer and the layer of the map on the board are the same choice
        self.results.set_layer(self.layer_choice.effective(layerchoice.EXTENDED_CONTEXT, n, faces)[0], single)
        self.results.set_layer_note(note if ctx in ("gradient", "animation", "profiles") else "")
        if changed and redraw_board and self.a_overlay.isChecked():
            self._toggle_overlay(True)                     # The map follows the layer being edited

    def _on_layer_changed(self, idx):
        """!
        @brief The user picked an entry of the toolbar Layer box.
        @param idx Combo index.
        """
        data = self.layer_combo.itemData(idx) if idx >= 0 else None
        if data is not None:
            self.layer_choice.pick(data)
            self._apply_layer()

    def _set_layer(self, layer):
        """!
        @brief Choose a copper layer by code (a selection on another layer, a clicked warning).
        @param layer Layer index (0-based).
        """
        self.layer_choice.follow(layer)                  # Not a pick: a stored All layers stays in Temperature, the drawing layer and the single maps move
        self._apply_layer()

    def _select_all(self):
        """!
        @brief Select every element of the active layer.
        """
        pr, L = self.doc.problem, self.canvas.layer
        items = [(k, i) for k, lst in (("zone", pr.zones), ("heater", pr.heaters), ("heatsink", pr.heatsinks))
                 for i, e in enumerate(lst) if e.layer == L] + [("via", i) for i in range(len(pr.vias))]
        self.canvas.set_selection(items)
        self._on_canvas_selection(items)

    def _on_canvas_selection(self, items):
        """!
        @brief Mirror the canvas selection in the list and the inspector.
        @param items List of (kind, index).
        """
        self.elements.set_selected(items)
        self.inspector.set_selection(items)

    def _on_list_selection(self, items):
        """!
        @brief Apply a selection made in the element list.
        @param items List of (kind, index).
        """
        pr = self.doc.problem
        layers = {getattr(e, "layer", None) for k, i in items
                  for e in [getattr(pr, {"zone": "zones", "heater": "heaters", "heatsink": "heatsinks", "via": "vias"}[k])[i]]}
        layers.discard(None)
        if len(layers) == 1 and self.canvas.layer not in layers:
            self._set_layer(next(iter(layers)))      # Switch to the layer of the element
        self.canvas.set_selection(items)
        self.inspector.set_selection(items)

    def _select_from_warning(self, kind, index):
        """!
        @brief Select the element that a clicked input warning is about (switching to its layer).
        @param kind Element kind ("zone", "heater", "heatsink" or "via").
        @param index 0-based index of the element in its list.
        """
        lst = getattr(self.doc.problem, {"zone": "zones", "heater": "heaters", "heatsink": "heatsinks", "via": "vias"}.get(kind, ""), None)
        if lst is None or not 0 <= index < len(lst):
            return
        layer = getattr(lst[index], "layer", None)
        if layer is not None and self.canvas.layer != layer:
            self._set_layer(layer)         # The element is drawn on its own layer
        self.canvas.set_selection([(kind, index)])
        self._on_canvas_selection([(kind, index)])

    def _on_created(self, kind, index):
        """!
        @brief Select a new element and return to the Select tool.
        @param kind Element kind.
        @param index Index.
        """
        self.canvas.set_selection([(kind, index)])
        self._on_canvas_selection([(kind, index)])
        self.tool_actions["select"].setChecked(True)
        self.canvas.set_tool("select")

    def _on_options_changed(self):
        """!
        @brief Schedule the live checks again when the selected models or the cell changed (the limits of the models and the via checks depend on them).
        """
        key = (tuple(self.doc.options.models), self.doc.options.cell_mm)
        if key != self._checks_key:
            self._checks_key = key
            self._check_timer.start()

    def _update_checks(self):
        """!
        @brief Run the live input checks (validity, limits of the selected models, vias; no solve) and show them in the Simulation panel.
        @details The same warnings, in the same order, that api.simulate puts at the head of the warnings of a run: the list shows the one-line form of each, the
                 Results summary and the tooltip of the item hold the full measured text, and the summary adds only what a run knows.
                 Run in the window's thread by a single-shot timer (restarted, never stacked); a calculation runs in its own process and is not slowed by it.
        """
        try:
            self.solver_panel.set_checks(check_input(self.doc.problem, self.doc.options.models, max(self.doc.options.cell_mm, 0.5), live=True, ui="gui"))
        except Exception:                                     # A half-edited design may be inconsistent
            self.solver_panel.set_checks([])

    def _on_doc_changed(self):
        """!
        @brief React to edits: refresh the layer list, mark results as outdated, schedule the input checks.
        """
        self._edits += 1
        self._update_background_action()
        self._sync_underlay()
        self.solver_panel.checks.set_stale()               # Until the check runs again its links could point to another element
        tips.apply(self.profile_page)                      # The profile page rebuilds its forms with the choices
        self._check_timer.start()
        self._refresh_layers()
        self._update_title()
        if self.sim is not None and not self._stale:
            self._stale = True
            self.tabs.setTabText(TAB_RESULTS, "Results (outdated)")
            self.canvas.clear_overlay()
            self.a_overlay.setChecked(False)
            self._update_map_button()

    def _update_title(self):
        """!
        @brief Window title with the file name and the modified flag.
        """
        self.setWindowTitle(f"{self.doc.title}{' *' if self.doc.modified else ''} - PCB Thermal Lab {__version__}")

    # ------------------------------------------------------------------ files
    def _confirm_discard(self):
        """!
        @brief Ask what to do with unsaved changes.
        @return True if it is fine to continue.
        """
        if not self.doc.modified:
            return True
        r = QMessageBox.question(self, "Unsaved changes", "Save the changes before continuing?",
                                 QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        if r == QMessageBox.Save:
            return self.save_file()
        return r == QMessageBox.Discard

    def _after_load(self):
        """!
        @brief Reset the views after a new document was loaded.
        """
        self.sim, self._stale = None, False
        self.tabs.setTabText(TAB_RESULTS, "Results")
        self.canvas.clear_overlay()
        self.a_overlay.setChecked(False)
        self._update_map_button()
        self.canvas.fit()
        self._refresh_layers()
        # A document just opened: its stored background opacity is the initial one again, also when the image file is the same as before
        self._underlay_key = None
        # Starting from scratch (or a project with no stored opacity) the pairs are 70 % again, not the previous project's value
        self.display.reset()
        self._sync_underlay()
        # The load rebuilt the canvas before this "Ready." could overwrite its message: say again that the stored image cannot be drawn
        self.statusBar().showMessage(self.canvas.background_problem or "Ready.")

    def new_board(self):
        """!
        @brief Create a new empty board.
        """
        if not self._confirm_discard():
            return
        d = NewBoardDialog(self)
        if d.exec():
            self.doc.new(d.w.value(), d.h.value(), d.layers.value())
            self._after_load()

    def open_file(self, path=None):
        """!
        @brief Open a project file.
        @param path Optional path; a file dialog is shown if omitted.
        """
        if not self._confirm_discard():
            return
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, "Open project", "", FILE_FILTER)
        if not path:
            return
        try:
            self.doc.open(path)
        except Exception as exc:
            QMessageBox.critical(self, "Cannot open file", str(exc))
            return
        self._after_load()
        package_actions.report_read_warnings(self)          # members of a package that were dropped or not verified: said, never silent

    def _load_problem(self, problem, name):
        """!
        @brief Load a ready-made problem as a new unsaved document.
        @param problem Problem.
        @param name Project name.
        """
        if self._confirm_discard():
            self.doc.open_problem(problem, name)
            self._after_load()

    def save_file(self):
        """!
        @brief Save to the current path (asks for one if needed).
        @return True if saved.
        """
        if not self.doc.path:
            return self.save_file_as()
        try:
            backup = self.doc.save()
        except Exception as exc:
            QMessageBox.critical(self, "Cannot save", str(exc))
            return False
        self._report_backup(backup)
        package_actions.report_notes(self)
        return True

    def _report_backup(self, backup):
        """!
        @brief Say in the status bar that a save changed the file format and kept a copy of the old file.
        @param backup Path of the copy, or None (nothing is shown).
        """
        if backup:
            self.statusBar().showMessage(f"Saved. The file format changed (a project with imported boards needs 2.5.0 or later); "
                                         f"the old file was kept as {backup}", 15000)

    def save_file_as(self):
        """!
        @brief Save under a new name.
        @return True if saved.
        """
        return package_actions.save_as(self)

    def export_results(self):
        """!
        @brief Save report, summary, CSV fields and figures to a folder.
        """
        if self.sim is None:
            QMessageBox.information(self, "Export", "Run a simulation first.")
            return
        d = QFileDialog.getExistingDirectory(self, "Export results to folder")
        if d:
            files = self.sim.save(d, plots=True)
            self.statusBar().showMessage(f"{len(files)} files written to {d}")

    def export_report(self):
        """!
        @brief Save the text report.
        """
        if self.sim is None:
            QMessageBox.information(self, "Export", "Run a simulation first.")
            return
        p, _ = QFileDialog.getSaveFileName(self, "Export report", "report.txt", "Text (*.txt)")
        if p:
            Path(p).write_text(self.sim.report(), encoding="utf-8")

    def export_summary(self):
        """!
        @brief Save the JSON summary.
        """
        if self.sim is None:
            QMessageBox.information(self, "Export", "Run a simulation first.")
            return
        p, _ = QFileDialog.getSaveFileName(self, "Export summary", "summary.json", "JSON (*.json)")
        if p:
            Path(p).write_text(json.dumps(self.sim.to_dict(), indent=2), encoding="utf-8")

    def set_background(self):
        """!
        @brief Choose and place a background image.
        """
        b = self.doc.problem.board
        has_bg = bool(self.doc.project.view.get("background"))
        imported = self._is_imported()
        if imported and not has_bg:
            return                                          # Menu, shortcut or command: nothing to choose or remove
        d = BackgroundDialog(self.doc.project.view.get("background"), (b.width * 1000, b.height * 1000), self, imported=imported)
        if d.exec():
            cfg = d.config()
            if cfg:
                self.doc.project.view["background"] = cfg
                if self.doc.project.package is not None:
                    self.doc.project.package.foreign_background = None   # chosen by the user now: a package may store it
            else:
                self.doc.project.view.pop("background", None)
            self.canvas.rebuild()
            self._sync_underlay()

    def _is_imported(self):
        """!
        @brief Whether the project comes from Gerber files (an import record or imported copper).
        @return True for an imported project.
        """
        return bool(self.doc.project.imports) or self.doc.problem.imported is not None

    def _update_background_action(self):
        """!
        @brief Enable "Background image..." only for a hand-drawn project (an imported one with an old image can still open it to remove the image).
        """
        imp = self._is_imported()
        keep = imp and bool(self.doc.project.view.get("background"))
        self.a_bg.setEnabled(not imp or keep)
        tip = BACKGROUND_IMPORTED_TIP if imp else "Place an image under the board to trace it"
        if keep:
            tip = BACKGROUND_IMPORTED_TIP + " The image stored by an older version is kept; open this to remove it."
        self.a_bg.setToolTip(tip)
        self.a_bg.setStatusTip(tip)

    # ------------------------------------------------------------------ simulation
    def run_simulation(self):
        """!
        @brief Validate the problem and start the simulation in the background.
        """
        if self.worker is not None and self.worker.isRunning():
            return
        try:
            self.doc.problem.validate()
            self.doc.options.validate()
            if not self.doc.problem.heaters or self.doc.problem.total_power() <= 0:
                raise ValueError("Add at least one heater with a power above zero.")
        except ValueError as exc:
            QMessageBox.warning(self, "Cannot run", str(exc))
            return
        # The memory guard in the window: a model above the limit never starts a process (the panel disables Run too; F5 and the menu arrive here), and a run that
        # needs more than the memory available now only warns
        self.solver_panel.refresh()
        if self.solver_panel.blocked:
            QMessageBox.warning(self, "Cannot run: not enough memory", self.solver_panel.blocked)
            return
        low = [v.message for v in self.solver_panel.verdicts() if v.exceeds_available]
        self.solver_panel.set_running(True, "Starting…" if not low else "Starting… " + low[0])
        if low:
            self.statusBar().showMessage(low[0], 10000)
        self._run_edits = self._edits
        self.worker = ProcessWorker("simulate", copy.deepcopy(self.doc.problem), dataclasses.replace(copy.deepcopy(self.doc.options), ui="gui"))
        self.worker.progress.connect(self.solver_panel.set_progress)
        self.worker.done.connect(self._on_done)
        self.worker.failed.connect(self._on_failed)
        self.worker.cancelled.connect(lambda: self._on_cancelled(self.solver_panel))
        compute.start(self.worker)

    def cancel_simulation(self):
        """!
        @brief Cancel the simulation (and the animation or analysis computing) without waiting: the calculation process is stopped.
        """
        for w in (self.worker, getattr(self, "_anim_worker", None), self.profile_page.worker):
            if w is not None and w.isRunning():
                w.cancel()

    def _on_cancelled(self, panel):
        """!
        @brief Return the panel to its idle state after a cancelled simulation.
        @param panel The SolverPanel.
        """
        self._run_edits = None
        panel.set_running(False, "Cancelled.")

    def _show_defaults_state(self, startup=False):
        """!
        @brief Say in the status bar when the user's defaults file is in use (and what it changes).
        @param startup True at start-up: a message is also shown for a few seconds.
        """
        text = defaults.diff_text()
        if defaults.has_user_file() and text:
            self.defaults_label.setText("Custom defaults")
            self.defaults_label.setToolTip(f"Your defaults file is in use: {defaults.user_file()}\nIt changes {text}.\nPreferences to change or reset it.")
            if startup:
                self.statusBar().showMessage(f"Custom defaults in use ({text}): {defaults.user_file()}", 8000)
        else:
            self.defaults_label.setText("")
            self.defaults_label.setToolTip("The program is using the shipped defaults (Preferences).")

    def show_preferences(self):
        """!
        @brief Open the preferences window; after it, refresh what depends on the libraries.
        """
        d = PreferencesDialog(self)
        d.exec()
        if d.saved:
            self.doc.options.memory_fraction = memory.default_fraction()       # The machine preference may have changed; the panel shows the new verdicts
            self.solver_panel.refresh()
            self._show_defaults_state()
            self.inspector.rebuild()
            self.stackup_page.refresh()
            self.statusBar().showMessage("Defaults saved. New boards and elements use them; open boards keep their values.", 6000)

    def show_import(self):
        """!
        @brief Open the Gerber import window; a finished import is loaded as a new unsaved project, or, when the open project already holds an import, applied to it as one undo step
               (the window asked Replace, Update, Add files, New project or Cancel).
        """
        existing = None
        if self.doc.project.imports:
            # The re-import dialog shows what each part keeps: the powers typed in the editor after the import, not those of the import itself
            existing = copy.deepcopy(self.doc.project.imports[0])
            editor_part_values(existing, self.doc.problem)
        dlg = ImportBoardWindow(self, existing=existing)
        cap = package_actions.capture_on_close(dlg)
        if existing is not None and package_actions.stored_sources(self):
            package_actions.offer_stored_sources(self, dlg)          # the project stores its source files: the re-import can start from them
        if dlg.exec() != QDialog.Accepted or dlg.record is None:
            return
        if dlg.mode == "new":
            if self._confirm_discard():
                dlg.problem.name = dlg.session.name
                self.doc.open_import(dlg.problem, dlg.record)
                package_actions.remember_import(self, cap)   # keep the source files in memory so that Export package can store them
                self._after_load()
            return
        old = copy.deepcopy(self.doc.project.imports[0])
        typed = getattr(dlg, "typed", set())
        synced = []
        # Add files: the heaters of the new parts, the heaters of the stored parts the new files moved, and the step-2 values (review: the heaters stayed where they were)
        kept = self.doc.reimport(dlg.problem, dlg.record, f"Re-import Gerber board ({dlg.mode})", typed=typed, carry_parts=getattr(dlg, "carry_parts", True),
                                 add=lambda project: synced.extend(sync_add_heaters(dlg.session, project.problem, old, dlg.record, typed)))
        kept = kept + synced
        package_actions.remember_import(self, cap, replace=dlg.mode != "add")
        self._refresh_layers()
        # What the editor kept comes first (the user must see it), then the first changes of the parts and files
        lines = kept + [c for c in dlg.changes if c.startswith("not taken")] + [c for c in dlg.changes if not c.startswith("not taken")]
        # The numbers first: copper layers replaced, files and parts, holes (never an empty text)
        lines = [reimport_summary(old, dlg.record, dlg.mode)] + lines
        self.statusBar().showMessage(f"Gerber board re-imported ({dlg.mode}): " + "; ".join(lines[:4]) + ("..." if len(lines) > 4 else ""))

    def show_calculator(self):
        """!
        @brief Open the power calculator.
        """
        PowerCalculator(self.doc, self).exec()

    def _suggest_animation(self, _index=None):
        """!
        @brief Preset the animation duration to a few time constants of the current board.
        @param _index Ignored (the tab index of the Qt signal).
        """
        if self.tabs.currentIndex() == TAB_RESULTS and self.doc.problem.heaters:
            try:
                self.results.animation.suggest_duration(5.0 * fvm.estimate_time_constant(self.doc.problem))
            except Exception:
                pass

    def compute_animation(self, kwargs):
        """!
        @brief Compute the transient response in the background and hand it to the animation tab.
        @param kwargs Duration, frame count, scheme and spacing chosen in the tab.
        """
        anim = self.results.animation
        try:
            self.doc.problem.validate()
            if self.doc.problem.total_power() <= 0:
                raise ValueError("Add at least one heater with a power above zero.")
        except ValueError as exc:
            anim.computing_failed(str(exc))
            return
        # With computed heat transfer coefficients, animate with the ones of the last simulation (fixed during the run)
        source = self.sim.effective_problem if (self.sim is not None and not self._stale and self.sim.effective_problem) \
            else self.doc.problem
        problem = copy.deepcopy(source)
        kwargs = dict(kwargs, cell_mm=max(self.doc.options.cell_mm, 1.0), laminate=self.doc.options.laminate_params())
        # The animation holds the factor of the matrix and the frames (memory.TRANSIENT_FACTOR): checked here with the preference, so that the message comes at once
        if kwargs.get("model", "fvm") in ("fvm", "fdm"):
            try:
                memory.check(problem, (kwargs.get("model", "fvm"),), kwargs["cell_mm"], fraction=self.doc.options.memory_fraction, transient=True, base=memory.BASE_DEFAULT,
                             laminate_params=self.doc.options.laminate_params())
            except memory.MemoryGuardError as exc:
                anim.computing_failed(str(exc))
                return
        self._anim_worker = ProcessWorker("transient", problem, kwargs)
        self._anim_worker.done.connect(lambda tr: anim.set_result(tr, problem))
        self._anim_worker.failed.connect(anim.computing_failed)
        self._anim_worker.cancelled.connect(lambda: anim.computing_failed("Cancelled."))
        compute.start(self._anim_worker)

    def _on_done(self, sim):
        """!
        @brief Show the results of a finished simulation.
        @param sim Simulation.
        """
        # An edit made while the solver ran means the result belongs to the previous design
        self.sim, self._stale = sim, self._run_edits is not None and self._edits != self._run_edits
        self._run_edits = None
        self.results.set_simulation(sim)
        self._apply_layer(redraw_board=False)              # The list of the Temperature context depends on the result (metal block)
        tips.apply(self.results)
        if sim.decisions:
            self.profile_page.show_decisions(sim.decisions, sim.profile_reference)
        self.tabs.setTabText(TAB_RESULTS, "Results (outdated)" if self._stale else "Results")
        ref = sim.reference
        self.solver_panel.set_running(False, f"Done: Tmax {ref.t_max:.1f} °C, Rθ {ref.r_theta:.2f} K/W"
                                      + ("  (the design changed while it ran)" if self._stale else ""))
        self.tabs.setCurrentIndex(TAB_RESULTS)
        self._update_map_button()
        if self.a_overlay.isChecked():
            self._toggle_overlay(True)             # Refused while the result is outdated

    def _on_failed(self, message):
        """!
        @brief Report a failed simulation.
        @param message Error text.
        """
        self.solver_panel.set_running(False, "Failed.")
        QMessageBox.critical(self, "Simulation failed", message)

    # ------------------------------------------------------------------ misc
    def toggle_theme(self):
        """!
        @brief Switch between the dark and light themes.
        """
        self.theme_name = "light" if self.theme_name == "dark" else "dark"
        self.settings.setValue("theme", self.theme_name)
        th.apply_theme(QApplication.instance(), self.theme_name)
        self.canvas.set_theme(self.theme_name)
        self.results.set_theme(self.theme_name)
        self.profile_page.set_theme(self.theme_name)
        self.stackup_page.set_theme(self.theme_name)
        self.solver_panel.refresh()                                         # The memory verdicts take the colours of the new theme
        self.solver_panel.checks.recolour()                                 # The links of the warnings take the link colour of the new palette
        self._refresh_icons()

    SHORTCUTS_HTML = """<table cellpadding=3>
<tr><td><b>S Z H C V O</b></td><td>Select, Zone, Heater, Heatsink (Cooling), Via, board Outline tools</td></tr>
<tr><td><b>P</b></td><td>Polygon mode (click vertices; double click or Enter finishes)</td></tr>
<tr><td><b>Wheel / middle drag / Space+drag</b></td><td>Zoom / pan</td></tr>
<tr><td><b>Ctrl+0, Ctrl++ (or Ctrl+=), Ctrl+-</b></td><td>Fit board, zoom in, zoom out</td></tr>
<tr><td><b>Right-click</b></td><td>On a shape: add or delete a vertex, duplicate, delete; on an empty spot: add a heater, zone, heatsink or via there</td></tr>
<tr><td><b>Del or Backspace, Ctrl+D, arrows</b></td><td>Delete, duplicate, nudge selection</td></tr>
<tr><td><b>Ctrl+A</b></td><td>Select all on the active layer</td></tr>
<tr><td><b>Ctrl+,</b></td><td>Preferences</td></tr>
<tr><td><b>Esc</b></td><td>Cancel drawing / clear selection</td></tr>
<tr><td><b>Enter / Tab</b></td><td>In a field: apply the typed number / apply it and go to the next field</td></tr>
<tr><td><b>G, Shift+G, T</b></td><td>Grid, solver grid, temperature map on the board (T; the Display button of the tool bar says how it is drawn)</td></tr>
<tr><td><b>D</b></td><td>Display settings: opens the Display panel with the keyboard in its controls</td></tr>
<tr><td><b>M</b></td><td>Model of the map: the list of the models of the result (the same as a click on the model name of the card on the board)</td></tr>
<tr><td><b>Ctrl+Shift+T</b></td><td>Light / dark theme</td></tr>
<tr><td><b>F5 / Ctrl+.</b></td><td>Run simulation / cancel the calculation</td></tr>
<tr><td><b>Ctrl+1 to Ctrl+4</b></td><td>Board, Stack-up, Power profile, Results tabs</td></tr>
<tr><td><b>Ctrl+Z / Ctrl+Shift+Z or Ctrl+Y</b></td><td>Undo / redo</td></tr>
<tr><td><b>F1</b></td><td>User guide</td></tr>
<tr><td><b>macOS</b></td><td>Ctrl in this table is the Command key (⌘); Backspace (the key labelled delete) also deletes the selection</td></tr></table>"""

    def show_shortcuts(self):
        """!
        @brief Show the keyboard and mouse help (the text is SHORTCUTS_HTML, which tests/test_shortcuts.py checks against the real shortcuts).
        """
        QMessageBox.information(self, "Keyboard and mouse", self.SHORTCUTS_HTML)

    def show_about(self):
        """!
        @brief Show the About box (program, version, author, project link, licence and the scope of the validation).
        """
        AboutDialog(self).exec()

    def show_guide(self):
        """!
        @brief Show the user guide inside the program.
        """
        if self._guide is None:
            self._guide = GuideWindow(self)
        self._guide.show()
        self._guide.raise_()

    def closeEvent(self, e):
        """!
        @brief Confirm unsaved changes and remember the window geometry.
        @param e QCloseEvent (accepted or ignored here).
        """
        if self._confirm_discard():
            self._close_display_popover()              # A floating panel does not outlive its window
            compute.shutdown()                         # Nothing keeps running in the background after the window closes
            self.settings.setValue("geometry", self.saveGeometry())
            self.settings.setValue("window_state", self.saveState(self.STATE_VERSION))      # Dock positions and visibility
            self.settings.setValue("dock_sizes", [self.dock_board.width(), self.dock_sim.width(), self.dock_board.height(),
                                                  self.dock_elements.height(), self.dock_sim.height(), self.dock_inspector.height()])
            e.accept()
        else:
            e.ignore()
