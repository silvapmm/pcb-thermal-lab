#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_analytic_2_6.py
@brief Tests of the analytic-2-6 prototypes: the per-layer edge iteration and the local modal transient.

@details Run: .venv/bin/python -m pytest -q research/analytic-2-6/tests
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(ROOT))
for sub in (("analytic-2-6", "lib"), ("analytic-2-6", "scripts"), ("analytic-edge-spatial", "scripts"), ("analytic-edge-spatial", "lib")):
    sys.path.insert(0, os.path.join(REPO, "research", *sub))
sys.path.insert(0, REPO)

import boards26 as B                  # noqa: E402
import local_modal as LM              # noqa: E402
import perlayer_local as PL           # noqa: E402
import robin_perlayer as RP           # noqa: E402
import study_review_checks as R       # noqa: E402
from pcbthermal import analytic       # noqa: E402


def test_equal_layers_is_the_program_bit_for_bit():
    """!
    @brief Layers with the same slab / S: no mismatch, the iteration is skipped and the result is the program's.
    @return None.
    """
    p = R.board(2, False, 200.0, "corner", (1, 1))
    assert RP.solve(p, 1.0)["t_max"] == analytic.solve_steady(p, 1.0).t_max
    assert RP.solve(p, 1.0)["iterations"] == 0


def test_per_layer_edge_matches_independent_finite_differences():
    """!
    @brief Unequal layers: the iteration equals the 2D finite-difference solution of the same sheets with the true per-layer Robin edge to 0.3 %; the common beta does not.
    @return None.
    """
    p = R.board(2, False, 200.0, "corner", (0.2, 1))
    r = RP.solve(p, 1.0)
    sh = r["sh"]
    rect = analytic._equivalent_rectangle(p.heaters[0].polygon, sh["W"], sh["H"])
    a, b = (R.sheet_fd(sh, p.board, rect, p.total_power(), d) for d in (0.5e-3, 0.25e-3))
    ext = b + (b - a) / 3.0
    x = r["t_max"] - 25.0
    assert abs(x / ext - 1.0) < 0.003
    assert abs((analytic.solve_steady(p, 1.0).t_max - 25.0) / ext - 1.0) > 0.05            # the common beta is 9.9 % off here
    assert abs(r["balance"] - 1.0) < 1e-3                                                  # the heat leaves through the faces and the per-layer edge


def test_complete_solve_agrees_with_the_uniform_iteration_without_vias():
    """!
    @brief The loop around the patched complete solve gives the same field as the uniform-board iteration when there are no vias and no heatsinks.
    @return None.
    """
    p = R.board(2, False, 200.0, "corner", (1, 0.2))
    assert abs(PL.solve(p, 1.0)["t_max"] - RP.solve(p, 1.0)["t_max"]) < 1e-3


def test_local_modal_without_local_elements_is_the_program():
    """!
    @brief No vias and no heatsinks: the local modal prototype hands over to the program's uniform system.
    @return None.
    """
    p = B.plain()
    t, z, r, _ = LM.step_local(p)
    t2, z2, r2 = analytic.step_responses(p)
    assert np.array_equal(z, z2) and np.array_equal(r, r2)


def test_local_modal_steady_resistance_is_the_steady_solve():
    """!
    @brief The calibrated local system ends at the steady rise of analytic.solve_steady at the same point (the program's own calibration target).
    @return None.
    """
    p = B.with_sink(B.with_vias(B.plain()))
    t, z, r, s = LM.step_local(p, K=16)
    ref = analytic.solve_steady(p, 1.0)
    assert abs(r[0] * p.heaters[0].power - (ref.t_max - 25.0)) / (ref.t_max - 25.0) < 0.01


def test_local_modal_time_to_63_beats_the_smeared_calibration():
    """!
    @brief Heatsink under the part: the smeared calibration reads t63 37 % short, the local system within 3 % of the FVM.
    @return None.
    """
    p = B.with_sink(B.plain())
    t, z, r = B.step(p, "fvm", 1.0)
    ref = B.t63(t, z[:1], r[:1])[0]
    ti, zi, ri = B.step(p, "analytic", 1.0)
    assert abs(B.t63(ti, zi[:1], ri[:1])[0] / ref - 1.0) > 0.3
    tl, zl, rl, _ = LM.step_local(p, K=16)
    assert abs(B.t63(tl, zl, rl)[0] / ref - 1.0) < 0.03
