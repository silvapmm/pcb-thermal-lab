"""!
@file test_tooltips.py
@brief Every control of the application explains itself with a tooltip, in every state of every panel.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("pytestqt")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QAbstractSpinBox, QCheckBox, QComboBox, QLineEdit, QPushButton, QRadioButton, QSlider, QTableWidget, QTreeWidget

from pcbthermal import SolverOptions, SquareWave, TableProfile, simulate
from pcbthermal.examples import example_block_board
from pcbthermal.gui import tips
from pcbthermal.gui.calculator import PowerCalculator
from pcbthermal.gui.document import Document
from pcbthermal.gui.main_window import MainWindow

KINDS = (QAbstractSpinBox, QComboBox, QCheckBox, QPushButton, QLineEdit, QSlider, QRadioButton, QTableWidget, QTreeWidget)


def missing(root, label):
    """!
    @brief Controls under root that have no tooltip (own or of their parent control).
    @param root QWidget to scan.
    @param label Context name for the report.
    @return List of (context, class, text).
    """
    out = []
    for kind in KINDS:
        for w in root.findChildren(kind):
            parent = w.parent()
            if isinstance(w, QLineEdit) and isinstance(parent, (QAbstractSpinBox, QComboBox)):
                continue                                             # The editor inside a spin box or combo box
            if parent is not None and isinstance(parent, KINDS) and parent.toolTip():
                continue
            if not w.toolTip():
                out.append((label, type(w).__name__, getattr(w, "text", lambda: "")() if not isinstance(w, QLineEdit) else w.objectName()))
    return out


def test_every_control_has_a_tooltip(qtbot, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr("pcbthermal.gui.main_window.QMessageBox.question", lambda *a, **k: QMessageBox.Discard)     # Closing a modified document asks
    win = MainWindow(Document(), QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    qtbot.addWidget(win)
    win.resize(1500, 900)
    win.show()
    win._load_problem(example_block_board(), "tips")
    bad = []
    bad += missing(win.board_panel, "board")
    bad += missing(win.solver_panel, "simulation")
    bad += missing(win.elements, "elements")
    win.stackup_page.mode.setCurrentIndex(1)
    bad += missing(win.stackup_page, "stack-up advanced")
    win.stackup_page.mode.setCurrentIndex(0)
    bad += missing(win.stackup_page, "stack-up simple")
    pr = win.doc.problem
    for kind, n in (("zone", len(pr.zones)), ("heater", len(pr.heaters)), ("heatsink", len(pr.heatsinks)), ("via", len(pr.vias))):
        for i in range(n):
            win.inspector.set_selection([(kind, i)])
            bad += missing(win.inspector.form_host, f"inspector {kind}")
    win.inspector.set_selection([("heater", 0), ("zone", 0)])
    bad += missing(win.inspector.form_host, "inspector several")
    # Power profile page in every profile kind
    for profile in (None, SquareWave(3.0, 1.0, 0.5), TableProfile([0.0, 1.0, 2.0], [1.0, 3.0], True)):
        win.doc.set_props("heater", 0, merge=False)
        if profile is None:
            pr.heaters[0].set_profile(None)
        else:
            pr.heaters[0].set_profile(profile)
        win.doc.changed.emit()
        bad += missing(win.profile_page, f"profile {type(profile).__name__}")
    # Results with every tab (the profile run adds its own tabs)
    pr.heaters[0].set_profile(None)
    sim = simulate(pr, SolverOptions(models=("fvm", "lumped", "analytic"), cell_mm=2.0))
    win.sim = sim
    win.results.set_simulation(sim)
    tips.apply(win.results)
    bad += missing(win.results, "results")
    bad += missing(win.toolbar, "toolbar")
    from pcbthermal.gui.profile_results import ProfileResultsTab as ProfileResults
    pres = ProfileResults()
    qtbot.addWidget(pres)
    bad += missing(pres, "profile results")
    calc = PowerCalculator(win.doc)
    qtbot.addWidget(calc)
    bad += missing(calc, "calculator")
    assert not bad, "\n".join(map(str, sorted(set(bad))))
