#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_via_pick.py
@brief A click on the editor canvas selects the via whose centre is nearest, within a screen-pixel tolerance, also in a dense array under a zone and a part.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("pytestqt")

from PySide6.QtCore import QPoint, QPointF, QSettings, Qt
from PySide6.QtTest import QTest

from pcbthermal import Problem
from pcbthermal.gui.document import Document
from pcbthermal.gui.main_window import MainWindow

PITCH = 0.5      # mm: finer than a 6 px tolerance at low zoom, as on an imported board


@pytest.fixture
def win(qtbot, tmp_path):
    """!
    @brief Main window with a 20 x 20 mm board: a full zone, a part over the middle and a 3 x 3 array of 0.3 mm vias at 0.5 mm pitch.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder for the settings file.
    @return MainWindow.
    """
    pr = Problem.new(20.0, 20.0, layers=2)
    pr.add_full_copper()
    pr.add_heater(1, 1.0, rect=(8.0, 8.0, 12.0, 12.0), name="U1")
    for i in range(3):
        for j in range(3):
            pr.add_via(10.0 + (i - 1) * PITCH, 10.0 + (j - 1) * PITCH, 0.3)
    w = MainWindow(Document(), QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    qtbot.addWidget(w)
    w.resize(1200, 800)
    w.show()
    w._load_problem(pr, "vias")
    return w


def click(cv, x_mm, y_mm, dx=0, dy=0, mod=Qt.NoModifier):
    """!
    @brief Click on the viewport at a scene point plus a pixel offset.
    @param cv Canvas.
    @param x_mm X in mm.
    @param y_mm Y in mm.
    @param dx Pixel offset in x.
    @param dy Pixel offset in y.
    @param mod Keyboard modifier.
    """
    p = cv.mapFromScene(QPointF(x_mm, y_mm)) + QPoint(dx, dy)
    QTest.mouseClick(cv.viewport(), Qt.LeftButton, mod, p)


def selected_vias(win):
    """!
    @brief Indices of the selected vias.
    @param win Main window.
    @return Sorted list.
    """
    return sorted(i for k, i in win.canvas.selected_elements() if k == "via")


@pytest.mark.parametrize("zoom", [0.4, 1.0, 4.0, 16.0])
def test_each_via_of_the_array_is_picked_at_every_zoom(win, zoom):
    cv = win.canvas
    cv.fit()
    cv.scale(zoom, zoom)
    vias = win.doc.problem.vias
    for n, v in enumerate(vias):
        # A click 2 px off the centre: the nearest centre must win, not the neighbour that the shapes reach, nor the part or the zone below
        click(cv, v.x * 1000.0, v.y * 1000.0, dx=2, dy=-1)
        assert selected_vias(win) == [n], (zoom, n)
        assert [k for k, _ in cv.selected_elements()] == ["via"]


def test_via_wins_over_the_part_and_a_miss_selects_the_part(win):
    cv = win.canvas
    cv.fit()
    click(cv, 10.0, 10.0, dx=3)
    assert [k for k, _ in cv.selected_elements()] == ["via"]
    click(cv, 11.5, 11.5)                                           # Inside the part, far from every via
    assert [k for k, _ in cv.selected_elements()] == ["heater"]


def test_ctrl_click_still_adds_to_the_selection(win):
    cv = win.canvas
    cv.fit()
    vias = win.doc.problem.vias
    click(cv, vias[0].x * 1000.0, vias[0].y * 1000.0, dx=1)
    click(cv, vias[4].x * 1000.0, vias[4].y * 1000.0, dx=1, mod=Qt.ControlModifier)
    assert selected_vias(win) == [0, 4]
    click(cv, vias[0].x * 1000.0, vias[0].y * 1000.0, dx=1, mod=Qt.ControlModifier)   # Ctrl toggles it off
    assert selected_vias(win) == [4]
