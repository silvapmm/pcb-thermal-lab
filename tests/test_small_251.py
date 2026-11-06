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


class _FakeClock:
    """!
    @brief A clock that advances one second per reading, to cut the live via pass after a known number of vias.
    """

    def __init__(self):
        """!
        @brief Start at zero.
        """
        self.t = 0.0

    def perf_counter(self):
        """!
        @brief Read the clock.
        @return float Seconds, one more than the previous reading.
        """
        self.t += 1.0
        return self.t


def test_partial_copper_pass_cap(monkeypatch):
    from test_via_partial_copper_warning import _two_planes
    p = _two_planes(0.3, n_vias=9)
    full = [str(w) for w in checks.check_input(p, ("fvm",), 0.5, live=True) if "copper over only part" in str(w)]
    plain = [str(w) for w in checks.check_input(p, ("fvm",), 0.5) if "copper over only part" in str(w)]
    assert full == plain and full and "At least" not in full[0]          # A fast pass is identical to the run's list
    n_all, n_checked = checks.partial_copper_vias(p, 0.5)
    assert len(n_all) == 9 and n_checked == len(p.vias)
    # Truncated: the clock jumps a second per reading, the cap is 3.5 s, so the pass stops after three exact via tests
    monkeypatch.setattr(checks, "time", _FakeClock())
    partial, n_done, cut = checks.partial_copper_scan(p, 0.5, 3.5)
    assert cut and n_done < len(p.vias) and len(partial) <= len(n_all)
    monkeypatch.setattr(checks, "time", _FakeClock())
    msgs = [w for w in checks.check_via_partial_copper(p, ("fvm",), 0.5, 3.5)]
    assert msgs and "At least" in str(msgs[0]) and "Results of the run" in str(msgs[0]) and "At least" in msgs[0].short


def test_live_budget_constant_is_used(monkeypatch):
    from test_via_partial_copper_warning import _two_planes
    p = _two_planes(0.3, n_vias=9)
    seen = []
    real = checks.partial_copper_scan
    monkeypatch.setattr(checks, "partial_copper_scan", lambda *a, **k: (seen.append(a[2] if len(a) > 2 else k.get("budget_s")), real(*a, **k))[1])
    monkeypatch.setattr(checks, "PARTIAL_COPPER_BUDGET_S", 123.0)
    checks.check_input(p, ("fvm",), 0.5, live=True)
    checks.check_input(p, ("fvm",), 0.5)
    assert seen == [123.0, None]
