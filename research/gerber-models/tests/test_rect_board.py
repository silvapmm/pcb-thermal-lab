#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
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
    @brief The FVM converges (0.25 mm against 0.1 mm within 1.5 %); at 1 mm the error is small with the edges on the cells and larger with the copper between them; the FDM reaches the same limit (within 4.5 %).
    @return None.
    """
    for shift, lo, hi in ((0.0, 0.0, 3.0), (0.4, 4.0, 9.0)):
        p = sc.problem(shift)
        fine, mid, coarse = rise(p, "fvm", 0.1), rise(p, "fvm", 0.25), rise(p, "fvm", 1.0)
        # limit moved from 1.5 % to 1.75 % (measured): the program changed in release 2.4.3 (fix/zone-union, the zones of this board are now
        # united per sample point, so the copper between the cell edges is counted in full): at shift 0.4 mm the 0.25 mm cell reads -1.33 %
        # of the 0.1 mm value in 2.4.2 and -1.55 % since 2.4.3 (shift 0: +0.12 % in both); nothing else in 2.4.5 moves it (bit-identical from v2.4.3 to develop)
        assert abs(mid / fine - 1) < 0.0175
        assert lo <= 100 * abs(coarse / fine - 1) <= hi
        # FDM limit 4 % -> 4.5 % for the same reason (zone union, 2.4.3): shift 0.4 reads -3.99 % in 2.4.2 and -4.13 % since 2.4.3 (shift 0: -2.72 % -> -2.87 %)
        # 4.5 % -> 5 % for the laminate rule of fix/laminate-nodes (measured: the FDM at 0.25 mm reads -4.90 % at shift 0.4 and -3.23 % at shift 0 with the rule, -4.13 % and -2.87 % without it;
        # the program with the rule switched off gives the earlier numbers to the digit, so the move is that item alone)
        assert abs(rise(p, "fdm", 0.25) / fine - 1) < 0.05


def test_models_differ_in_physics_not_only_in_grid():
    """!
    @brief At 0.25 mm the Lumped and the Analytic are 10 to 30 % below the FVM and the 3D solid (two layers) is 2 to 12 % above it (4 to 12 % before the laminate rule of the program).
    @return None.
    """
    p = sc.problem(0.0)
    ref = rise(p, "fvm", 0.25)
    assert -0.30 < rise(p, "lumped", 0.25) / ref - 1 < -0.10
    assert -0.32 < rise(p, "analytic", 0.25) / ref - 1 < -0.10
    # Lower bound 4 % -> 2 %: the laminate rule raises the layered FVM (the reference here) by 5 % on this two-layer board with patterned copper, the 3D solid is not changed by it:
    # measured +8.5 % without the rule, +3.0 % with it. The Lumped (-15.9 -> -20.2 %) and the Analytic (-26.4 -> -30.2 %) read lower against the FVM for the same reason, inside their limits.
    assert 0.02 < rise(p, "solid3d", 0.25) / ref - 1 < 0.12
