#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_calculator_dialog.py
@brief The Power Calculator dialog (gui/calculator.py) driven offscreen on the datasheet boards of docs/calculators.md 2.1: the numbers shown by the dialog, the greyed
       fields, the selector that writes the power into the part, the Help page and the dialog closed while its calculation runs.
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("pytestqt")

from pcbthermal.gui import calculator as calc
from pcbthermal.gui import compute
from pcbthermal.gui.document import Document

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "research", "power-calculator", "scripts"))

import calculator_validation as cv                                          # noqa: E402


def _dialog(qtbot, board, theta_ja, point="junction", psi_jt=0.0, cell_mm=0.5):
    """!
    @brief A calculator dialog on a datasheet board, filled with the temperature the datasheet's RθJA gives for 1 W.
    @param qtbot pytest-qt fixture.
    @param board Problem of the datasheet board.
    @param theta_ja Datasheet RθJA in K/W.
    @param point Measurement point key of the dialog.
    @param psi_jt Datasheet ψJT in K/W (point "top").
    @param cell_mm Cell size of the project in mm.
    @return tuple (Document, PowerCalculator).
    """
    doc = Document()
    doc.project.problem = board
    doc.set_options(cell_mm=cell_mm)
    dlg = calc.PowerCalculator(doc)
    qtbot.addWidget(dlg)
    dlg.band.setChecked(False)
    dlg.point.setCurrentIndex(dlg.point.findData(point))
    dlg.ambient.setValue(board.board.ambient)
    dlg.measured.setValue(board.board.ambient + theta_ja - psi_jt)
    if point == "top":
        dlg.psi_jt.setValue(psi_jt)
    return doc, dlg


def _wait(qtbot, dlg):
    """!
    @brief Wait until the dialog shows a result or a message.
    @param qtbot pytest-qt fixture.
    @param dlg PowerCalculator.
    @return None
    """
    qtbot.waitUntil(lambda: dlg.use.isEnabled() or ("Calculating" not in dlg.result.text() and dlg.result.text() != ""), timeout=180000)


def test_the_dialog_gives_the_csd17308q3_numbers_of_the_validation_table(qtbot):
    """TI CSD17308Q3 (RθJA 46 K/W): the dialog shows 0.986 W, i.e. a model resistance of 46.7 K/W and -1.4 % (docs/calculators.md 2.1)."""
    _doc, dlg = _dialog(qtbot, cv.csd17308q3_board(), 46.0)
    dlg.compute.click()
    _wait(qtbot, dlg)
    assert dlg.out is not None, dlg.result.text()
    p = dlg.out["power_w"]
    assert 46.0 / p == pytest.approx(46.7, abs=0.15)
    assert 100 * (p - 1.0) == pytest.approx(-1.4, abs=0.3)
    assert f"{p:.3f} W" in dlg.result.text()


@pytest.mark.parametrize("point,psi", [("junction", 0.0), ("top", 0.3)])
def test_the_dialog_gives_the_jedec_2s2p_numbers_of_the_validation_table(qtbot, point, psi):
    """JEDEC 2s2p exposed-pad QFN (RθJA 32.5 K/W): 31.6 K/W and +2.9 % at the 0.5 mm cell of the dialog (docs/calculators.md 2.1 prints 31.4 and +3.4), from the junction and from the top with ψJT 0.3 K/W."""
    _doc, dlg = _dialog(qtbot, cv.jedec_2s2p_board(), 32.5, point=point, psi_jt=psi)
    dlg.compute.click()
    _wait(qtbot, dlg)
    assert dlg.out is not None, dlg.result.text()
    p = dlg.out["power_w"]
    assert 32.5 / p == pytest.approx(31.6, abs=0.2)
    assert 100 * (p - 1.0) == pytest.approx(2.9, abs=0.4)


def test_fields_not_used_by_the_point_are_greyed_and_the_selector_writes_the_power(qtbot):
    """θ and ψJT are greyed for the board points; the case selector chooses the power that Use writes into the part (one undo step)."""
    doc, dlg = _dialog(qtbot, cv.csd17308q3_board(), 46.0)
    dlg.point.setCurrentIndex(dlg.point.findData("ring"))
    assert not dlg.theta.isEnabled() and not dlg.psi_jt.isEnabled()
    dlg.point.setCurrentIndex(dlg.point.findData("top"))
    assert dlg.theta.isEnabled() and dlg.psi_jt.isEnabled()
    dlg.point.setCurrentIndex(dlg.point.findData("junction"))
    assert dlg.theta.isEnabled() and not dlg.psi_jt.isEnabled()
    dlg.point.setCurrentIndex(dlg.point.findData("ring"))
    dlg.band.setChecked(True)
    dlg.design.setCurrentIndex(dlg.design.findData("hand"))
    dlg.compute.click()
    _wait(qtbot, dlg)
    assert dlg.out is not None and "worst_w" in dlg.out, dlg.result.text()
    dlg.case.setCurrentIndex(dlg.case.findData("worst"))
    n = doc.stack.count()
    dlg.use.click()
    assert doc.problem.heaters[0].power == pytest.approx(dlg.out["worst_w"])
    assert doc.stack.count() == n + 1
    doc.stack.undo()
    assert doc.problem.heaters[0].power != pytest.approx(dlg.out["worst_w"])


def test_the_help_button_shows_the_calculator_page(qtbot, monkeypatch):
    """Help opens calculator.html in the help dialog (its exec is replaced so that the test does not block)."""
    _doc, dlg = _dialog(qtbot, cv.csd17308q3_board(), 46.0)
    shown = []
    monkeypatch.setattr(calc.CalculatorHelp, "exec", lambda self: (shown.append(self.view.toPlainText()), 0)[1])
    dlg.help_btn.click()
    assert len(shown) == 1 and "band" in shown[0].lower() and "validation" in shown[0].lower()


def test_closing_the_dialog_while_the_job_runs_cancels_it_cleanly(qtbot):
    """The modal dialog is closed (Close or Esc) with the calculation running: the job is cancelled, nothing is shown afterwards and the engine becomes idle."""
    _doc, dlg = _dialog(qtbot, cv.csd17308q3_board(), 46.0)
    dlg.show()
    dlg.compute.click()
    assert dlg.worker is not None and dlg.worker.isRunning() and not dlg.compute.isEnabled()
    dlg.close_btn.click()
    assert not dlg.isVisible()
    assert not dlg.worker.isRunning()
    qtbot.waitUntil(lambda: not compute.busy(), timeout=60000)
    qtbot.wait(300)                                                             # a late signal of the cancelled job must not raise
    assert dlg.out is None and not dlg.use.isEnabled()
