#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_small_251.py
@brief Three small 2.5.1 fixes: the missing background image is said, the Analytic heatsink transient note reaches every Results summary, the live partial-copper via pass has a time cap.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from pcbthermal import SquareWave, analytic, checks
from pcbthermal.api import SolverOptions, simulate
from pcbthermal.examples import example_board


def test_missing_background_image_is_said_once(qtbot, tmp_path):
    from PySide6.QtCore import QSettings
    from pcbthermal.gui.document import Document
    from pcbthermal.gui.main_window import MainWindow
    win = MainWindow(Document(), QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    qtbot.addWidget(win)
    seen = []
    win.canvas.message.connect(seen.append)
    cfg = {"path": str(tmp_path / "gone.png"), "x_mm": 0.0, "y_mm": 0.0, "w_mm": 30.0, "h_mm": 20.0}
    win.doc.project.view["background"] = cfg
    win.canvas.rebuild()
    win.canvas.rebuild()                                          # A redraw does not repeat the message
    assert len(seen) == 1 and "gone.png" in seen[0] and "not found" in seen[0] and "Background image" in seen[0]
    assert win.doc.project.view["background"]["path"] == cfg["path"]      # The stored path is kept
    win._after_load()
    assert "gone.png" in win.statusBar().currentMessage()         # Not overwritten by "Ready." on a load
    # An unreadable file (exists, is not an image) is worded differently
    bad = tmp_path / "bad.png"
    bad.write_text("not an image")
    win.doc.project.view["background"]["path"] = str(bad)
    win.canvas.rebuild()
    assert "could not be read" in seen[-1] and "bad.png" in seen[-1]


@pytest.mark.parametrize("period", [20.0, 0.01])
def test_analytic_heatsink_note_in_every_profile_run(period):
    p = example_board()
    assert p.heatsinks
    p.heaters[0].set_profile(SquareWave(p_on=10.0, period=period, duty=0.3))      # 20 s: resolved; 10 ms: averaged
    sim = simulate(p, SolverOptions(models=("analytic",), cell_mm=2.0))
    assert any(analytic.HEATSINK_TRANSIENT_KEY in w for w in sim.warnings)


def test_animation_notes_reach_the_summary(qtbot):
    from pcbthermal.gui.results_view import ResultsView
    rv = ResultsView()
    qtbot.addWidget(rv)
    p = example_board()
    sim = simulate(p, SolverOptions(models=("analytic",), cell_mm=2.0))
    rv.set_simulation(sim)
    tr = analytic.solve_transient(p, 10.0, n_out=4, cell_mm=2.0)
    rv.animation.set_result(tr, p)
    assert analytic.HEATSINK_TRANSIENT_KEY in rv.warnings.text()
    rv.set_simulation(sim)                                       # A new run clears the old animation's notes
    assert analytic.HEATSINK_TRANSIENT_KEY not in rv.warnings.text()
