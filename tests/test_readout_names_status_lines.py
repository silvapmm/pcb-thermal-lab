#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_readout_names_status_lines.py
@brief The status bar after a run, the Animation summary and the `transient` command line name the read-out of the temperature they show ("(column)"); no number moves.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from pcbthermal import analytic
from pcbthermal.api import SolverOptions, simulate
from pcbthermal.cli import main
from pcbthermal.examples import example_board


def test_status_bar_after_a_run_names_the_read_out(qtbot, tmp_path):
    """!
    @brief The line under Run and the status bar read 'Tmax <value> °C (column)' after a model ran.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    """
    pytest.importorskip("pytestqt")
    from PySide6.QtCore import QSettings
    from pcbthermal.gui.document import Document
    from pcbthermal.gui.main_window import MainWindow
    win = MainWindow(Document(), QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    qtbot.addWidget(win)
    sim = simulate(example_board(), SolverOptions(models=("fvm",), cell_mm=2.0))
    win._on_done(sim)
    want = f"Tmax {sim.reference.t_max:.1f} °C (column), Rθ"
    assert want in win.statusBar().currentMessage()
    assert want in win.solver_panel.status.text()


def test_animation_summary_names_the_read_out(qtbot):
    """!
    @brief The Animation summary says 'Steady Tmax <value> °C (column)'.
    @param qtbot pytest-qt fixture.
    """
    from pcbthermal.gui.animation import AnimationTab
    tab = AnimationTab()
    qtbot.addWidget(tab)
    p = example_board()
    tr = analytic.solve_transient(p, t_end=30.0, n_out=4, cell_mm=2.0, n_terms=40)
    tab.set_result(tr, p)
    assert f"Steady Tmax {tr.steady_t_max:.1f} °C (column);" in tab.status.text()


def test_cli_transient_line_names_the_read_out(tmp_path, capsys):
    """!
    @brief The `transient` command prints both temperatures with '(column)'.
    @param tmp_path Temporary folder.
    @param capsys pytest output capture.
    """
    cfg = os.path.join(os.path.dirname(__file__), "..", "examples", "example_board.pcbt.json")
    main(["transient", cfg, "--t-end", "10", "--steps", "3", "--cell", "2", "--out", str(tmp_path)])
    line = next(x for x in capsys.readouterr().out.splitlines() if x.startswith("Transient done"))
    assert "steady Tmax" in line
    assert line.count("°C (column)") == 2
