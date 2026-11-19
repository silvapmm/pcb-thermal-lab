#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_cut_slider_narrow_window.py
@brief The Cut slider of the Results Profiles tab stays usable in a narrow window (900 x 700 and 800 x 600 with both docks open): it was squeezed to its handle (23 px).
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("pytestqt")

from PySide6.QtCore import QPoint, QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QSlider, QStyle, QStyleOptionSlider

from pcbthermal.api import SolverOptions, simulate
from pcbthermal.examples import example_board
from pcbthermal.gui.document import Document
from pcbthermal.gui.main_window import TAB_RESULTS, MainWindow
from pcbthermal.gui.results_view import PlotTab

MIN_USABLE_PX = 50              # A slider narrower than this cannot be dragged to a chosen position


@pytest.fixture(scope="module")
def sim():
    """!
    @brief One FVM run of the example board at a 2 mm cell.
    @return The api result of `simulate`.
    """
    return simulate(example_board(), SolverOptions(cell_mm=2.0, models=("fvm",)))


def _profiles_window(qtbot, tmp_path, sim, size):
    """!
    @brief A main window of the given size with the Profiles tab shown, docks open, private settings.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder (the settings file lives there).
    @param sim Simulation result shown.
    @param size Window size (width, height) in pixels.
    @return The MainWindow.
    """
    win = MainWindow(Document(), QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    qtbot.addWidget(win)
    win.resize(*size)
    win.show()
    win._on_done(sim)
    win.tabs.setCurrentIndex(TAB_RESULTS)
    win.results.tabs.setCurrentWidget(win.results.profile)
    qtbot.wait(200)
    assert all(d.isVisible() and not d.isFloating() for d in (win.dock_board, win.dock_sim))
    return win


def _handle_centre(slider):
    """!
    @brief Centre of the handle of a horizontal slider, in the coordinates of the slider.
    @param slider The QSlider.
    @return QPoint.
    """
    opt = QStyleOptionSlider()
    opt.initFrom(slider)
    opt.orientation = Qt.Horizontal
    opt.minimum, opt.maximum, opt.sliderPosition, opt.sliderValue = slider.minimum(), slider.maximum(), slider.value(), slider.value()
    opt.subControls = QStyle.SC_SliderHandle
    return slider.style().subControlRect(QStyle.CC_Slider, opt, QStyle.SC_SliderHandle, slider).center()


@pytest.mark.parametrize("size", [(900, 700), (800, 600)])
def test_the_cut_slider_is_usable_in_a_narrow_window(qtbot, tmp_path, sim, size):
    """!
    @brief In a narrow window the slider is wide enough to drag, lies inside the tab, its position text is shown whole, and the keyboard and the mouse move it.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @param sim Simulation of the example board.
    @param size Window size in pixels.
    """
    win = _profiles_window(qtbot, tmp_path, sim, size)
    tab: PlotTab = win.results.profile
    s: QSlider = tab.pos
    assert s.isVisible() and s.width() >= MIN_USABLE_PX, (size, s.width())
    # Fully inside the tab, nothing of it (or of its position text) beyond the edge
    for w in (s, tab.pos_label):
        r = w.rect().translated(w.mapTo(tab, QPoint(0, 0)))
        assert tab.rect().contains(r), (size, w, r, tab.rect())
    assert tab.pos_label.width() >= tab.pos_label.fontMetrics().horizontalAdvance(tab.pos_label.text())
    # Keyboard: the arrow keys move it
    s.setFocus()
    s.setValue(500)
    QTest.keyClick(s, Qt.Key_Right)
    assert s.value() > 500
    QTest.keyClick(s, Qt.Key_Left)
    QTest.keyClick(s, Qt.Key_Left)
    assert s.value() < 500
    # Mouse: dragging the handle to the right raises the value, the value shows in the label
    s.setValue(200)
    before = s.value()
    c = _handle_centre(s)
    QTest.mousePress(s, Qt.LeftButton, Qt.NoModifier, c)
    QTest.mouseMove(s, c + QPoint(30, 0))
    QTest.mouseRelease(s, Qt.LeftButton, Qt.NoModifier, c + QPoint(30, 0))
    assert s.value() > before + 100, (before, s.value())
    assert tab.pos_label.text()


def test_the_wide_layout_of_the_controls_is_unchanged_at_1200_x_800(qtbot, tmp_path, sim):
    """!
    @brief At 1200 x 800 the whole control row (Cut, direction, slider, position, overlay box) stays on one line, as before the fix.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @param sim Simulation of the example board.
    """
    win = _profiles_window(qtbot, tmp_path, sim, (1200, 800))
    tab = win.results.profile
    assert tab._controls.indexOf(tab.cut_overlay) >= 0 and tab._controls.indexOf(tab.pos) >= 0
    assert tab._controls2.count() == 0 and tab._controls3.count() == 0
    assert tab.pos.width() >= 100
    # Narrow and wide again: the row comes back
    win.resize(900, 700)
    qtbot.wait(150)
    assert tab._controls.indexOf(tab.pos) < 0 and tab._controls3.indexOf(tab.pos) >= 0
    win.resize(1200, 800)
    qtbot.wait(150)
    assert tab._controls.indexOf(tab.pos) >= 0 and tab._controls3.count() == 0
