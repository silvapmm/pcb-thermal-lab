"""!
@file test_gui_profile.py
@brief The Power profile page and its results, offscreen.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("pytestqt")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QMessageBox

from pcbthermal import SolverOptions, simulate
from pcbthermal.examples import example_board
from pcbthermal.gui.document import Document
from pcbthermal.gui.main_window import TAB_PROFILE, TAB_RESULTS, MainWindow


@pytest.fixture
def window(qtbot, tmp_path, monkeypatch):
    doc = Document()
    doc.open_problem(example_board(), "example")
    w = MainWindow(doc, QSettings(str(tmp_path / "s.ini"), QSettings.IniFormat))
    qtbot.addWidget(w)
    monkeypatch.setattr("pcbthermal.gui.main_window.QMessageBox.warning", lambda *a, **k: None)
    monkeypatch.setattr("pcbthermal.gui.main_window.QMessageBox.critical", lambda *a, **k: None)
    monkeypatch.setattr("pcbthermal.gui.main_window.QMessageBox.question", lambda *a, **k: QMessageBox.Discard)
    return w


def test_edit_square_wave_and_units(window):
    page = window.profile_page
    page.table.selectRow(1)
    page.kind.setCurrentIndex(1)                               # Square wave
    page.value.setValue(20.0)
    page.duty.setValue(25.0)
    page.p_on.setValue(6.0)
    h = window.doc.problem.heaters[1]
    assert h.profile.period == pytest.approx(20.0) and h.profile.duty == pytest.approx(0.25)
    assert h.average_power() == pytest.approx(1.5)
    # Frequency entry: 100 Hz is a 10 ms period
    page.table.selectRow(0)
    page.kind.setCurrentIndex(1)
    page.by.setCurrentIndex(1)
    page.unit.setCurrentText("Hz")
    page.value.setValue(100.0)
    assert window.doc.problem.heaters[0].profile.period == pytest.approx(0.01)
    page.kind.setCurrentIndex(0)
    assert window.doc.problem.heaters[0].profile is None


def test_analysis_and_full_run(window, qtbot):
    pr = window.doc.problem
    from pcbthermal import SquareWave
    pr.heaters[0].set_profile(SquareWave(p_on=4 / 0.3, period=0.01, duty=0.3))
    pr.heaters[1].set_profile(SquareWave(p_on=6.0, period=20.0, duty=0.25))
    window.doc.changed.emit()
    window.profile_page.run_analysis()
    qtbot.waitUntil(lambda: bool(window.profile_page.decisions), timeout=60000)
    assert [d.regime for d in window.profile_page.decisions] == ["average", "resolved"]
    assert window.profile_page.dec_table.rowCount() == 2
    window.doc.options.cell_mm = 2.0
    window.run_simulation()
    qtbot.waitUntil(lambda: window.sim is not None, timeout=120000)
    assert window.tabs.currentIndex() == TAB_RESULTS
    tab = window.results.time_sim
    assert tab.model.count() == 3
    for i in range(tab.view.count()):
        tab.view.setCurrentIndex(i)
    assert window.tabs.indexOf(window.profile_page) == TAB_PROFILE
