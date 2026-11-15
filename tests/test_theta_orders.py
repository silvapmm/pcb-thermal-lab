#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_theta_orders.py
@brief The orders of the theta method of the transient solver against the exact exponential of a uniform slab (docs/validation.md 7, docs/theory.md 2.5).

@details Implicit Euler (theta 1) is first order and Crank-Nicolson (theta 0.5) second order in the step. The orders measured on the program are 0.88 to 0.96 (Euler)
         and 2.00 to 2.03 (Crank-Nicolson); the bands below hold them, with four step sizes (substeps 1, 2, 4, 8),
         and the error at the finest step is held too (a wrong theta keeps the order of its family).
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest

from pcbthermal import fvm, laminate
from tests.test_fvm import reference_problem


def _slab(monkeypatch):
    """!
    @brief The uniform one-layer slab of test_fvm: a single node with an exact exponential response.
    @param monkeypatch pytest fixture used to switch the laminate nodes off.
    @return Problem.
    """
    monkeypatch.setattr(laminate, "LAMINATE_NODES", 0)
    monkeypatch.setattr(laminate, "uses_rule", lambda problem: False)
    p = reference_problem(layers=1, heater_mm=100.0, power=10.0)
    p.board.h_side = None
    return p


def _error(p, tau, exact, scheme, substeps):
    """!
    @brief Largest error of the hottest point against the exact exponential.
    @param p Problem.
    @param tau Time constant in s.
    @param exact Callable t (s) -> exact temperature in degC.
    @param scheme Theta of the method (1 Euler, 0.5 Crank-Nicolson).
    @param substeps Substeps per output interval.
    @return float Largest absolute error in K.
    """
    tr = fvm.solve_transient(p, t_end=3 * tau, n_out=6, cell_mm=12.5, substeps=substeps, theta_scheme=scheme, log_times=False)
    return float(np.abs(tr.t_max - exact(tr.times)).max())


# Bands of the asymptotic order (measured 0.964 and 2.002) and the error at the finest step (measured 0.4482 and 0.004792 K): the order alone cannot tell a wrong
# theta between 0.5 and 1 from implicit Euler (theta 0.75 also gives 0.96, with half the error), so the error itself is held within 5 %
@pytest.mark.parametrize("scheme,low,high,finest", [(1.0, 0.9, 1.05, 0.4482), (0.5, 1.95, 2.05, 0.004792)])
def test_observed_order_of_the_theta_method(monkeypatch, scheme, low, high, finest):
    p = _slab(monkeypatch)
    net = fvm.Network(p, 8, 8, assemble=False)
    C, G, P = net.C.sum(), net.g_amb.sum(), net.Q.sum()
    tau = C / G
    exact = lambda t: p.board.ambient + P / G * (1.0 - np.exp(-t / tau))
    errs = [_error(p, tau, exact, scheme, s) for s in (1, 2, 4, 8)]
    orders = [np.log2(errs[i] / errs[i + 1]) for i in range(3)]
    print(f"\ntheta {scheme}: errors {errs}, orders {orders}")
    # The step halves at each line: the last order is the asymptotic one
    assert low <= orders[-1] <= high
    assert abs(errs[-1] / finest - 1.0) < 0.05
