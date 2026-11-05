#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_analytic_transient_warning.py
@brief The Analytic time simulation of a board with a heatsink carries the measured-error warning, and only then.
"""
from pcbthermal import analytic
from pcbthermal.api import SolverOptions, simulate
from pcbthermal.examples import example_board
from pcbthermal import SquareWave

KEY = "-66 % to +84 %"


def _profile_board(heatsink):
    """!
    @brief The example board with a square-wave profile on its first part, with or without heatsinks.
    @param heatsink True to keep the heatsinks of the example, False to remove them.
    @return Problem.
    """
    p = example_board()
    if not heatsink:
        p.heatsinks = []
    p.heaters[0].set_profile(SquareWave(p_on=10.0, period=20.0, duty=0.3))
    return p


def _analytic_warnings(p, models=("analytic",)):
    """!
    @brief Warnings of the time simulation of the chosen models.
    @param p Problem.
    @param models Model keys.
    @return List of strings.
    """
    sim = simulate(p, SolverOptions(models=models, cell_mm=2.0))
    return [w for w in sim.warnings if "(time simulation)" in w or "time simulation" in w]


def test_heatsink_profile_run_warns_with_the_measured_range():
    p = _profile_board(True)
    assert p.heatsinks
    assert any(KEY in w for w in _analytic_warnings(p))


def test_no_heatsink_no_warning():
    p = _profile_board(False)
    assert not any(KEY in w for w in _analytic_warnings(p))
    assert not any(KEY in w for w in analytic._AnalyticAdapter(p, 2.0, 40).warnings)


def test_steady_run_and_other_models_do_not_warn():
    p = example_board()
    steady = simulate(p, SolverOptions(models=("analytic",), cell_mm=2.0))
    assert not any(KEY in w for w in steady.warnings)
    other = simulate(_profile_board(True), SolverOptions(models=("fvm", "lumped"), cell_mm=2.0))
    assert not any(KEY in w for w in other.warnings)


def test_warning_names_the_sample_and_not_the_lumped_model():
    """!
    @brief The text says where the range was measured and does not send the user to the Lumped model (it was -41.8 % with the heatsink beside the part).
    """
    w = [x for x in analytic._AnalyticAdapter(_profile_board(True), 2.0, 40).warnings if KEY in x]
    assert len(w) == 1
    assert "sample" in w[0] and "not a bound" in w[0] and "+175 %" in w[0] and "step response only" in w[0]
    assert "FVM or the FDM" in w[0]
    assert "Lumped" not in w[0]


def test_transient_result_carries_the_warning_for_the_animation():
    """!
    @brief The animation of the Analytic model (solve_transient) carries the warning; the FVM and FDM animations and a board without heatsink carry none.
    """
    from pcbthermal import fdm, fvm
    from pcbthermal.results import TransientResult
    p = example_board()
    tr = analytic.solve_transient(p, t_end=30.0, n_out=4, cell_mm=2.0, n_terms=40)
    assert any(KEY in w and w.startswith("Analytic (animation)") for w in tr.warnings)
    q = example_board()
    q.heatsinks = []
    assert not any(KEY in w for w in analytic.solve_transient(q, t_end=30.0, n_out=4, cell_mm=2.0, n_terms=40).warnings)
    assert fvm.solve_transient(p, t_end=30.0, n_out=4, cell_mm=4.0).warnings == []
    assert fdm.solve_transient(p, t_end=30.0, n_out=4, cell_mm=4.0).warnings == []
    # A result built without the field (an older caller) has an empty list
    old = TransientResult(times=tr.times, t_max=tr.t_max, t_mean=tr.t_mean, frames=tr.frames, steady_t_max=tr.steady_t_max, ambient=tr.ambient)
    assert old.warnings == []


def test_cli_transient_prints_the_warning(tmp_path, capsys):
    """!
    @brief The `transient` command prints the warning of an Analytic run with a heatsink, and none for the FVM.
    """
    from pcbthermal import cli
    path = tmp_path / "e.pcbt.json"
    cli.main(["example", str(path), "--which", "example"])
    assert cli.main(["transient", str(path), "--model", "analytic", "--t-end", "30", "--steps", "4", "--out", str(tmp_path / "a"), "--no-plots"]) == 0
    assert KEY in capsys.readouterr().out
    assert cli.main(["transient", str(path), "--model", "fvm", "--t-end", "30", "--steps", "4", "--cell-mm", "4", "--out", str(tmp_path / "f"), "--no-plots"]) == 0
    assert KEY not in capsys.readouterr().out


def test_animation_status_shows_the_warning(qtbot):
    """!
    @brief The animation tab writes the warnings of the result under its status line (and in its tooltip); a result without warnings shows none.
    """
    from pcbthermal.gui.animation import AnimationTab
    p = example_board()
    tab = AnimationTab()
    qtbot.addWidget(tab)
    tab.set_result(analytic.solve_transient(p, t_end=30.0, n_out=4, cell_mm=2.0, n_terms=40), p)
    assert KEY in tab.status.text() and KEY in tab.status.toolTip()
    q = example_board()
    q.heatsinks = []
    tab.set_result(analytic.solve_transient(q, t_end=30.0, n_out=4, cell_mm=2.0, n_terms=40), q)
    assert KEY not in tab.status.text() and KEY not in tab.status.toolTip()
