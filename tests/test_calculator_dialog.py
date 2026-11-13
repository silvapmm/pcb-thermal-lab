#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_calculator_dialog.py
@brief The Power Calculator dialog (gui/calculator.py) driven offscreen on the datasheet boards of docs/calculators.md 2.1 (the numbers the dialog shows at its cell)
       and the dialog closed while its calculation runs. The greyed fields, the case selector with its undo step and the Help page are held by
       tests/test_calculator_window.py (the review removed the copies that were here).
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


def test_the_dialog_gives_the_jedec_2s2p_numbers_of_the_validation_table(qtbot):
    """JEDEC 2s2p exposed-pad QFN (RθJA 32.5 K/W): 31.6 K/W and +2.9 % at the 0.5 mm cell of the dialog (docs/calculators.md 2.1; `calculator_validation.py` prints the same) (the top point with ψJT is held through the API by tests/test_calculator_validation.py)."""
    _doc, dlg = _dialog(qtbot, cv.jedec_2s2p_board(), 32.5)
    dlg.compute.click()
    _wait(qtbot, dlg)
    assert dlg.out is not None, dlg.result.text()
    p = dlg.out["power_w"]
    assert 32.5 / p == pytest.approx(31.6, abs=0.2)
    assert 100 * (p - 1.0) == pytest.approx(2.9, abs=0.4)


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
