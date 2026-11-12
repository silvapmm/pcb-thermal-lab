#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_underlay_default_and_shortcuts_window.py
@brief The Underlay of the Display panel for a project imported from Gerber files (Copper by default, the user's choice kept) driven through the real main window,
       and the Keyboard and mouse dialog (two columns, within the screen).
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("pytestqt")

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtTest import QTest

from pcbthermal.examples import example_board
from pcbthermal.gui import import_window as iw
from pcbthermal.gui.document import Document
from pcbthermal.gui.main_window import MainWindow
from pcbthermal.gui.shortcuts_dialog import ShortcutsDialog, parse_rows
from tests.helpers.synthetic_board import make_board


def _window(qtbot, tmp_path):
    """!
    @brief A main window on an empty project.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @return MainWindow.
    """
    w = MainWindow(Document(), QSettings(str(tmp_path / "s.ini"), QSettings.IniFormat))
    qtbot.addWidget(w)
    w.resize(1400, 850)
    w.show()
    return w


def _import(win, monkeypatch, folder):
    """!
    @brief Import a fabrication set through the real import window (the three steps, Import).
    @param win MainWindow.
    @param monkeypatch pytest fixture.
    @param folder Folder with the Gerber files.
    """
    def fake_exec(self):
        self.confirm = lambda *a: True
        self.open_path(str(folder))
        QTest.mouseClick(self.next_btn, Qt.LeftButton)
        self.session.set_part("U1", power=2.0)                            # a run needs a heater with a power
        QTest.mouseClick(self.next_btn, Qt.LeftButton)
        QTest.mouseClick(self.next_btn, Qt.LeftButton)
        return self.result()
    monkeypatch.setattr(iw.ImportBoardWindow, "exec", fake_exec)
    win.show_import()


def _run(win, qtbot):
    """!
    @brief Run the FVM on the open project at 2 mm and wait for the result.
    @param win MainWindow.
    @param qtbot pytest-qt fixture.
    """
    win.doc.set_options(models=("fvm",), cell_mm=2.0)
    win.run_simulation()
    qtbot.waitUntil(lambda: win.worker is None or not win.worker.isRunning(), timeout=180000)
    qtbot.wait(100)
    assert win.sim is not None


def test_an_imported_project_starts_with_copper_and_keeps_it_across_layers(qtbot, tmp_path, monkeypatch):
    win = _window(qtbot, tmp_path)
    _import(win, monkeypatch, make_board(tmp_path / "fab", inner=2))
    assert win._is_imported()
    assert win.display.kind == "copper"                                  # the default before any map, any click
    _run(win, qtbot)
    win.a_overlay.setChecked(True)                                       # the thermometer
    assert win.canvas._overlay is not None and win.display.kind == "copper"
    n = win.doc.problem.board.layers
    for i in range(n):                                                   # the single Layer box over every layer
        win.layer_combo.setCurrentIndex(win.layer_combo.findData(i))
        assert win.display.kind == "copper" and win.canvas.layer == i
        assert win.canvas.copper_under_map
        assert win.canvas._copper_item is not None                       # the copper of this layer is drawn under the map (every layer has a mask)
    win.results.tabs.setCurrentIndex(0)
    win._on_tab_changed(win.tabs.currentIndex())
    assert win.display.kind == "copper"
    _run(win, qtbot)                                                     # a new run
    assert win.display.kind == "copper"


def test_an_explicit_none_stays_none_for_an_imported_project(qtbot, tmp_path, monkeypatch):
    win = _window(qtbot, tmp_path)
    _import(win, monkeypatch, make_board(tmp_path / "fab", inner=2))
    _run(win, qtbot)
    win.a_overlay.setChecked(True)
    win.display.set_kind("none")                                         # what the popover does
    assert win.canvas._overlay is not None and not win.canvas.copper_under_map
    for i in range(win.doc.problem.board.layers):
        win.layer_combo.setCurrentIndex(win.layer_combo.findData(i))
        assert win.display.kind == "none"
    win._sync_underlay()
    assert win.display.kind == "none"
    win.display.set_kind("copper")
    assert win.canvas.copper_under_map


def test_none_picked_in_the_display_panel_survives_layers_runs_and_a_reimport(qtbot, tmp_path, monkeypatch):
    """!
    @brief The user's None chosen in the Underlay combo of the Display panel (not a call on the state) hides the copper under the board map and survives the layers,
           a new run and a re-import of the same files; the map turned off shows the copper again (review).
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @param monkeypatch pytest fixture.
    """
    win = _window(qtbot, tmp_path)
    fab = make_board(tmp_path / "fab", inner=2)
    _import(win, monkeypatch, fab)
    _run(win, qtbot)
    win.a_overlay.setChecked(True)
    win._toggle_display_popover()
    combo = win.display_popover.underlay
    assert combo.currentData() == "copper"
    combo.setCurrentIndex(combo.findData("none"))
    assert win.display.kind == "none" and win.display.user_set
    assert win.canvas._copper_item is not None and not win.canvas._copper_item.isVisible()
    for i in range(win.doc.problem.board.layers):
        win.layer_combo.setCurrentIndex(win.layer_combo.findData(i))
        assert win.display.kind == "none" and not win.canvas._copper_item.isVisible()
    _run(win, qtbot)
    assert win.display.kind == "none"
    win.a_overlay.setChecked(False)
    assert win.canvas._copper_item.isVisible()                          # no map on the board: the imported copper is drawn as always
    def reimport(self):
        self.confirm = lambda *a: True
        self.open_path(str(fab))
        self.ask_reimport = lambda dlg: (dlg.radios["update"].setChecked(True), True)[1]
        return 1 if self.do_import() else 0
    monkeypatch.setattr(iw.ImportBoardWindow, "exec", reimport)
    win.show_import()
    assert win._is_imported() and win.doc.project.imports
    assert win.display.kind == "none"                                   # a re-import into the same project keeps the user's choice


def test_a_drawn_board_keeps_none_by_default(qtbot, tmp_path):
    win = _window(qtbot, tmp_path)
    win._load_problem(example_board(), "t")
    assert win.display.kind == "none" and not win._is_imported()
    win.canvas.set_layer(1) if hasattr(win.canvas, "set_layer") else None
    assert win.display.kind == "none"


def test_a_new_project_after_an_imported_one_does_not_inherit_the_choice(qtbot, tmp_path, monkeypatch):
    win = _window(qtbot, tmp_path)
    _import(win, monkeypatch, make_board(tmp_path / "fab", inner=2))
    win.display.set_kind("none")
    win._load_problem(example_board(), "t")
    assert win.display.kind == "none" and not win.display.user_set
    _import(win, monkeypatch, make_board(tmp_path / "fab2", inner=2))
    assert win.display.kind == "copper"


def test_the_shortcuts_dialog_is_two_columns_and_within_the_screen(qtbot, tmp_path):
    win = _window(qtbot, tmp_path)
    rows = parse_rows(win.SHORTCUTS_HTML)
    assert len(rows) >= 15
    dlg = ShortcutsDialog(win.SHORTCUTS_HTML, "light", win)
    qtbot.addWidget(dlg)
    dlg.show()
    avail = QGuiApplication.primaryScreen().availableGeometry()
    assert dlg.width() <= 0.8 * avail.width() + 1 and dlg.height() <= 0.8 * avail.height() + 1
    assert (dlg.width(), dlg.height()) == ShortcutsDialog.fitted_size(win)
    text = dlg.browser.toPlainText()
    for keys, _t in rows:
        assert keys.split(" ")[0].replace("&amp;", "&") in text
    # two key/description pairs per line: the table has about half as many lines as rows
    assert dlg.browser.toHtml().count("<tr") <= len(rows) // 2 + 3
    assert dlg.isSizeGripEnabled()
    QTest.keyClick(dlg, Qt.Key_Escape)
    assert not dlg.isVisible()


def test_the_dialog_is_capped_on_a_small_screen(qtbot, tmp_path, monkeypatch):
    win = _window(qtbot, tmp_path)
    class Geo:
        def width(self): return 800
        def height(self): return 500
    class Scr:
        def availableGeometry(self): return Geo()
    monkeypatch.setattr(QGuiApplication, "primaryScreen", staticmethod(lambda: Scr()))
    monkeypatch.setattr(type(win), "screen", lambda self: None)
    assert ShortcutsDialog.fitted_size(None) == (640, 400)


def test_the_menu_entry_opens_the_dialog(qtbot, tmp_path, monkeypatch):
    win = _window(qtbot, tmp_path)
    seen = []
    monkeypatch.setattr(ShortcutsDialog, "exec", lambda self: seen.append(self.size()))
    win.show_shortcuts()
    assert len(seen) == 1
