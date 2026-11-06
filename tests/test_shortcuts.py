#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_shortcuts.py
@brief Keyboard shortcuts of the main window: no key sequence is bound to two different actions, and the key tables (Keyboard shortcuts box, user guide) name the real keys of the View menu.
"""

import os
import re
from collections import defaultdict

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("pytestqt")

from PySide6.QtCore import QSettings
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QWidget

from pcbthermal.gui.document import Document
from pcbthermal.gui.help import GUIDE
from pcbthermal.gui.main_window import MainWindow

## Key sequences that two different actions may share on purpose: none. A second key for the SAME action (Redo: Ctrl+Shift+Z and
#  Ctrl+Y; Zoom in: Ctrl++ and Ctrl+=) is not a clash and needs no entry; add one here, with the reason, only for a real exception.
ALLOWED_SHARED = {}


@pytest.fixture
def win(qtbot, tmp_path):
    """!
    @brief A main window on the offscreen platform.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder for the settings file.
    @return MainWindow.
    """
    w = MainWindow(Document(), QSettings(str(tmp_path / "test.ini"), QSettings.IniFormat))
    qtbot.addWidget(w)
    return w


def _all_actions(win):
    """!
    @brief Every QAction reachable from the window (menus, tool bar, tab actions, docks, canvas and every child widget).
    @param win The main window.
    @return list of unique QAction.
    """
    seen = {}
    for a in win.findChildren(QAction):
        seen[id(a)] = a
    for w in [win] + win.findChildren(QWidget):
        for a in w.actions():
            seen[id(a)] = a
    for d in win.findChildren(type(win.dock_board)):
        seen[id(d.toggleViewAction())] = d.toggleViewAction()
    return list(seen.values())


def _bindings(win):
    """!
    @brief Map each key sequence (portable text) to the set of action labels that carry it.
    @param win The main window.
    @return dict str -> set of str.
    """
    by_key = defaultdict(set)
    for a in _all_actions(win):
        for k in a.shortcuts():
            by_key[k.toString(QKeySequence.PortableText)].add(a.text().replace("&", "") or repr(a))
    return by_key


def test_no_key_sequence_on_two_actions(win):
    # A sequence on two actions makes Qt report an ambiguous shortcut and run neither
    clashes = {k: sorted(v) for k, v in _bindings(win).items() if len(v) > 1 and k not in ALLOWED_SHARED}
    assert not clashes, f"shortcut bound to different actions: {clashes}"


def test_a_prefix_of_another_sequence_is_not_shadowed(win):
    # "Ctrl+Shift+T" and "Ctrl+T" are different keys; only a chord prefix (one sequence the start of another) would shadow
    keys = [k for k in _bindings(win) if "," in k]
    for k in keys:
        assert not any(o != k and o.startswith(k + ",") for o in keys)


def test_the_same_action_is_not_in_a_menu_twice(win):
    for top in win.menuBar().actions():
        items = [a for a in top.menu().actions() if not a.isSeparator()]
        assert len(items) == len({id(a) for a in items}), top.text()
        labels = [a.text() for a in items]
        assert len(labels) == len(set(labels)), (top.text(), labels)


def test_every_key_is_listed_once_per_action(win):
    for a in _all_actions(win):
        keys = [k.toString() for k in a.shortcuts()]
        assert len(keys) == len(set(keys)), (a.text(), keys)


def _plain(text):
    """!
    @brief Strip HTML tags and blanks so that '<kbd>Ctrl</kbd>+<kbd>0</kbd>' reads 'Ctrl+0'.
    @param text HTML text.
    @return str.
    """
    text = re.sub(r"</t[dh]>|</tr>", " | ", text)             # Cell borders stay word borders
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", text))


def _mentions(table, key):
    """!
    @brief True when a key table names the key sequence (a bare letter only as a separate word).
    @param table Text of the table, tags removed.
    @param key Key sequence, for example 'Ctrl+0' or 'G'.
    @return bool.
    """
    if len(key) == 1:
        return re.search(rf"(^|[\s,/>]){re.escape(key)}($|[\s,/<|])", table) is not None
    return key.replace(" ", "") in table.replace(" ", "")


def test_the_key_tables_name_the_real_view_keys(win):
    shown = _plain(win.SHORTCUTS_HTML)
    guide = _plain(GUIDE.read_text(encoding="utf-8"))
    view = [a for a in win.menuBar().actions() if a.text() == "&View"][0].menu()
    missing = []
    for a in view.actions():
        for k in a.shortcuts():
            key = k.toString(QKeySequence.PortableText)
            for name, table in (("Keyboard shortcuts box", shown), ("user guide", guide)):
                if not _mentions(table, key):
                    missing.append((a.text(), key, name))
    assert not missing, missing


def test_the_key_tables_name_the_other_real_keys(win):
    # Edit, Simulation and Help keys too, and the tool keys
    shown = _plain(win.SHORTCUTS_HTML)
    guide = _plain(GUIDE.read_text(encoding="utf-8"))
    for key in ("Del", "Ctrl+D", "F5", "Ctrl+.", "F1", "Ctrl+Z", "Ctrl+Shift+Z", "Ctrl+Y", "Ctrl+1", "Ctrl+A", "Ctrl+,"):
        assert _mentions(shown, key) and _mentions(guide, key), key
    real = _bindings(win)
    for key in ("Ctrl+Shift+Z", "Ctrl+Y", "Ctrl+Z", "Ctrl+=", "Ctrl++", "Ctrl+-", "Ctrl+Q"):
        assert key in real, key


def _count(problem):
    """!
    @brief Number of drawn elements of a problem.
    @param problem The Problem.
    @return int.
    """
    return len(problem.heaters) + len(problem.zones) + len(problem.vias) + len(problem.heatsinks)


def test_delete_and_duplicate_keys_reach_the_actions_not_the_canvas(win, qtbot):
    # Del and Ctrl+D are window shortcuts: they act once through the action and the canvas never sees them, so the canvas does not handle them (its old
    # branches were dead code); Backspace, the Mac "delete" key, is the second key of the Delete action
    from PySide6.QtCore import QEvent, QObject, Qt
    from PySide6.QtTest import QTest

    from pcbthermal.examples import example_board

    win.show()
    win.activateWindow()
    qtbot.waitExposed(win)
    win._load_problem(example_board(), "example")
    qtbot.wait(20)                                                          # Let the scene be rebuilt before items are selected
    seen = []

    class Spy(QObject):
        """!
        @brief Records the key presses delivered to the canvas.
        """

        def eventFilter(self, obj, event):
            """!
            @brief Record a key press of the canvas.
            @param obj Watched object.
            @param event Event.
            @return bool False (the event goes on).
            """
            if event.type() == QEvent.KeyPress:
                seen.append(event.key())
            return False

    spy = Spy()
    win.canvas.installEventFilter(spy)
    win.canvas.setFocus()

    def select_one():
        """!
        @brief Select the first selectable item of the canvas.
        @return None.
        """
        win.canvas.scene().clearSelection()
        [i for i in win.canvas.scene().items() if i.flags() & i.GraphicsItemFlag.ItemIsSelectable][0].setSelected(True)
        qtbot.wait(5)
        assert win.canvas.selected_elements()

    n = _count(win.doc.problem)
    select_one()
    QTest.keyClick(win.canvas, Qt.Key_D, Qt.ControlModifier)
    assert _count(win.doc.problem) == n + 1 and Qt.Key_D not in seen         # Duplicated once, by the action
    select_one()
    QTest.keyClick(win.canvas, Qt.Key_Delete)
    assert _count(win.doc.problem) == n and Qt.Key_Delete not in seen        # Deleted once, by the action
    select_one()
    QTest.keyClick(win.canvas, Qt.Key_Backspace)
    assert _count(win.doc.problem) == n - 1 and Qt.Key_Backspace not in seen # Deleted once, by the action (Backspace is its second key)


def test_the_tables_say_that_ctrl_is_command_on_macos(win):
    shown = _plain(win.SHORTCUTS_HTML)
    guide = _plain(GUIDE.read_text(encoding="utf-8"))
    for table in (shown, guide):
        assert "macOS" in table and "Command key" in table and "Backspace" in table


def test_delete_action_has_del_and_backspace_and_the_menu_shows_them(win):
    keys = [k.toString(QKeySequence.PortableText) for k in win.a_delete.shortcuts()]
    assert keys == ["Del", "Backspace"]
    assert win.a_delete in [a for top in win.menuBar().actions() for a in top.menu().actions()]
    assert "Backspace" in _plain(win.SHORTCUTS_HTML) and "Backspace" in _plain(GUIDE.read_text(encoding="utf-8"))


def test_dock_titles_say_settings_but_object_names_and_saved_layouts_are_kept(win, qtbot):
    from PySide6.QtWidgets import QDockWidget

    assert win.dock_board.windowTitle() == "Board settings" and win.dock_sim.windowTitle() == "Simulation settings"
    guide = GUIDE.read_text(encoding="utf-8")
    assert "Board settings dock" in guide and "Simulation settings dock" in guide
    # The object names are the keys of the saved window layouts: they must stay the old titles
    assert win.dock_board.objectName() == "Board" and win.dock_sim.objectName() == "Simulation"
    titles = [a.text() for top in win.menuBar().actions() if top.text().replace("&", "") == "View" for a in top.menu().actions()]
    assert "Board settings" in titles and "Simulation settings" in titles
    # A state saved by a program that named the docks "Board" and "Simulation" (the same object names) still restores
    win.show()
    qtbot.waitExposed(win)
    win.dock_sim.hide()                                                     # A visible change that the saved state must bring back
    state = win.saveState(win.STATE_VERSION)
    names = {d.objectName() for d in win.findChildren(QDockWidget)}
    assert {"Board", "Simulation", "Elements", "Properties"} <= names
    win.dock_sim.show()
    assert win.restoreState(state, win.STATE_VERSION) and win.dock_sim.isHidden()


def test_the_key_d_is_bound_once_to_display_settings_and_is_in_both_key_tables(win):
    """!
    @brief D opens the Display panel through one hidden window action; the keyboard box and the user guide name it.
    @param win MainWindow fixture.
    """
    bound = [a for a in _all_actions(win) if any(k.toString() == "D" for k in a.shortcuts())]
    assert len(bound) == 1 and bound[0].text() == "Display settings…"
    assert _mentions(_plain(win.SHORTCUTS_HTML), "D") and _mentions(_plain(GUIDE.read_text(encoding="utf-8")), "D")
