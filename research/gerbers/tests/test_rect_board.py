"""!
@file test_rect_board.py
@brief The rectangle board in the five models of the program: convergence with the cell size and the spread between the models (README 4.35 and 4.37). Needs the program's dependencies.
"""

import pytest

pytest.importorskip("pcbthermal")

from pcbthermal import SolverOptions, simulate  # noqa: E402
from pcbthermal.analysis import heater_stats  # noqa: E402

import study_rect_convergence as sc  # noqa: E402


def rise(p, model, cell):
    """!
    @brief Mean heater rise of one model.
    @param p Problem.
    @param model Model key.
    @param cell Cell (mm).
    @return float Rise (K).
    """
    sim = simulate(p, SolverOptions(models=(model,), cell_mm=cell))
    return heater_stats(sim.results[model], p)[0]["t_mean"] - p.board.ambient


def test_fvm_converges_and_the_fill_error_depends_on_the_cell_edges():
    """!
    @brief The FVM converges (0.25 mm against 0.1 mm within 1.5 %); at 1 mm the error is small with the edges on the cells and larger with the copper between them; the FDM reaches the same limit.
    @return None.
    """
    for shift, lo, hi in ((0.0, 0.0, 3.0), (0.4, 4.0, 9.0)):
        p = sc.problem(shift)
        fine, mid, coarse = rise(p, "fvm", 0.1), rise(p, "fvm", 0.25), rise(p, "fvm", 1.0)
        assert abs(mid / fine - 1) < 0.015
        assert lo <= 100 * abs(coarse / fine - 1) <= hi
        assert abs(rise(p, "fdm", 0.25) / fine - 1) < 0.04


def test_models_differ_in_physics_not_only_in_grid():
    """!
    @brief At 0.25 mm the Lumped and the Analytic are 10 to 30 % below the FVM and the 3D solid (two layers) is 4 to 12 % above it.
    @return None.
    """
    p = sc.problem(0.0)
    ref = rise(p, "fvm", 0.25)
    assert -0.30 < rise(p, "lumped", 0.25) / ref - 1 < -0.10
    assert -0.32 < rise(p, "analytic", 0.25) / ref - 1 < -0.10
    assert 0.04 < rise(p, "solid3d", 0.25) / ref - 1 < 0.12
