#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_ui_polish.py
@brief Menu key hints without a bare letter, and a robust first layout of the side docks.
"""
import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import QSettings
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QApplication, QMenu

from pcbthermal.gui.document import Document
from pcbthermal.gui.main_window import MainWindow


def _window(qtbot, ini, w=1480, h=900):
    """!
    @brief Build a window on a settings file and show it.
    @param qtbot pytest-qt fixture.
    @param ini Path of the INI settings file (str).
    @param w Window width in pixels.
    @param h Window height in pixels.
    @return The shown MainWindow.
    """
    win = MainWindow(Document(), QSettings(ini, QSettings.IniFormat))
    qtbot.addWidget(win)
    win.resize(w, h)
    win.show()
    return win


def test_no_menu_entry_shows_a_bare_letter(qtbot, tmp_path):
    """!
    @brief The menus show no shortcut hint made of one letter, and the keys G, Shift+G and T still toggle the views.
    @param qtbot pytest-qt fixture.
    @param tmp_path pytest temporary folder.
    """
    win = _window(qtbot, str(tmp_path / "a.ini"))
    for menu in win.menuBar().findChildren(QMenu):
        for a in menu.actions():
            text = a.shortcut().toString(QKeySequence.NativeText)
            assert not (len(text) == 1 and text.isalpha()), (a.text(), text)
    keys = {s.toString() for a in win.actions() for s in a.shortcuts()}
    assert {"G", "Shift+G", "T"} <= keys
    # The overlay key needs a result, so the toggling is checked with the solver grid (Shift+G)
    hidden = next(a for a in win.actions() if [s.toString() for s in a.shortcuts()] == ["Shift+G"])
    assert not win.a_sgrid.isChecked()
    hidden.trigger()
    assert win.a_sgrid.isChecked()
    hidden.trigger()
    assert not win.a_sgrid.isChecked()


def _docks_usable(win):
    """!
    @brief Assert that every side dock is visible and at least as wide as its fields need.
    @param win The MainWindow.
    """
    for d in (win.dock_board, win.dock_elements):
        assert d.isVisible() and d.width() >= win.DOCK_MIN_LEFT, (d.windowTitle(), d.width())
    for d in (win.dock_sim, win.dock_inspector):
        assert d.isVisible() and d.width() >= win.DOCK_MIN_RIGHT, (d.windowTitle(), d.width())


def test_first_start_has_usable_docks(qtbot, tmp_path):
    """!
    @brief A first launch with no saved settings, at the default and at a small window, shows every dock at its minimum width.
    @param qtbot pytest-qt fixture.
    @param tmp_path pytest temporary folder.
    """
    for n, (w, h) in enumerate(((1480, 900), (1100, 700))):
        win = _window(qtbot, str(tmp_path / f"fresh{n}.ini"), w, h)
        qtbot.waitUntil(lambda: win.dock_board.width() >= win.DOCK_MIN_LEFT, timeout=3000)
        QApplication.processEvents()
        _docks_usable(win)


def test_stale_saved_layout_is_replaced_by_the_default(qtbot, tmp_path):
    """!
    @brief A saved arrangement with collapsed dock sizes, or a state of an older version, opens with the default widths.
    @param qtbot pytest-qt fixture.
    @param tmp_path pytest temporary folder.
    """
    # Sizes saved while the docks were squeezed, with a state of the current version
    ini = str(tmp_path / "squeezed.ini")
    first = _window(qtbot, ini)
    qtbot.waitUntil(lambda: first.dock_board.width() >= 300, timeout=3000)
    s = QSettings(ini, QSettings.IniFormat)
    s.setValue("window_state", first.saveState(MainWindow.STATE_VERSION))
    s.setValue("dock_sizes", [90, 100, 300, 200, 300, 300])
    s.sync()
    first.close()
    win = _window(qtbot, ini)
    qtbot.waitUntil(lambda: win.dock_board.width() >= win.DOCK_MIN_LEFT, timeout=3000)
    _docks_usable(win)
    # A state written by an older version (no version number) is refused by restoreState
    ini2 = str(tmp_path / "old.ini")
    s2 = QSettings(ini2, QSettings.IniFormat)
    s2.setValue("window_state", first.saveState())
    s2.setValue("dock_sizes", [90, 100, 300, 200, 300, 300])
    s2.sync()
    win2 = _window(qtbot, ini2)
    qtbot.waitUntil(lambda: win2.dock_board.width() >= win2.DOCK_MIN_LEFT, timeout=3000)
    _docks_usable(win2)


@pytest.mark.parametrize("name", ["dark", "light"])
def test_warning_symbol_and_text_share_one_colour(qtbot, name):
    """!
    @brief In the Run panel list every character of an entry (symbol, bullet, link text) has the colour of the theme's alert token.
    @param qtbot pytest-qt fixture.
    @param name Theme name.
    """
    from PySide6.QtGui import QColor
    from pcbthermal.gui import theme as th
    from pcbthermal.gui.panels import WarningList

    class Warn(str):
        kind, index = "heater", 0

    th.apply_theme(QApplication.instance(), name)
    lst = WarningList()
    qtbot.addWidget(lst)
    for ws in ([Warn("one")], [Warn("one"), Warn("two")]):
        lst.set_warnings(ws)
        seen = set()
        block = lst.document().begin()
        while block.isValid():
            it = block.begin()
            while not it.atEnd():
                frag = it.fragment()
                if frag.text().strip() and "warnings" not in frag.text():
                    seen.add(frag.charFormat().foreground().color().name())
                it += 1
            block = block.next()
        assert seen == {QColor(th.colors(name)["alert"]).name()}, seen
