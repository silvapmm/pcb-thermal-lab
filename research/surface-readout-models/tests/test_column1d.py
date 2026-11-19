#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_column1d.py
@brief Checks of the independent column solver and of the closed forms of the study that need no program run.
"""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import column1d  # noqa: E402


def test_steady_state_is_the_series_resistance_and_the_surface_is_q_t_over_2k_above_the_mean():
    # One slab, flux q on top, film h below: the long-time surface rise is q (1/h + t/k), the mean q (1/h + t/2k), so surface - mean = q t / 2k
    t, k, rc, h, q = 5e-3, 100.0, 3e6, 200.0, 1e4
    r = column1d.solve([(t, k, rc, 40)], h, lambda s: q, 600.0, 0.5)
    assert r["surf"][-1] == pytest.approx(q * (1 / h + t / k), rel=2e-3)
    assert r["surf"][-1] - r["mean"][0][-1] == pytest.approx(q * t / (2 * k), rel=2e-3)
    assert r["balance"] < 1e-4


def test_short_time_is_the_half_space_law():
    # Before the heat reaches the bottom the surface follows 2 q sqrt(t / (pi k rho c))
    t, k, rc, q = 20e-3, 400.0, 3.4e6, 1e5
    tau = 0.05
    r = column1d.solve([(t, k, rc, 60)], 1e-3, lambda s: q, tau, 1e-4)
    assert r["surf"][-1] == pytest.approx(2 * q * np.sqrt(tau / (np.pi * k * rc)), rel=0.01)


def test_two_layers_balance_the_energy():
    r = column1d.solve([(2e-3, 385.0, 3.4e6, 20), (1e-3, 0.3, 1.7e6, 10), (35e-6, 385.0, 3.4e6, 2)], 50.0, lambda s: 5e3, 100.0, 0.1)
    assert r["balance"] < 1e-4
