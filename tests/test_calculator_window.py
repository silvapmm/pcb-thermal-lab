#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_calculator_window.py
@brief The Power Calculator window, opened from the Simulation menu of the main window: both routes (the board model run backwards, the datasheet formula), the result text, the
       band, "Use as the power of a part" with undo, the greyed-field rule, the Help button, and the calculator on an imported-copper board (the real RP2040 through the library
       variables, a synthetic imported board always).
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("pytestqt")

from PySide6.QtCore import QSettings

from pcbthermal import SolverOptions, simulate
from pcbthermal.examples import example_board
from pcbthermal.gui import calculator as calc
from pcbthermal.gui.document import Document
from pcbthermal.gui.import_session import ImportSession
from pcbthermal.gui.main_window import MainWindow
from tests.helpers.synthetic_board import make_board

REAL = os.environ.get("PCBT_REAL_BOARDS", "")


@pytest.fixture
def win(qtbot, tmp_path):
    """!
    @brief A main window with the example board at a 2 mm cell (the calculator reads the cell of the project).
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @return MainWindow
    """
    w = MainWindow(Document(), QSettings(str(tmp_path / "s.ini"), QSettings.IniFormat))
    qtbot.addWidget(w)
    w.resize(1400, 850)
    w.show()
    w._load_problem(example_board(), "example")
    w.doc.set_options(cell_mm=2.0)
    return w


@pytest.fixture
def opened(win, monkeypatch):
    """!
    @brief The calculator as the menu opens it: show_calculator runs, its modal exec is replaced by a recorder that keeps the dialog.
    @param win MainWindow.
    @param monkeypatch pytest fixture.
    @return list that receives the PowerCalculator opened.
    """
    seen = []
    monkeypatch.setattr(calc.PowerCalculator, "exec", lambda self: (seen.append(self), 0)[1])
    return seen


def _wait_result(qtbot, dlg):
    """!
    @brief Wait for the calculation process to deliver (a result or a message replaces "Calculating").
    @param qtbot pytest-qt fixture.
    @param dlg PowerCalculator.
    @return None
    """
    qtbot.waitUntil(lambda: dlg.use.isEnabled() or ("Calculating" not in dlg.result.text() and dlg.result.text() != ""), timeout=180000)


def test_the_menu_opens_the_calculator_with_the_heaters_of_the_project(win, opened, qtbot):
    win.a_calc.trigger()
    assert len(opened) == 1
    dlg = opened[0]
    qtbot.addWidget(dlg)
    assert dlg.windowTitle() == "Power Calculator" and dlg.tabs.count() == 2
    assert [dlg.heater.itemText(i) for i in range(dlg.heater.count())] == [h.name or f"Heater {i + 1}" for i, h in enumerate(win.doc.problem.heaters)]
    assert dlg.compute.isEnabled() and not dlg.use.isEnabled() and dlg.result.text() == ""
    assert dlg.band.isChecked() and dlg.design.isEnabled()
    assert dlg.theta.value() == pytest.approx(win.doc.problem.heaters[0].theta)       # the part's θ is the starting value
    dlg.band.setChecked(False)
    assert not dlg.design.isEnabled()                                                  # the board description only acts on the band


def test_the_greyed_fields_follow_the_measurement_point(win, opened, qtbot):
    win.show_calculator()
    dlg = opened[0]
    qtbot.addWidget(dlg)
    rule = {"ring": (False, False), "max": (False, False), "mean": (False, False), "junction": (True, False), "top": (True, True)}
    assert set(rule) == {k for _l, k, _t in calc.POINTS}
    for key, (theta_on, psi_on) in rule.items():
        dlg.point.setCurrentIndex(dlg.point.findData(key))
        assert dlg.theta.isEnabled() == theta_on and dlg.theta_label.isEnabled() == theta_on
        assert dlg.psi_jt.isEnabled() == psi_on and dlg.psi_label.isEnabled() == psi_on
        assert ("Greyed" in dlg.theta.toolTip()) == (not theta_on) and ("Greyed" in dlg.psi_jt.toolTip()) == (not psi_on)
    size = dlg.minimumSize()
    dlg.point.setCurrentIndex(dlg.point.findData("ring"))
    assert dlg.minimumSize() == size                                                   # the window does not change size when the point changes


def test_route_1_finds_the_power_writes_it_into_the_heater_and_undo_restores_it(win, opened, qtbot):
    truth = win.doc.problem.heaters[0].power
    row = simulate(win.doc.problem, SolverOptions(models=("fvm",), cell_mm=2.0)).heater_rows()[0]
    win.show_calculator()
    dlg = opened[0]
    qtbot.addWidget(dlg)
    dlg.band.setChecked(False)
    dlg.point.setCurrentIndex(dlg.point.findData("mean"))
    dlg.measured.setValue(row["t_mean"])
    dlg.ambient.setValue(win.doc.problem.board.ambient)
    win.doc.set_props("heater", 0, power=1.0, merge=False)                              # the unknown power
    n = win.doc.stack.count()
    dlg.compute.click()
    _wait_result(qtbot, dlg)
    text = dlg.result.text()
    assert dlg.out["power_w"] == pytest.approx(truth, rel=0.01) and "best_w" not in dlg.out
    assert "W</b>" in text and "reproduces" in text and "Board resistance" in text and "worst case" not in text
    assert dlg.selected_power() == pytest.approx(truth, rel=0.01)
    dlg.use.click()
    assert win.doc.problem.heaters[0].power == pytest.approx(truth, rel=0.01) and not dlg.use.isEnabled()
    assert win.doc.stack.count() == n + 1
    win.doc.stack.undo()
    assert win.doc.problem.heaters[0].power == 1.0                                      # one undo step
    win.doc.stack.redo()
    assert win.doc.problem.heaters[0].power == pytest.approx(truth, rel=0.01)
    dlg.close()


def test_route_1_band_best_nominal_worst_and_the_case_selector(win, opened, qtbot):
    truth = win.doc.problem.heaters[0].power
    row = simulate(win.doc.problem, SolverOptions(models=("fvm",), cell_mm=2.0)).heater_rows()[0]
    win.show_calculator()
    dlg = opened[0]
    qtbot.addWidget(dlg)
    dlg.point.setCurrentIndex(dlg.point.findData("mean"))
    dlg.measured.setValue(row["t_mean"])
    dlg.design.setCurrentIndex(dlg.design.findData("hand"))
    dlg.compute.click()
    _wait_result(qtbot, dlg)
    out = dlg.out
    assert out["best_w"] < out["power_w"] < out["worst_w"] and out["best_w"] < truth < out["worst_w"]
    assert "best case" in dlg.result.text() and "worst case" in dlg.result.text() and "Board description (hand)" in dlg.result.text()
    assert any(c.get("design") for c in out["contributions"]) and any(not c.get("design") for c in out["contributions"])
    for key, expect in (("best", out["best_w"]), ("nominal", out["power_w"]), ("worst", out["worst_w"])):
        dlg.case.setCurrentIndex(dlg.case.findData(key))
        assert dlg.selected_power() == pytest.approx(expect)
    dlg.case.setCurrentIndex(dlg.case.findData("best"))
    dlg.use.click()
    assert win.doc.problem.heaters[0].power == pytest.approx(out["best_w"])
    win.doc.stack.undo()
    assert win.doc.problem.heaters[0].power == pytest.approx(truth)
    dlg.close()


def test_route_1_junction_point_uses_the_theta_typed_in_the_window_only(win, opened, qtbot):
    stored = win.doc.problem.heaters[0].theta
    win.show_calculator()
    dlg = opened[0]
    qtbot.addWidget(dlg)
    dlg.band.setChecked(False)
    dlg.point.setCurrentIndex(dlg.point.findData("junction"))
    dlg.theta.setValue(5.0)
    dlg.measured.setValue(120.0)
    dlg.compute.click()
    _wait_result(qtbot, dlg)
    p5 = dlg.out["power_w"]
    assert "junction" in dlg.result.text()
    dlg.theta.setValue(20.0)                                                            # a larger θ for the same Tj means a smaller power
    dlg.compute.click()
    _wait_result(qtbot, dlg)
    assert dlg.out["power_w"] < p5
    assert win.doc.problem.heaters[0].theta == stored                                   # the θ of the window is for the calculation only
    dlg.close()


def test_a_temperature_below_the_ambient_is_a_message_and_the_window_survives(win, opened, qtbot):
    win.show_calculator()
    dlg = opened[0]
    qtbot.addWidget(dlg)
    dlg.band.setChecked(False)
    dlg.measured.setValue(dlg.ambient.value() - 5.0)
    dlg.compute.click()
    qtbot.waitUntil(lambda: "above the ambient" in dlg.result.text(), timeout=120000)
    assert dlg.compute.isEnabled() and not dlg.use.isEnabled()


def test_route_2_the_datasheet_formula_and_its_use_button(win, opened, qtbot):
    win.show_calculator()
    dlg = opened[0]
    qtbot.addWidget(dlg)
    dlg.tabs.setCurrentIndex(1)
    dlg.tj.setValue(120.0)
    dlg.tref.setValue(100.0)
    dlg.par.setValue(10.0)
    assert dlg.out2.text() == "<b>2.000 W</b>" and dlg.use2.isEnabled()
    before = win.doc.problem.heaters[0].power
    n = win.doc.stack.count()
    dlg.use2.click()
    assert win.doc.problem.heaters[0].power == pytest.approx(2.0) and win.doc.stack.count() == n + 1
    win.doc.stack.undo()
    assert win.doc.problem.heaters[0].power == pytest.approx(before)
    dlg.tj.setValue(90.0)                                                               # the reference is hotter than the junction: a message, no button
    assert "hotter" in dlg.out2.text() and not dlg.use2.isEnabled()
    dlg.close()


def test_no_heater_disables_the_calculation_and_the_buttons(qtbot):
    dlg = calc.PowerCalculator(Document())
    qtbot.addWidget(dlg)
    assert not dlg.compute.isEnabled() and dlg.result.text() == "Draw a heater first." and not dlg.use2.isEnabled()
    assert dlg.selected_power() is None


def test_the_help_button_opens_the_help_page(win, opened, qtbot, monkeypatch):
    win.show_calculator()
    dlg = opened[0]
    qtbot.addWidget(dlg)
    shown = []
    monkeypatch.setattr(calc.CalculatorHelp, "exec", lambda self: (shown.append(self), 0)[1])
    dlg.help_btn.click()
    assert len(shown) == 1
    html = shown[0].view.toPlainText()
    assert "band" in html.lower() and len(html) > 500
    assert dlg.close_btn.text() == "Close"
    dlg.show()
    dlg.close_btn.click()
    assert not dlg.isVisible()


def _imported_synthetic(tmp_path):
    """!
    @brief The synthetic fabrication set imported with 2 W on U1 (a Problem with imported copper and its record).
    @param tmp_path Temporary folder.
    @return tuple (Problem, ImportRecord).
    """
    sx = ImportSession()
    sx.set_files(make_board(tmp_path / "fab"))
    sx.load()
    sx.set_part("U1", power=2.0)
    sx.cell_mm = 1.0
    prob = sx.build_problem()
    return prob, sx.record


def test_the_calculator_on_an_imported_copper_board(qtbot, tmp_path):
    """The calculator runs the board model on a board with imported copper: the power it finds reproduces the one that made the temperature."""
    prob, rec = _imported_synthetic(tmp_path)
    doc = Document()
    doc.open_import(prob, rec)
    assert doc.problem.imported is not None
    doc.set_options(cell_mm=2.0)
    row = simulate(doc.problem, SolverOptions(models=("fvm",), cell_mm=2.0)).heater_rows()[0]
    truth = doc.problem.heaters[0].power
    dlg = calc.PowerCalculator(doc)
    qtbot.addWidget(dlg)
    dlg.band.setChecked(False)
    dlg.point.setCurrentIndex(dlg.point.findData("mean"))
    dlg.measured.setValue(row["t_mean"])
    dlg.ambient.setValue(doc.problem.board.ambient)
    doc.set_props("heater", 0, power=0.5, merge=False)
    dlg.compute.click()
    _wait_result(qtbot, dlg)
    assert dlg.out is not None, dlg.result.text()
    assert dlg.out["power_w"] == pytest.approx(truth, rel=0.02)
    dlg.use.click()
    assert doc.problem.heaters[0].power == pytest.approx(truth, rel=0.02)
    assert doc.project.imports                                                          # the import record is untouched by the calculator
    dlg.close()


@pytest.mark.skipif(not REAL or not os.path.isdir(os.path.join(REAL, "rp2040")), reason="PCBT_REAL_BOARDS does not point to the real boards")
def test_the_calculator_on_the_imported_rp2040(qtbot):
    sx = ImportSession()
    sx.set_files(os.path.join(REAL, "rp2040"))
    sx.load()
    sx.set_part("C1", power=0.5)
    sx.cell_mm = 1.0
    prob = sx.build_problem()
    doc = Document()
    doc.open_import(prob, sx.record)
    doc.set_options(cell_mm=2.0)
    row = simulate(doc.problem, SolverOptions(models=("fvm",), cell_mm=2.0)).heater_rows()[0]
    dlg = calc.PowerCalculator(doc)
    qtbot.addWidget(dlg)
    dlg.band.setChecked(False)
    dlg.point.setCurrentIndex(dlg.point.findData("max"))
    dlg.measured.setValue(row["t_max"])
    dlg.ambient.setValue(doc.problem.board.ambient)
    dlg.compute.click()
    _wait_result(qtbot, dlg)
    assert dlg.out is not None, dlg.result.text()
    assert dlg.out["power_w"] == pytest.approx(doc.problem.heaters[0].power, rel=0.03)
    dlg.close()
