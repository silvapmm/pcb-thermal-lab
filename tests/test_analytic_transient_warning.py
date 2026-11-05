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

KEY = "-67 % to +113 %"


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
