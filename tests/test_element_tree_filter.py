#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_element_tree_filter.py
@brief The filter field of the element tree: matching, selection kept, undo, Esc, Down, window letters never fired, speed on 1000 rows.
"""

import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("pytestqt")

from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest

from pcbthermal.examples import example_board
from pcbthermal import Project
from pcbthermal.api import default_options
from pcbthermal.gui.document import Document
from pcbthermal.gui.main_window import MainWindow
from pcbthermal.gui.panels import ElementList


def _rows(el):
    """!
    @brief Visible element rows.
    @param el ElementList.
    @return List of row texts of the visible children.
    """
    out = []
    for t in range(el.tree.topLevelItemCount()):
        top = el.tree.topLevelItem(t)
        if top.isHidden():
            continue
        out += [top.child(c).text(0) for c in range(top.childCount()) if not top.child(c).isHidden()]
    return out


@pytest.fixture
def win(qtbot, tmp_path):
    """!
    @brief Main window with the example board.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @return MainWindow.
    """
    w = MainWindow(Document(Project(problem=example_board(), options=default_options())), QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    qtbot.addWidget(w)
    w.show()
    return w


def test_filter_by_name_type_layer_and_case(win):
    el = win.elements
    total = len(_rows(el))
    assert total > 2
    el.filter.setText("VIA")                                         # Type word, upper case
    assert 0 < len(_rows(el)) < total
    for t in range(el.tree.topLevelItemCount()):
        top = el.tree.topLevelItem(t)
        assert top.isHidden() == ("via" not in top.text(0).lower())  # A group with no match is hidden
    el.filter.setText("zzz-no-such")
    assert _rows(el) == []
    el.filter.setText("")
    assert len(_rows(el)) == total


def test_filter_keeps_selection_and_survives_undo_and_edits(win):
    el = win.elements
    el.tree.topLevelItem(1).child(0).setSelected(True)
    sel = el.selected()
    el.filter.setText(el.tree.topLevelItem(1).child(0).text(0))
    assert el.selected() == sel
    n = win.doc.problem.heaters.__len__()
    win.doc.duplicate(sel)                                           # An edit while filtered: the filter is applied again
    assert win.elements.filter.text() != ""
    win.doc.stack.undo()
    assert len(win.doc.problem.heaters) == n
    assert "Filter" not in str(win.doc.problem.__dict__)         # The filter is not part of the project


def test_esc_clears_and_down_moves_to_first_match(win, qtbot):
    el = win.elements
    el.focus_filter()
    QTest.keyClicks(el.filter, "via")
    assert el.filter.text() == "via"
    QTest.keyClick(el.filter, Qt.Key_Down)
    assert el.tree.currentItem() is el._first_match()
    el.filter.setFocus()
    QTest.keyClick(el.filter, Qt.Key_Escape)
    assert el.filter.text() == ""


def test_window_letters_do_not_fire_while_typing_in_the_filter(win, qtbot):
    fired = []
    for name, act in (("M", win.a_model), ("D", win.a_display), ("T", win.a_overlay)):
        act.setEnabled(True)
        act.triggered.connect(lambda *_a, n=name: fired.append(n))
    win.activateWindow()
    qtbot.waitActive(win)
    win._focus_filter()
    qtbot.waitUntil(lambda: win.elements.filter.hasFocus())
    QTest.keyClicks(win.elements.filter, "mdtgl12")
    assert fired == []
    assert win.elements.filter.text() == "mdtgl12"


def test_ctrl_f_action_exists_and_focuses_the_field(win, qtbot):
    win.a_find.trigger()
    qtbot.waitUntil(lambda: win.elements.filter.hasFocus())
    assert "Ctrl+F" in win.SHORTCUTS_HTML


def test_filter_is_fast_on_1000_rows(qtbot):
    from pcbthermal.model import Problem
    pr = Problem.new(60, 40, layers=2)
    for i in range(1000):
        pr.add_via(1 + (i % 50), 1 + i // 50, 0.3)
    el = ElementList(Document(Project(problem=pr, options=default_options())))
    qtbot.addWidget(el)
    t0 = time.perf_counter()
    el.apply_filter("v12")
    dt = time.perf_counter() - t0
    assert 0 < len(_rows(el)) < 1000
    assert dt < 0.2, f"filter took {dt * 1000:.0f} ms"             # Target 50 ms; the margin is for a loaded machine
    print(f"filter 1000 rows: {dt * 1000:.1f} ms")


def test_backspace_and_delete_in_the_field_never_delete_an_element(win, qtbot):
    # Backspace is also a key of the window's Delete action: in the field it edits the text, never the board
    win.canvas.set_selection([("heater", 0)])
    win._on_canvas_selection([("heater", 0)])
    n = len(win.doc.problem.heaters)
    win.activateWindow()
    qtbot.waitActive(win)
    win._focus_filter()
    qtbot.waitUntil(lambda: win.elements.filter.hasFocus())
    QTest.keyClicks(win.elements.filter, "ab")
    QTest.keyClick(win.elements.filter, Qt.Key_Backspace)
    assert win.elements.filter.text() == "a"
    win.elements.filter.clear()
    for key in (Qt.Key_Backspace, Qt.Key_Delete):                 # Also with the field empty
        QTest.keyClick(win.elements.filter, key)
    assert len(win.doc.problem.heaters) == n


def test_ctrl_z_in_the_field_undoes_the_text_not_the_document(win, qtbot):
    # Decided: in a text field Ctrl+Z is the field's own undo, as in every field of the window; the document's undo stays in the Edit menu
    n = len(win.doc.problem.heaters)
    win.doc.duplicate([("heater", 0)])
    assert len(win.doc.problem.heaters) == n + 1
    win.activateWindow()
    qtbot.waitActive(win)
    win._focus_filter()
    qtbot.waitUntil(lambda: win.elements.filter.hasFocus())
    QTest.keyClicks(win.elements.filter, "via")
    QTest.keyClick(win.elements.filter, Qt.Key_Z, Qt.ControlModifier)
    assert win.elements.filter.text() == ""
    QTest.keyClick(win.elements.filter, Qt.Key_Z, Qt.ControlModifier)
    assert len(win.doc.problem.heaters) == n + 1


def test_every_window_letter_stays_in_the_field(win, qtbot):
    # The tool letters (S, Z, H, C, V, O, P) and the view letters (G, T, D, M, L and the digits, with or without Shift)
    fired = []
    for a in win.findChildren(type(win.a_find)):
        keys = [k.toString() for k in a.shortcuts()]
        if any(len(k) == 1 or k.startswith("Shift+") and len(k) == 7 for k in keys):
            a.setEnabled(True)
            a.triggered.connect(lambda *_a, t=a.text(): fired.append(t))
    win.activateWindow()
    qtbot.waitActive(win)
    win._focus_filter()
    qtbot.waitUntil(lambda: win.elements.filter.hasFocus())
    QTest.keyClicks(win.elements.filter, "szhcvopgtdml0123456789")
    QTest.keyClicks(win.elements.filter, "GL")
    assert fired == []
    assert win.elements.filter.text() == "szhcvopgtdml0123456789GL"


def test_clearing_the_filter_restores_the_open_and_closed_groups(qtbot):
    from pcbthermal.model import Problem
    pr = Problem.new(60, 40, layers=2)
    for i in range(30):                                              # More than 12 rows: the group starts closed
        pr.add_via(1 + i, 5, 0.3)
    pr.add_heater(1, 1.0, rect=(28, 18, 32, 22), name="U1")
    el = ElementList(Document(Project(problem=pr, options=default_options())))
    qtbot.addWidget(el)
    tops = {el.tree.topLevelItem(t).text(0).split(" (")[0]: el.tree.topLevelItem(t) for t in range(el.tree.topLevelItemCount())}
    vias = next(v for k, v in tops.items() if k.startswith("Via"))
    heaters = next(v for k, v in tops.items() if k.startswith("Heater"))
    heaters.setExpanded(False)                                       # Closed by the user
    before = (vias.isExpanded(), heaters.isExpanded())
    assert before == (False, False)
    el.filter.setText("v1")
    assert vias.isExpanded()                                         # Opened to show the matches
    el.filter.setText("")
    assert (vias.isExpanded(), heaters.isExpanded()) == before


def test_a_new_project_clears_the_filter(win):
    win.elements.filter.setText("U1")
    win.doc.new(50, 40, 2)
    assert win.elements.filter.text() == ""


def test_hint_for_no_match_and_for_a_hidden_selection(win):
    el = win.elements
    assert el.hint.isHidden()
    el.filter.setText("zzz-no-such")
    assert not el.hint.isHidden() and "No elements match" in el.hint.text()
    el.filter.setText("via")
    assert el.hint.isHidden()
    # An element selected on the board that the filter hides: the filter is kept and the line says so
    win.canvas.set_selection([("heater", 0)])
    win._on_canvas_selection([("heater", 0)])
    assert el.selected() == []                                       # Hidden rows are not offered to the tree's own actions
    assert not el.hint.isHidden() and "hidden by the filter" in el.hint.text()
    el.filter.setText("")
    assert el.hint.isHidden()
    assert el.selected() == [("heater", 0)]                          # Shown again as selected when the filter is cleared


def test_an_edit_while_filtered_keeps_a_hidden_selection(win):
    # The board selection is hidden by the filter; an edit rebuilds the tree, and clearing the filter must show it selected again
    el = win.elements
    el.filter.setText("via")
    win.canvas.set_selection([("heater", 0)])
    win._on_canvas_selection([("heater", 0)])
    win.doc.duplicate([("via", 0)])                                  # Any edit: the tree is rebuilt
    el.filter.setText("")
    assert ("heater", 0) in el.selected()
    assert win.canvas.selected_elements() == [("heater", 0)]
