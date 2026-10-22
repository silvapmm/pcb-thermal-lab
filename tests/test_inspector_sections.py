"""!
@file test_inspector_sections.py
@brief The Properties panel groups the fields of each element in titled boxes; a manual-input heatsink is typed as h or as theta_SA; the simple stack-up lives in the Stack-up tab.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("pytestqt")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QAbstractSpinBox, QComboBox, QGroupBox

from pcbthermal.examples import example_block_board, example_board
from pcbthermal.gui.document import Document
from pcbthermal.gui.main_window import MainWindow
from tests.test_tooltips import missing


@pytest.fixture
def win(qtbot, tmp_path):
    w = MainWindow(Document(), QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    qtbot.addWidget(w)
    w.resize(1500, 900)
    w.show()
    w._load_problem(example_board(), "sections")
    return w


def titles(win):
    return [g.title() for g in win.inspector.form_host.findChildren(QGroupBox)]


def select(win, kind, i=0):
    win.canvas.set_selection([(kind, i)])
    win._on_canvas_selection([(kind, i)])


def test_boxes_of_every_element(win):
    select(win, "zone")
    assert titles(win) == ["Copper", "Position and size"]
    select(win, "heater")
    assert titles(win) == ["Part", "Junction", "Package top: junction to case", "Interface: package top to heatsink", "Heatsink on the package", "Position and size"]
    select(win, "via")
    assert titles(win) == ["Via"]
    select(win, "heatsink")
    assert titles(win) == ["Cooling model", "Manual input", "Position and size"]
    win._load_problem(example_block_board(), "block")
    select(win, "heatsink")
    assert titles(win) == ["Cooling model", "Metal block", "Interface: board to block", "Fins (optional)",
                           "Extra cooling of the exposed surface (optional)", "Position and size"]
    assert not missing(win.inspector.form_host, "block boxes")


def test_manual_input_is_h_or_theta_sa(win):
    select(win, "heatsink")
    hs = lambda: win.doc.problem.heatsinks[0]                                                    # noqa: E731
    form = lambda: win.inspector.form_host                                                       # noqa: E731
    how = next(c for c in form().findChildren(QComboBox) if c.itemText(0).startswith("Heat transfer coefficient"))
    assert not [s for s in form().findChildren(QAbstractSpinBox) if s.toolTip().startswith("Heatsink resistance")]      # Only the h field
    how.setCurrentIndex(1)
    spin = next(s for s in form().findChildren(QAbstractSpinBox) if s.toolTip().startswith("Heatsink resistance"))
    assert not [s for s in form().findChildren(QAbstractSpinBox) if s.toolTip().startswith("Extra heat transfer")]       # Only the θSA field
    spin.setValue(2.0)
    from pcbthermal.geometry import polygon_area
    assert hs().h_extra == pytest.approx(1.0 / (2.0 * polygon_area(hs().polygon)), rel=1e-3)
    assert not missing(form(), "manual theta")
    select(win, "zone")                                                                          # Elsewhere and back: the choice is remembered
    select(win, "heatsink")
    assert any(s.toolTip().startswith("Heatsink resistance") for s in form().findChildren(QAbstractSpinBox))


def test_simple_stackup_fields_are_in_the_stackup_tab(win):
    page, bp = win.stackup_page, win.board_panel
    assert page.isAncestorOf(bp.thickness) and page.isAncestorOf(bp.copper) and page.isAncestorOf(bp.layers)
    assert page.isAncestorOf(bp.k_th) and page.isAncestorOf(bp.laminate) and page.isAncestorOf(bp.plating)
    assert not bp.isAncestorOf(bp.thickness) and bp.isAncestorOf(bp.width) and bp.isAncestorOf(bp.h_top)
    page.mode.setCurrentIndex(1)                                                                  # Advanced: thickness and copper are read-only, materials of copper stay
    assert not bp.thickness.isEnabled() and bp.k_cu.isEnabled()
    page.mode.setCurrentIndex(0)
    assert bp.thickness.isEnabled()


def tmax(win, model="fvm"):
    from pcbthermal import SolverOptions, simulate
    return simulate(win.doc.problem, SolverOptions(models=(model,), cell_mm=2.0)).results[model].t_max


def test_values_typed_in_the_new_places_change_the_result_sensibly(win):
    bp = win.board_panel
    base = tmax(win)
    assert base == pytest.approx(85.34, abs=0.05)                              # The same number as before the reorganisation (cell 2 mm)
    bp.copper.setValue(70.0)                                                   # Copper per layer, now in the Stack-up tab: twice the copper spreads better
    assert tmax(win) < base - 3.0
    bp.copper.setValue(35.0)
    assert tmax(win) == pytest.approx(base, abs=1e-6)
    bp.ambient.setValue(35.0)                                                  # Ambient +10 K with typed coefficients moves every temperature by 10 K
    assert tmax(win) == pytest.approx(base + 10.0, abs=1e-6)
    bp.ambient.setValue(25.0)
    bp.k_th.setValue(3.0)                                                      # A better dielectric across the board cannot make it hotter
    assert tmax(win) <= base + 1e-9
    bp.k_th.setValue(0.3)
    # A heatsink typed as h or as θSA is the same physics
    select(win, "heatsink")
    hs = win.doc.problem.heatsinks[0]
    t_h = tmax(win)
    how = next(c for c in win.inspector.form_host.findChildren(QComboBox) if c.itemText(0).startswith("Heat transfer coefficient"))
    how.setCurrentIndex(1)
    spin = next(s for s in win.inspector.form_host.findChildren(QAbstractSpinBox) if s.toolTip().startswith("Heatsink resistance"))
    from pcbthermal.geometry import polygon_area
    spin.setValue(1.0 / (hs.h_extra * polygon_area(hs.polygon)))               # The same heatsink expressed as θSA
    assert tmax(win) == pytest.approx(t_h, abs=1e-6)
    spin.setValue(spin.value() / 2.0)                                          # Half the resistance: a stronger heatsink is cooler
    assert tmax(win) < t_h


def test_direct_contact_is_cooler_than_a_gap_pad_under_a_metal_block(win):
    win._load_problem(example_block_board(), "block")
    select(win, "heatsink")
    t_pad = tmax(win)                                                          # 5 K cm2/W gap pad
    combo = next(c for c in win.inspector.form_host.findChildren(QComboBox) if c.itemText(0).startswith("Interface material"))
    combo.setCurrentIndex(combo.findText("Direct contact", __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.MatchStartsWith))
    hs = win.doc.problem.heatsinks[0]
    assert hs.interface_resistance() == 0.0
    assert tmax(win) < t_pad
