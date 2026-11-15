#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_refboards.py
@brief Tests of the helpers of the transient comparison: the time to 63 %, the periodisation of a step response against a closed form, the program problems, and the
       energy balance and plateau of the finite-element step response of the coarsest two-layer board.
"""
import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import refboards as R                                                    # noqa: E402


def test_t_at_exponential():
    """!
    @brief The time to 63 % of 1 - exp(-t/tau) is tau.
    @return None.
    """
    t = np.geomspace(1e-3, 50, 400)
    assert R.t_at(t, 1 - np.exp(-t / 3.0), 1 - np.exp(-1.0)) == pytest.approx(3.0, rel=2e-3)


def test_periodise_single_pole():
    """!
    @brief The periodic peak of a one-pole response to a square wave equals the closed form.
    @return None.
    """
    tau, period, duty, rth = 2.0, 3.0, 0.4, 10.0
    t = np.geomspace(1e-4, 400, 600)
    pk, vl = R.periodise(t, rth * (1 - np.exp(-t / tau)), rth, period, duty)
    e_on, e_off = np.exp(-duty * period / tau), np.exp(-(1 - duty) * period / tau)
    peak = rth * (1 - e_on) / (1 - e_on * e_off)
    assert pk == pytest.approx(peak, rel=2e-3)
    # the valley: the on stretch raises the field by (rth - peak_start) and the off stretch lets the peak decay for the off time
    valley = peak * e_off
    assert vl == pytest.approx(valley, rel=2e-3)
    assert 0 < vl < pk < rth


@pytest.mark.parametrize("name", R.BOARDS)
def test_program_problems_validate(name):
    """!
    @brief Every board of the study is a valid program problem with one part.
    @param name Board.
    @return None.
    """
    p = R.program_problem(name)
    p.validate()
    assert len(p.heaters) == 1


def test_fem_two2_energy_and_plateau():
    """!
    @brief The coarse finite-element step response of `two2` closes its energy balance and ends on the steady solve.
    @return None.
    """
    try:
        import transient
    except Exception as exc:                                              # scikit-fem-free, but the libraries of the sibling folders must import
        pytest.skip(str(exc))
    m, rho_c, fp = R.fem_board("two2", 4.0)
    tr = transient.Transient(m, rho_c, consistent=False)
    w = tr.reduce_weights(transient.face_weights(m, fp))
    r = tr.step_response({"m": w}, 6000.0, dt0=0.05, per_level=5, factor=2.5)
    e_in, e_store, e_lost = r["energy"]
    assert abs(e_in - e_store - e_lost) / e_in < 1e-6
    assert r["series"]["m"][-1] == pytest.approx(float(w @ tr.steady()), rel=2e-3)
