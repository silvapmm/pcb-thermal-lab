#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_transient.py
@brief The frame rule of the study reads the same fluxes as the program's steady read-out, and the plate rules reproduce the closed forms.
"""

import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import rules  # noqa: E402
import transient as TR  # noqa: E402
from pcbthermal import SolverOptions, simulate  # noqa: E402


@pytest.mark.parametrize("ci", [0, 2])
def test_the_frame_rule_at_steady_state_equals_the_programs_steady_surface(ci):
    # Long implicit steps reach the steady state; the surface of the frame must be the T_surface of thickness.attach at the same cell
    case = TR.CASES[ci]
    prob = TR.problem(case)
    fr = TR.Frames(prob)
    out = fr.run(lambda s: 1.0, 2e4, 40)
    res = simulate(prob, SolverOptions(models=("fvm",), cell_mm=10.0)).results["fvm"]
    cy, cx = res.T.shape[1] // 2, res.T.shape[2] // 2
    assert out["col"][-1] + 25.0 == pytest.approx(res.T[0, cy, cx], abs=1e-6)
    assert out["surf"][-1] + 25.0 == pytest.approx(res.arrays["T_surface"][0, cy, cx], abs=1e-6)


def test_rule_f_on_the_programs_own_field_reproduces_the_fvm_surface_on_a_one_dimensional_board():
    # The uniform conductances are exact on a one-dimensional board: rule F on the FVM column equals the FVM surface
    case = TR.CASES[0]
    prob = TR.problem(case)
    res = simulate(prob, SolverOptions(models=("fvm",), cell_mm=10.0)).results["fvm"]
    f = rules.field_rule(prob, np.asarray(res.T), 10.0)
    assert np.allclose(f["top"], res.arrays["T_surface"][0], atol=2e-4)


def test_the_bound_is_q_t_over_2k():
    case = TR.CASES[1]
    prob = TR.problem(case)
    res = simulate(prob, SolverOptions(models=("lumped",), cell_mm=10.0)).results["lumped"]
    f = rules.field_rule(prob, np.asarray(res.T), 10.0)
    q = 1.0 / (0.02 * 0.02)
    assert float(f["bound_top"].max()) == pytest.approx(q * 10e-3 / (2 * 200.0), rel=1e-9)
