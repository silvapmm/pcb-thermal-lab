#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_enter_focus.py
@brief Enter in a Properties field commits the typed number and the keyboard focus stays in that field, also right after a layer change and when the element shown in the
       Properties panel is on a layer other than the one drawn (the canvas rebuild after the edit used to report an empty selection and the form, with its focus, was lost).
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("pytestqt")

from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDoubleSpinBox

from pcbthermal.examples import example_board
from pcbthermal.gui.document import Document
from pcbthermal.gui.main_window import MainWindow


@pytest.fixture
def win(qtbot, tmp_path):
    """!
    @brief A main window with the example board, heater U2 moved to layer 3.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @return MainWindow
    """
    w = MainWindow(Document(), QSettings(str(tmp_path / "s.ini"), QSettings.IniFormat))
    qtbot.addWidget(w)
    w.resize(1500, 900)
    w.show()
    w._load_problem(example_board(), "enter")
    w.doc.set_props("heater", 1, layer=2, merge=False)
    return w


def _type_power_and_enter(win, qtbot):
    """!
    @brief Type 7 in the first number field of the Properties form of the selected heater and press Enter.
    @param win MainWindow.
    @param qtbot pytest-qt fixture.
    @return QWidget that has the focus afterwards.
    """
    spins = [s for s in win.inspector.form_host.findChildren(QDoubleSpinBox) if s.isEnabled() and s.isVisibleTo(win.inspector.form_host)]
    spins[0].setFocus(Qt.TabFocusReason)
    QTest.keyClicks(QApplication.focusWidget(), "7")
    QTest.keyClick(QApplication.focusWidget(), Qt.Key_Return)
    qtbot.wait(50)
    return QApplication.focusWidget()


def _select_heater_on_canvas(win, index):
    """!
    @brief Select a heater the way a click does (the canvas item, which emits the selection).
    @param win MainWindow.
    @param index Heater index.
    @return None
    """
    item = next(i for i in win.canvas.scene().items() if getattr(i, "kind", None) == "heater" and i.index == index)
    win.canvas.scene().clearSelection()
    item.setSelected(True)


@pytest.mark.parametrize("how", ["combo", "key", "step"])
def test_enter_after_a_layer_change_keeps_the_focus_in_the_field(win, qtbot, how):
    win.layer_combo.setCurrentIndex(1)
    {"combo": lambda: win.layer_combo.setCurrentIndex(2), "key": lambda: win._show_layer_key(3), "step": lambda: win._step_layer(1)}[how]()
    assert win.canvas.layer == 2
    _select_heater_on_canvas(win, 1)
    focus = _type_power_and_enter(win, qtbot)
    assert isinstance(focus, QDoubleSpinBox) and win.inspector.form_host.isAncestorOf(focus)
    assert win.doc.problem.heaters[1].power == pytest.approx(7.0)


def test_enter_in_a_field_of_an_element_on_another_layer_keeps_the_form_and_the_focus(win, qtbot):
    win.canvas.set_layer(0)
    win.inspector.set_selection([("heater", 1)])                              # Shown in Properties, not selectable on the drawn layer 1
    assert win.canvas.layer == 0
    focus = _type_power_and_enter(win, qtbot)
    assert win.doc.problem.heaters[1].power == pytest.approx(7.0)
    assert isinstance(focus, QDoubleSpinBox) and win.inspector.form_host.isAncestorOf(focus)
    assert win.inspector.selection == [("heater", 1)]


# ---------------------------------------------------------------------------------------------------------------- review: the paths that refresh the Properties form
# The canvas no longer reports an unchanged selection after a rebuild, so every path below must refresh the form or the selection through its own route (the
# Inspector listens to Document.changed itself; a changed canvas selection is still reported).


def _list_select(win, items):
    """!
    @brief Select elements in the element tree the way a click does (the tree emits the request).
    @param win MainWindow.
    @param items List of (kind, index).
    @return None
    """
    t = win.elements.tree
    t.clearSelection()
    for a in range(t.topLevelItemCount()):
        top = t.topLevelItem(a)
        for c in range(top.childCount()):
            if top.child(c).data(0, Qt.UserRole) in items:
                top.child(c).setSelected(True)


def _shown_power(win):
    """!
    @brief The power shown by the Properties form of the selected heater.
    @param win MainWindow.
    @return float Value of the first enabled number field (the power).
    """
    return [s for s in win.inspector.form_host.findChildren(QDoubleSpinBox) if s.isEnabled() and s.isVisibleTo(win.inspector.form_host)][0].value()


@pytest.mark.parametrize("other_layer", [False, True])
def test_undo_and_redo_refresh_the_properties_form(win, qtbot, other_layer):
    if other_layer:
        win.canvas.set_layer(0)
        win.inspector.set_selection([("heater", 1)])
    else:
        _select_heater_on_canvas(win, 0)
    i = win.inspector.selection[0][1]
    before = win.doc.problem.heaters[i].power
    _type_power_and_enter(win, qtbot)
    assert _shown_power(win) == pytest.approx(7.0)
    win.doc.stack.undo()
    assert _shown_power(win) == pytest.approx(before) and win.inspector.selection == [("heater", i)]
    win.doc.stack.redo()
    assert _shown_power(win) == pytest.approx(7.0)


@pytest.mark.parametrize("other_layer", [False, True])
def test_a_value_set_elsewhere_refreshes_the_properties_form(win, qtbot, other_layer):
    """The Power Calculator's Use and the Power profile page write a heater through Document.set_props, not through the form."""
    if other_layer:
        win.canvas.set_layer(0)
        win.inspector.set_selection([("heater", 1)])
    else:
        _select_heater_on_canvas(win, 0)
    i = win.inspector.selection[0][1]
    win.doc.set_props("heater", i, power=3.25)
    assert _shown_power(win) == pytest.approx(3.25) and win.inspector.selection == [("heater", i)]


def test_a_selection_that_is_no_longer_drawn_is_still_cleared(win, qtbot):
    """A layer change (and a delete) changes the canvas selection, which is still reported: the form and the list follow."""
    _select_heater_on_canvas(win, 0)
    assert win.inspector.selection == [("heater", 0)]
    win.layer_combo.setCurrentIndex(1)
    assert win.inspector.selection == [] and win.elements.selected() == []
    win.layer_combo.setCurrentIndex(0)
    _select_heater_on_canvas(win, 0)
    win.doc.delete([("heater", 0)])
    assert win.inspector.selection == [] and win.elements.selected() == []


def test_a_selection_on_two_layers_survives_an_edit_made_elsewhere(win, qtbot):
    """Two heaters on two layers picked in the element tree: an edit made elsewhere used to cut the form and the list to the one drawn on the canvas."""
    _list_select(win, [("heater", 0), ("heater", 1)])
    assert sorted(win.inspector.selection) == [("heater", 0), ("heater", 1)]
    win.doc.set_props("heater", 0, power=9.0)
    assert sorted(win.inspector.selection) == [("heater", 0), ("heater", 1)]
    assert sorted(win.elements.selected()) == [("heater", 0), ("heater", 1)]


def test_duplicate_selects_the_copy_in_properties_and_in_the_list(win, qtbot):
    """Ctrl+D selected the copy on the board only: Properties and the list kept the original, so the next typed value changed the original."""
    _select_heater_on_canvas(win, 0)
    n = len(win.doc.problem.heaters)
    win.a_dup.trigger()
    assert win.canvas.selected_elements() == [("heater", n)]
    assert win.inspector.selection == [("heater", n)] and win.elements.selected() == [("heater", n)]
    original = win.doc.problem.heaters[0].power
    _type_power_and_enter(win, qtbot)
    assert win.doc.problem.heaters[n].power == pytest.approx(7.0) and win.doc.problem.heaters[0].power == pytest.approx(original)
