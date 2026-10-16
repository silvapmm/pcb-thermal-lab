"""!
@file main_window.py
@brief Main window: menus, tool bar, docks, board canvas, results and background simulation.
"""

import copy
import json
import os
from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QAction, QActionGroup, QIcon, QKeySequence
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDockWidget,
                               QDoubleSpinBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QMainWindow,
                               QMessageBox, QPushButton, QSlider, QSpinBox, QStatusBar, QTabWidget, QToolBar,
                               QVBoxLayout, QWidget)

from .. import __version__
from .. import fvm
from ..api import simulate
from ..checks import check_problem
from ..examples import example_board
from ..model import reference_problem
from . import theme as th
from .canvas import BoardView
from .animation import TransientWorker
from .document import Document
from .panels import BoardPanel, ElementList, Inspector, SolverPanel
from .profile_page import ProfilePage
from .results_view import ResultsView

FILE_FILTER = "PCB Thermal projects (*.pcbt.json *.json);;All files (*)"


TAB_BOARD, TAB_PROFILE, TAB_RESULTS = 0, 1, 2     # Order of the main tabs


class SimWorker(QThread):
    """!
    @brief Runs simulate() in a background thread so the window stays responsive.
    """

    progress = Signal(str, float)
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, problem, options, parent=None):
        """!
        @param problem Problem (deep-copied so later edits cannot race with the solver).
        @param options SolverOptions (copied).
        @param parent Qt parent.
        """
        super().__init__(parent)
        self.problem, self.options = copy.deepcopy(problem), copy.deepcopy(options)

    def run(self):
        """!
        @brief Thread body: run the simulation and emit the outcome.
        """
        try:
            self.done.emit(simulate(self.problem, self.options, progress=lambda m, f: self.progress.emit(m, f)))
        except Exception as exc:                       # Any solver or validation error goes to the user
            self.failed.emit(str(exc))


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
        for s, v in ((self.w, 100.0), (self.h, 80.0)):
            s.setRange(5, 1000)
            s.setValue(v)
            s.setSuffix(" mm")
        self.layers = QSpinBox()
        self.layers.setRange(1, 12)
        self.layers.setValue(2)
        f.addRow("Width", self.w)
        f.addRow("Height", self.h)
        f.addRow("Copper layers", self.layers)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        f.addRow(bb)


class BackgroundDialog(QDialog):
    """!
    @brief Place a photo or layout image under the board (position, size, opacity).
    """

    def __init__(self, cfg, board_mm, parent=None):
        """!
        @param cfg Current background dict or None.
        @param board_mm Board size (width, height) in mm, used by "Fit to board".
        @param parent Qt parent.
        """
        super().__init__(parent)
        self.setWindowTitle("Background image")
        self.board_mm = board_mm
        cfg = cfg or {}
        self.path = cfg.get("path", "")
        f = QFormLayout(self)
        self.file_label = QLabel(os.path.basename(self.path) or "no image")
        choose = QPushButton("Choose image…")
        choose.clicked.connect(self._choose)
        row = QHBoxLayout()
        row.addWidget(self.file_label, 1)
        row.addWidget(choose)
        f.addRow(row)
        self.x, self.y, self.w, self.h = (QDoubleSpinBox() for _ in range(4))
        for s, k, d in ((self.x, "x_mm", 0.0), (self.y, "y_mm", 0.0), (self.w, "w_mm", board_mm[0]),
                        (self.h, "h_mm", board_mm[1])):
            s.setRange(-2000, 4000)
            s.setDecimals(2)
            s.setSuffix(" mm")
            s.setValue(cfg.get(k, d))
        self.opacity = QSlider(Qt.Horizontal)
        self.opacity.setRange(5, 100)
        self.opacity.setValue(int(cfg.get("opacity", 0.5) * 100))
        fit = QPushButton("Fit to board")
        fit.clicked.connect(self._fit)
        for label, w in (("X", self.x), ("Y", self.y), ("Width", self.w), ("Height", self.h),
                         ("Opacity", self.opacity)):
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
        return {"path": self.path, "x_mm": self.x.value(), "y_mm": self.y.value(), "w_mm": self.w.value(),
                "h_mm": self.h.value(), "opacity": self.opacity.value() / 100.0}


class MainWindow(QMainWindow):
    """!
    @brief The application window.
    """

    def __init__(self, doc=None, settings=None):
        """!
        @param doc Optional Document to edit (default: a new empty board).
        @param settings Optional QSettings (tests pass a temporary one so real preferences are untouched).
        """
        super().__init__()
        self.settings = settings or QSettings("PMS Labs", "PCB Thermal Lab")
        self.theme_name = self.settings.value("theme", "dark")
        self.doc = doc or Document()
        self.sim, self.worker, self._stale = None, None, False

        self.canvas = BoardView(self.doc, self.theme_name)
        self.results = ResultsView(self.theme_name)
        self.tabs = QTabWidget()
        self.tabs.addTab(self.canvas, "Board")
        self.profile_page = ProfilePage(self.doc, self.theme_name)
        self.tabs.addTab(self.profile_page, "Power profile")
        self.tabs.addTab(self.results, "Results")
        self.setCentralWidget(self.tabs)

        self.board_panel = BoardPanel(self.doc)
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
        self.statusBar().addPermanentWidget(self.coord_label)
        self.statusBar().addPermanentWidget(self.version_label)

        self.canvas.selection_changed.connect(self._on_canvas_selection)
        self.canvas.cursor_moved.connect(lambda x, y: self.coord_label.setText(f"x {x:7.2f} mm   y {y:7.2f} mm"))
        self.canvas.message.connect(lambda m: self.statusBar().showMessage(m))
        self.canvas.element_created.connect(self._on_created)
        self.elements.selection_requested.connect(self._on_list_selection)
        self.solver_panel.run_requested.connect(self.run_simulation)
        self.results.animation.compute_requested.connect(self.compute_animation)
        self.tabs.currentChanged.connect(self._suggest_animation)
        self._check_timer = QTimer(self)                      # Re-check the design shortly after the last edit
        self._check_timer.setSingleShot(True)
        self._check_timer.setInterval(350)
        self._check_timer.timeout.connect(self._update_checks)
        self.doc.changed.connect(self._on_doc_changed)
        self.doc.state_changed.connect(self._update_title)
        self.doc.state_changed.connect(lambda: self.canvas.__setattr__("solver_cell", self.doc.options.cell_mm))

        th.apply_theme(QApplication.instance(), self.theme_name)
        self._refresh_icons()
        self._refresh_layers()
        self._update_title()
        self.resize(1480, 900)
        geo = self.settings.value("geometry")
        if geo:
            self.restoreGeometry(geo)
        self.canvas.set_tool("select")

    # ------------------------------------------------------------------ construction
    def _dock(self, title, widget, area):
        """!
        @brief Add a titled dock widget.
        @param title Dock title.
        @param widget Content widget.
        @param area Qt dock area.
        @return The QDockWidget.
        """
        d = QDockWidget(title, self)
        d.setObjectName(title)
        d.setWidget(widget)
        d.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.addDockWidget(area, d)
        return d

    def _build_docks(self):
        """!
        @brief Create the left and right docks.
        """
        self.dock_board = self._dock("Board", self.board_panel, Qt.LeftDockWidgetArea)
        self.dock_elements = self._dock("Elements", self.elements, Qt.LeftDockWidgetArea)
        self.splitDockWidget(self.dock_board, self.dock_elements, Qt.Vertical)
        self.dock_sim = self._dock("Simulation", self.solver_panel, Qt.RightDockWidgetArea)
        self.dock_inspector = self._dock("Properties", self.inspector, Qt.RightDockWidgetArea)
        self.splitDockWidget(self.dock_sim, self.dock_inspector, Qt.Vertical)
        self.resizeDocks([self.dock_board, self.dock_sim], [310, 300], Qt.Horizontal)
        self.resizeDocks([self.dock_sim, self.dock_inspector], [470, 330], Qt.Vertical)

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
        self.a_ex_ref = self._act("Reference board (100 × 100 mm, 2 layers)", lambda: self._load_problem(reference_problem(), "reference"))
        self.a_ex_4l = self._act("Example 4-layer board (vias, sink, 2 heaters)", lambda: self._load_problem(example_board(), "example-4layer"))
        self.a_export_all = self._act("Export results to a folder…", self.export_results)
        self.a_export_txt = self._act("Export report (TXT)…", self.export_report)
        self.a_export_json = self._act("Export summary (JSON)…", self.export_summary)
        self.a_quit = self._act("Quit", self.close, QKeySequence.Quit)

        self.a_undo = self.doc.stack.createUndoAction(self, "Undo")
        self.a_undo.setShortcut(QKeySequence.Undo)
        self.a_redo = self.doc.stack.createRedoAction(self, "Redo")
        self.a_redo.setShortcut(QKeySequence.Redo)
        self.a_delete = self._act("Delete", lambda: self.doc.delete(self.canvas.selected_elements()), "Del")
        self.a_dup = self._act("Duplicate", lambda: self.canvas.set_selection(
            self.doc.duplicate(self.canvas.selected_elements())), "Ctrl+D")
        self.a_selall = self._act("Select all on layer", self._select_all, QKeySequence.SelectAll)

        self.a_fit = self._act("Fit board", self.canvas.fit, "Ctrl+0")
        self.a_zin = self._act("Zoom in", lambda: self.canvas.zoom(1.25), QKeySequence.ZoomIn)
        self.a_zout = self._act("Zoom out", lambda: self.canvas.zoom(0.8), QKeySequence.ZoomOut)
        self.a_grid = self._act("Grid", self._toggle_grid, "G", True, True)
        self.a_sgrid = self._act("Solver grid", self._toggle_solver_grid, "Shift+G", True, False,
                                 "Show the cells of the FVM mesh")
        self.a_overlay = self._act("Temperature on board", self._toggle_overlay, "T", True, False,
                                   "Paint the last result over the board")
        self.a_bg = self._act("Background image…", self.set_background)
        self.a_theme = self._act("Light / dark theme", self.toggle_theme, "Ctrl+Shift+T")

        self.a_run = self._act("Run simulation", self.run_simulation, "F5")

        self.a_keys = self._act("Keyboard shortcuts", self.show_shortcuts)
        self.a_about = self._act("About", self.show_about)

        mb = self.menuBar()
        m = mb.addMenu("&File")
        for a in (self.a_new, self.a_open, None):
            m.addAction(a) if a else m.addSeparator()
        ex = m.addMenu("Open example")
        ex.addAction(self.a_ex_ref)
        ex.addAction(self.a_ex_4l)
        for a in (None, self.a_save, self.a_saveas, None, self.a_export_all, self.a_export_txt,
                  self.a_export_json, None, self.a_quit):
            m.addAction(a) if a else m.addSeparator()
        m = mb.addMenu("&Edit")
        for a in (self.a_undo, self.a_redo, None, self.a_dup, self.a_delete, self.a_selall):
            m.addAction(a) if a else m.addSeparator()
        m = mb.addMenu("&View")
        for a in (self.a_fit, self.a_zin, self.a_zout, None, self.a_grid, self.a_sgrid, self.a_overlay, None,
                  self.a_bg, self.a_theme):
            m.addAction(a) if a else m.addSeparator()
        for d in (self.dock_board, self.dock_elements, self.dock_sim, self.dock_inspector):
            m.addAction(d.toggleViewAction())
        m = mb.addMenu("&Simulation")
        m.addAction(self.a_run)
        m = mb.addMenu("&Help")
        m.addAction(self.a_keys)
        m.addAction(self.a_about)

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
        for name, text, key in (("select", "Select", "V"), ("zone", "Copper zone", "Z"), ("heater", "Heater", "H"),
                                ("sink", "Sink", "K"), ("via", "Via", "I")):
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
        self.layer_combo = QComboBox()
        self.layer_combo.currentIndexChanged.connect(self._on_layer_changed)
        tb.addWidget(self.layer_combo)
        tb.addWidget(QLabel("  Snap "))
        self.snap_combo = QComboBox()
        for label, v in (("off", 0), ("0.1 mm", 0.1), ("0.5 mm", 0.5), ("1 mm", 1.0), ("2.5 mm", 2.5), ("5 mm", 5.0)):
            self.snap_combo.addItem(label, v)
        self.snap_combo.setCurrentIndex(3)
        self.snap_combo.currentIndexChanged.connect(lambda _i: self.canvas.set_snap(self.snap_combo.currentData()))
        tb.addWidget(self.snap_combo)
        tb.addSeparator()
        for a in (self.a_fit, self.a_grid, self.a_sgrid, self.a_overlay):
            tb.addAction(a)
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
        self.a_sgrid.setIcon(th.tool_icon("grid", self.theme_name))
        self.a_run.setIcon(th.tool_icon("run", self.theme_name))
        self.a_overlay.setIcon(th.tool_icon("overlay", self.theme_name))
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

    def _toggle_overlay(self, on):
        """!
        @brief Paint or remove the last temperature result on the board.
        @param on True to paint.
        """
        if not on or self.sim is None or self._stale:
            self.canvas.clear_overlay()
            if on and self.sim is None:
                self.statusBar().showMessage("Run a simulation first.")
                self.a_overlay.setChecked(False)
            return
        ref = self.sim.reference
        layer = min(self.canvas.layer, ref.T.shape[0] - 1)
        cfg = self.results.temp.current_field()
        self.canvas.set_overlay(ref.T[layer], ref.dx, ref.dy, cmap=cfg[3] if cfg else "inferno")

    def _refresh_layers(self):
        """!
        @brief Rebuild the layer chooser from the board.
        """
        n = self.doc.problem.board.layers
        cur = self.layer_combo.currentIndex()
        self.layer_combo.blockSignals(True)
        self.layer_combo.clear()
        for l in range(n):
            self.layer_combo.addItem(f"{l + 1}" + (" top" if l == 0 else " bottom" if l == n - 1 else ""), l)
        self.layer_combo.setCurrentIndex(min(max(cur, 0), n - 1))
        self.layer_combo.blockSignals(False)
        if self.canvas.layer != self.layer_combo.currentIndex():
            self.canvas.layer = self.layer_combo.currentIndex()

    def _on_layer_changed(self, idx):
        """!
        @brief Change the edited layer.
        @param idx Combo index (= layer).
        """
        if idx >= 0:
            self.canvas.set_layer(idx)

    def _select_all(self):
        """!
        @brief Select every element of the active layer.
        """
        pr, L = self.doc.problem, self.canvas.layer
        items = [(k, i) for k, lst in (("zone", pr.zones), ("heater", pr.heaters), ("sink", pr.sinks))
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
                  for e in [getattr(pr, {"zone": "zones", "heater": "heaters", "sink": "sinks", "via": "vias"}[k])[i]]}
        layers.discard(None)
        if len(layers) == 1 and self.canvas.layer not in layers:
            self.layer_combo.setCurrentIndex(next(iter(layers)))      # Switch to the layer of the element
        self.canvas.set_selection(items)
        self.inspector.set_selection(items)

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

    def _update_checks(self):
        """!
        @brief Run the input validity checks and show them in the Simulation panel.
        """
        try:
            self.solver_panel.set_checks(check_problem(self.doc.problem, max(self.doc.options.cell_mm, 0.5)))
        except Exception:                                     # A half-edited design may be inconsistent
            self.solver_panel.set_checks([])

    def _on_doc_changed(self):
        """!
        @brief React to edits: refresh the layer list, mark results as outdated, schedule the input checks.
        """
        self._check_timer.start()
        self._refresh_layers()
        self._update_title()
        if self.sim is not None and not self._stale:
            self._stale = True
            self.tabs.setTabText(TAB_RESULTS, "Results (outdated)")
            self.canvas.clear_overlay()
            self.a_overlay.setChecked(False)

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
        self.canvas.fit()
        self._refresh_layers()
        self.statusBar().showMessage("Ready.")

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
            self.doc.save()
        except Exception as exc:
            QMessageBox.critical(self, "Cannot save", str(exc))
            return False
        return True

    def save_file_as(self):
        """!
        @brief Save under a new name.
        @return True if saved.
        """
        path, _ = QFileDialog.getSaveFileName(self, "Save project", f"{self.doc.problem.name}.pcbt.json",
                                              "PCB Thermal projects (*.pcbt.json)")
        if not path:
            return False
        if not path.endswith(".json"):
            path += ".pcbt.json"
        try:
            self.doc.save(path)
        except Exception as exc:
            QMessageBox.critical(self, "Cannot save", str(exc))
            return False
        return True

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
        d = BackgroundDialog(self.doc.project.view.get("background"), (b.width * 1000, b.height * 1000), self)
        if d.exec():
            cfg = d.config()
            if cfg:
                self.doc.project.view["background"] = cfg
            else:
                self.doc.project.view.pop("background", None)
            self.canvas.rebuild()

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
        self.solver_panel.set_running(True, "Starting…")
        self.worker = SimWorker(self.doc.problem, self.doc.options, self)
        self.worker.progress.connect(self.solver_panel.set_progress)
        self.worker.done.connect(self._on_done)
        self.worker.failed.connect(self._on_failed)
        self.worker.start()

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
        kwargs = dict(kwargs, cell_mm=max(self.doc.options.cell_mm, 1.0))
        self._anim_worker = TransientWorker(problem, kwargs, self)
        self._anim_worker.done.connect(lambda tr: anim.set_result(tr, problem))
        self._anim_worker.failed.connect(anim.computing_failed)
        self._anim_worker.start()

    def _on_done(self, sim):
        """!
        @brief Show the results of a finished simulation.
        @param sim Simulation.
        """
        self.sim, self._stale = sim, False
        self.results.set_simulation(sim)
        if sim.decisions:
            self.profile_page.show_decisions(sim.decisions, sim.profile_reference)
        self.tabs.setTabText(TAB_RESULTS, "Results")
        ref = sim.reference
        self.solver_panel.set_running(False, f"Done: Tmax {ref.t_max:.1f} °C, Rθ {ref.r_theta:.2f} K/W")
        self.tabs.setCurrentIndex(TAB_RESULTS)
        if self.a_overlay.isChecked():
            self._toggle_overlay(True)

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
        self._refresh_icons()

    def show_shortcuts(self):
        """!
        @brief Show the keyboard and mouse help.
        """
        QMessageBox.information(self, "Keyboard and mouse", """<table cellpadding=3>
<tr><td><b>V Z H K I</b></td><td>Select, Zone, Heater, Sink, Via tools</td></tr>
<tr><td><b>P</b></td><td>Polygon mode (click vertices; double click or Enter finishes)</td></tr>
<tr><td><b>Wheel / middle drag / Space+drag</b></td><td>Zoom / pan</td></tr>
<tr><td><b>Ctrl+0</b></td><td>Fit board</td></tr>
<tr><td><b>Del, Ctrl+D, arrows</b></td><td>Delete, duplicate, nudge selection</td></tr>
<tr><td><b>Esc</b></td><td>Cancel drawing / clear selection</td></tr>
<tr><td><b>G, Shift+G, T</b></td><td>Grid, solver grid, temperature overlay</td></tr>
<tr><td><b>F5</b></td><td>Run simulation</td></tr>
<tr><td><b>Ctrl+Z / Ctrl+Shift+Z</b></td><td>Undo / redo</td></tr></table>""")

    def show_about(self):
        """!
        @brief Show the About box.
        """
        QMessageBox.about(self, "About PCB Thermal Lab", f"<b>PCB Thermal Lab</b> version {__version__}<br>"
                          "Thermal simulation of printed circuit boards with three models: "
                          "finite volumes, lumped network and analytic series.<br><br>"
                          "© 2025 Pedro Silva - PMS Labs")

    def closeEvent(self, e):
        """!
        @brief Confirm unsaved changes and remember the window geometry.
        @param e QCloseEvent (accepted or ignored here).
        """
        if self.worker is not None and self.worker.isRunning():
            self.worker.wait(30000)
        if self._confirm_discard():
            self.settings.setValue("geometry", self.saveGeometry())
            e.accept()
        else:
            e.ignore()
