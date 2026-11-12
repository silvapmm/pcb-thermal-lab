#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_gui_boxes.py
@brief The 2.6.1 redesign: collapsible boxes, the warnings accordion, the on-screen report without `WARNING:` lines, the layer keys and the export of the map over the copper.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("pytestqt")

from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDoubleSpinBox, QLineEdit

from pcbthermal import checks
from pcbthermal.api import SolverOptions, simulate
from pcbthermal.examples import example_board
from pcbthermal.gui import boxes
from pcbthermal.gui.boxes import CollapsibleBox
from pcbthermal.gui.document import Document
from pcbthermal.gui.main_window import MainWindow


@pytest.fixture
def win(qtbot, tmp_path):
    """!
    @brief A main window on the example board with its own settings file.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @return MainWindow.
    """
    w = MainWindow(Document(), QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    qtbot.addWidget(w)
    w.resize(1280, 800)
    w.show()
    w.activateWindow()
    qtbot.waitActive(w)
    w._load_problem(example_board(), "boxes")
    return w


def test_a_box_opens_collapses_and_remembers_its_state(win, qtbot, tmp_path):
    """!
    @brief The title row is the button; the state is stored by key in the settings and a new window finds the box as it was left.
    @param win MainWindow fixture.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    """
    env = next(b for b in win.dock_board.findChildren(CollapsibleBox) if b.title() == "Environment")
    assert env.is_open() and env.body.isVisibleTo(env)
    QTest.mouseClick(env.header, Qt.LeftButton)
    assert not env.is_open() and not env.body.isVisibleTo(env) and "…" in env.header.text()
    assert env.header.toolTip()
    win.settings.sync()
    w2 = MainWindow(Document(), QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    qtbot.addWidget(w2)
    assert not next(b for b in w2.dock_board.findChildren(CollapsibleBox) if b.title() == "Environment").is_open()
    boxes.set_store(win.settings)


def test_every_group_of_the_three_docks_is_a_box(win):
    """!
    @brief Board settings, Simulation settings and Properties hold their groups as collapsible boxes with the names of the mock-ups.
    @param win MainWindow fixture.
    """
    names = lambda dock: [b.title() for b in dock.findChildren(CollapsibleBox)]                  # noqa: E731
    assert names(win.dock_board) == ["Size", "Board outline", "Environment"]
    assert names(win.dock_sim)[:2] == ["Models", "Settings"]
    win.canvas.set_selection([("heater", 0)])
    win._on_canvas_selection([("heater", 0)])
    assert names(win.dock_inspector)[:2] == ["Heater", "Power"]
    # The Run button is above the boxes, outside them
    assert not any(b.isAncestorOf(win.solver_panel.run) for b in win.dock_sim.findChildren(CollapsibleBox))


def test_warning_titles_are_short_and_clean():
    """!
    @brief The title is the first clause of the warning; a designator prefix stays; a long clause is cut at a word.
    """
    assert checks.warning_title("U1: 9 vias under the footprint; the Lumped model is approximate here.") == "U1: 9 vias under the footprint"
    assert checks.warning_title("Imported copper at a cell above 1 mm: on 24 mm windows the faces read hot.") == "Imported copper at a cell above 1 mm"
    long = checks.warning_title("word " * 40)
    assert len(long) <= checks.TITLE_MAX + 1 and long.endswith("…")
    assert checks.warning_severity("this will not run") == "high" and checks.warning_severity("a note") == "note"


def test_the_accordion_lists_closed_rows_and_the_select_button_names_the_element(win, qtbot):
    """!
    @brief Rows start closed; an opened row shows its full text and 'Select heater U1'; the button selects the element; a stale list disables it.
    @param win MainWindow fixture.
    @param qtbot pytest-qt fixture.
    """
    cw = checks.CheckWarning("U1: first clause; the second clause is long")
    cw.kind, cw.index = "heater", 0
    acc = win.solver_panel.checks
    win.solver_panel.set_checks([cw])
    row = acc.rows[0]
    assert not row.is_open() and not row.text.isVisibleTo(row) and row.title == "U1: first clause"
    QTest.mouseClick(row.head, Qt.LeftButton)
    assert row.is_open() and row.text.isVisibleTo(row) and row.text.text() == str(cw)
    assert row.button.text() == f"Select heater {win.doc.problem.heaters[0].name}"
    win.canvas.set_selection([])
    row.button.click()
    assert win.canvas.selected_elements() == [("heater", 0)]
    acc.set_stale()
    assert not row.button.isEnabled()


def test_the_summary_has_the_box_and_the_on_screen_report_has_no_warning_lines(qtbot):
    """!
    @brief The Results summary shows its warnings in the Warnings box; the on-screen report ends with the pointer line; the saved report keeps every WARNING line.
    @param qtbot pytest-qt fixture.
    """
    from pcbthermal.gui.results_view import ResultsView
    prob = example_board()
    sim = simulate(prob, SolverOptions(models=("fvm", "lumped"), cell_mm=2.0))
    sim.warnings.extend(["first note: something", "second note will not run"])
    view = ResultsView("light")
    qtbot.addWidget(view)
    view.set_simulation(sim)
    n = len(sim.warnings)
    assert view.warnings.box.title() == f"Warnings ({n})" and len(view.warnings.rows) == n
    on_screen = view.report.toPlainText()
    assert "WARNING:" not in on_screen and f"({n} warnings: see the Warnings list above; the saved report keeps them.)" in on_screen
    assert sim.report().count("WARNING:") == n and "see the Warnings list above" not in sim.report()
    assert sim.to_text().count("WARNING:") == n


def test_layer_keys_step_pick_and_do_not_fire_in_a_text_field(win, qtbot):
    """!
    @brief L and Shift+L step through the layers round the end, 1 to N pick a layer, 0 shows All layers in Temperature, a missing layer says so; typed into a field they do nothing.
    @param win MainWindow fixture.
    @param qtbot pytest-qt fixture.
    """
    from pcbthermal.gui import layerchoice
    n = win.doc.problem.board.layers
    win.tabs.setCurrentIndex(0)
    win.canvas.setFocus()
    shown = lambda: win.layer_combo.currentData()                                                # noqa: E731
    assert shown() == 0
    QTest.keyClick(win.canvas, Qt.Key_L)
    assert shown() == 1
    for _ in range(n - 1):
        QTest.keyClick(win.canvas, Qt.Key_L)
    assert shown() == 0                                                                          # Round the end
    QTest.keyClick(win.canvas, Qt.Key_L, Qt.ShiftModifier)
    assert shown() == n - 1                                                                      # Shift+L goes back, round the start
    QTest.keyClick(win.canvas, Qt.Key_2)
    assert shown() == 1 and win.canvas.layer == 1
    QTest.keyClick(win.canvas, Qt.Key_9)
    assert shown() == 1 and "no layer 9" in win.statusBar().currentMessage()
    QTest.keyClick(win.canvas, Qt.Key_0)
    assert "Temperature tab only" in win.statusBar().currentMessage()                            # The editor lists no All layers
    # Temperature tab with a result: 0 is All layers
    sim = simulate(win.doc.problem, SolverOptions(models=("fvm",), cell_mm=2.0))
    win.sim = sim
    win.results.set_simulation(sim)
    win.tabs.setCurrentIndex(3)
    win.results.tabs.setCurrentWidget(win.results.temp)
    win._apply_layer()
    QTest.keyClick(win.canvas, Qt.Key_0)
    assert shown() == layerchoice.ALL_LAYERS
    # Typed into a line edit or a number box the keys are characters, not commands
    for field in (QLineEdit(win), QDoubleSpinBox(win)):
        field.setGeometry(0, 0, 80, 24)
        field.show()
        field.raise_()
        field.setFocus()
        qtbot.waitUntil(lambda f=field: f.hasFocus())
        before = shown()
        QTest.keyClicks(field, "l3")
        assert shown() == before
        field.deleteLater()


def test_the_layer_keys_are_unique_and_in_the_key_tables(win):
    """!
    @brief No other action carries L, Shift+L or a digit, and both key tables name them.
    @param win MainWindow fixture.
    """
    from pcbthermal.gui.help import GUIDE
    from tests.test_shortcuts import _all_actions, _mentions, _plain
    for key in ["L", "Shift+L"] + [str(d) for d in range(10)]:
        bound = [a for a in _all_actions(win) if any(k.toString() == key for k in a.shortcuts())]
        assert len(bound) == 1, (key, [a.text() for a in bound])
    for table in (_plain(win.SHORTCUTS_HTML), _plain(GUIDE.read_text(encoding="utf-8"))):
        assert _mentions(table, "L") and _mentions(table, "Shift+L")


def test_the_export_writes_the_map_as_the_display_panel_draws_it(win, qtbot, tmp_path, monkeypatch):
    """!
    @brief Export results to a folder passes the Display choice (underlay copper, view, colour map) to the maps: the files differ from the plain export and the choice reaches plots.
    @param win MainWindow fixture.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @param monkeypatch pytest fixture.
    """
    from PySide6.QtWidgets import QFileDialog
    sim = simulate(win.doc.problem, SolverOptions(models=("fvm",), cell_mm=2.0))
    win.sim = sim
    win.display.kind = "copper"
    win.display.cmap = "viridis"
    seen = {}
    real_save = sim.save
    monkeypatch.setattr(sim, "save", lambda d, plots=True, view=None, cmap="inferno": seen.update(view=view, cmap=cmap) or real_save(d, plots, view, cmap))
    out = tmp_path / "export"
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", staticmethod(lambda *a, **k: str(out)))
    win.export_results()
    assert seen["view"] is not None and seen["view"].show_copper and seen["view"].underlay == "copper" and seen["cmap"] == "viridis"
    assert (out / "fields_fvm.png").stat().st_size > 1000
    plain = tmp_path / "plain"
    sim.save(str(plain))
    assert (out / "fields_fvm.png").read_bytes() != (plain / "fields_fvm.png").read_bytes()
