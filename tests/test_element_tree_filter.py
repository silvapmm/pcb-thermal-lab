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
