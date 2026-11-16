#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_accessibility_names.py
@brief Screen-reader names and keyboard order: every value control the user can reach has a name (its own, or the label of its row), and Tab goes through
       the Properties fields right after the dock (review of the window: 6 accessible names in the whole interface; the fields of a rebuilt form came after the tool bar).
"""

import pytest

pytest.importorskip("pytestqt")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QWidget

from pcbthermal import SolverOptions, simulate
from pcbthermal.examples import example_board
from pcbthermal.gui.a11y import FIELDS
from tests.test_gui_stress import load, popups, win  # noqa: F401  (fixtures and helpers)


def _unnamed(root):
    """!
    @brief The visible, enabled value controls under `root` with no accessible name and no label whose buddy they are.
    @param root A QWidget.
    @return list of str descriptions.
    """
    buddies = {id(lab.buddy()) for lab in root.findChildren(QLabel) if lab.buddy() is not None}
    out = []
    for w in root.findChildren(QWidget):
        if not isinstance(w, FIELDS) or not w.isVisibleTo(root) or isinstance(w.parentWidget(), FIELDS):
            continue
        if w.accessibleName() or id(w) in buddies:
            continue
        out.append(f"{type(w).__name__} tip={w.toolTip()[:50]!r}")
    return out


def test_every_value_control_of_the_window_has_a_name(win):
    """!
    @brief Board, Simulation and Properties docks (a heater selected), the tool bar and every Results tab after a run.
    @param win Main window fixture.
    """
    load(win, example_board())
    win.canvas.set_selection([("heater", 0)])
    win._on_canvas_selection([("heater", 0)])
    win._on_done(simulate(win.doc.problem, SolverOptions(cell_mm=2.0)))
    missing = []
    for i in range(win.results.tabs.count()):
        win.results.tabs.setCurrentIndex(i)
        QApplication.processEvents()
        missing += [f"Results/{win.results.tabs.tabText(i)}: {m}" for m in _unnamed(win.results.tabs.widget(i))]
    for d in (win.dock_board, win.dock_sim, win.dock_inspector):
        missing += [f"{d.windowTitle()}: {m}" for m in _unnamed(d)]
    missing += [f"tool bar: {m}" for m in _unnamed(win.toolbar)]
    assert not missing, "\n".join(sorted(set(missing)))


def test_the_stack_up_and_power_profile_pages_and_the_display_panel_name_their_fields(win):
    """!
    @brief The pages of the other main tabs and the Display popover are walked too (review of branch C: the Stack-up bar, the 'Repeats every' row and the
           opacity box had no name, and the test above did not visit them).
    @param win Main window fixture.
    """
    from pcbthermal.examples import example_profile_board
    from pcbthermal.gui.main_window import TAB_PROFILE, TAB_STACKUP

    load(win, example_profile_board())
    missing = []
    for tab, page in ((TAB_STACKUP, win.stackup_page), (TAB_PROFILE, win.profile_page)):
        win.tabs.setCurrentIndex(tab)
        QApplication.processEvents()
        missing += [f"{win.tabs.tabText(tab)}: {m}" for m in _unnamed(page)]
    missing += [f"Display: {m}" for m in _unnamed(win.display_popover)]
    assert not missing, "\n".join(sorted(set(missing)))


def test_tab_goes_through_the_properties_fields_before_the_tool_bar(win):
    """!
    @brief With a heater selected, the first fields after the Properties dock in the keyboard order are its own fields, not the tool bar boxes.
    @param win Main window fixture.
    """
    load(win, example_board())
    win.canvas.set_selection([("heater", 0)])
    win._on_canvas_selection([("heater", 0)])
    QApplication.processEvents()
    from PySide6.QtWidgets import QScrollArea

    first = win.inspector._focus_chain()[0]
    w = win.inspector
    while not isinstance(w, QScrollArea):                       # The dock's scroll area: the stop of the keyboard order just before the fields
        w = w.parentWidget()
    seen = []
    for _ in range(400):
        w = w.nextInFocusChain()
        if w.focusPolicy() & Qt.TabFocus and w.isVisible():
            seen.append(w)
            if len(seen) == 1:
                break
    assert seen and seen[0] is first, (type(seen[0]).__name__, seen[0].accessibleName())


def test_the_dialogs_name_their_value_controls(win, qtbot):
    """!
    @brief Preferences (every page), the Power calculator and the empty Gerber import window: every value control has a name.
    @param win Main window fixture.
    @param qtbot pytest-qt fixture.
    """
    from pcbthermal.gui.calculator import PowerCalculator
    from pcbthermal.gui.import_window import ImportBoardWindow
    from pcbthermal.gui.preferences import PreferencesDialog

    load(win, example_board())
    missing = []
    d = PreferencesDialog(win)
    qtbot.addWidget(d)
    d.show()
    for i in range(d.sections.count()):
        d.sections.setCurrentRow(i)
        QApplication.processEvents()
        missing += [f"Preferences/{d.sections.item(i).text()}: {m}" for m in _unnamed(d)]
    d.close()
    c = PowerCalculator(win.doc, win)
    qtbot.addWidget(c)
    c.show()
    QApplication.processEvents()
    missing += [f"Calculator: {m}" for m in _unnamed(c)]
    c.close()
    w = ImportBoardWindow(win)
    qtbot.addWidget(w)
    w.show()
    QApplication.processEvents()
    missing += [f"Import: {m}" for m in _unnamed(w)]
    w.close()
    assert not missing, "\n".join(sorted(set(missing)))
