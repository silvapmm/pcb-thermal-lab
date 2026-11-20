#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_exact1d.py
@brief Checks of the independent exact solutions of the folder (no program run) and of the program's FEM stepper on the T3 bar.
@details Light: a few seconds.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import exact1d as E  # noqa: E402


def test_t3_exact_series_rounds_to_the_published_value_and_is_converged():
    """!
    @brief The series gives 36.6031 degC at x = 0.08 m, t = 32 s (published 36.60) and does not move with the number of terms.
    @return None.
    """
    a = E.bar_sinusoidal_end(0.08, 32.0, n_terms=500)
    b = E.bar_sinusoidal_end(0.08, 32.0, n_terms=8000)
    assert abs(a - b) < 1e-4
    assert abs(b - 36.603116) < 2e-6
    assert round(b, 2) == 36.60


def test_t3_series_meets_its_boundary_and_initial_conditions():
    """!
    @brief u(0, t) = 0, u(L, t) = 100 sin(pi t / 40) and u(x, 0+) = 0 within the series truncation.
    @return None.
    """
    assert abs(E.bar_sinusoidal_end(0.0, 20.0)) < 1e-9
    assert abs(E.bar_sinusoidal_end(0.1, 20.0, n_terms=20000) - 100.0 * np.sin(np.pi * 20 / 40)) < 0.05
    assert abs(E.bar_sinusoidal_end(0.05, 1e-6)) < 1e-3


def test_semi_infinite_flux_closed_form_value():
    """!
    @brief 2 q sqrt(alpha t / pi) / k for q = 1000 W/m2, k = 35, alpha = 35 / 3.172e6, t = 10 s equals the hand value.
    @return None.
    """
    got = E.semi_infinite_flux_step(10.0, 1000.0, 35.0, 3.172e6)
    assert abs(got - 2 * 1000 / 35 * np.sqrt(35 / 3.172e6 * 10 / np.pi)) < 1e-12


def test_robin_plate_series_goes_to_the_dirichlet_series_and_to_the_steady_state():
    """!
    @brief A very large film gives the Dirichlet double series; at a long time the centre rise is the steady one (a second, independent value: the Dirichlet steady centre
           0.2947 q s^2 / k of the square plate).
    @return None.
    """
    k, rc, q, s = 35.0, 3.172e6, 1e6, 0.1
    d = E.square_plate_uniform_heating(0.04, 0.05, 30.0, s, k, rc, q, n_max=201)
    r = E.square_plate_robin_heating(0.04, 0.05, 30.0, s, k, rc, q, 1e9, n_roots=100)
    assert abs(float(d) - float(r)) < 2e-3 * float(d)
    cen = float(E.square_plate_uniform_heating(0.05, 0.05, 5000.0, s, k, rc, q, n_max=201))
    assert abs(cen / (q * s * s / k) - 0.07367) < 2e-4          # Dirichlet steady centre of the unit square, T k / (q s^2) = 0.0736713 (Poisson problem)


def test_program_fem_stepper_reproduces_t3_to_the_published_digits():
    """!
    @brief The femcore stepper on the T3 bar, 200 elements, 3200 Crank-Nicolson steps: within 0.005 K of the exact series and within 0.01 K of the published 36.60.
    @return None.
    """
    import study_t3_and_plate as S
    got = S.fem_t3(n=200)
    assert abs(got - E.bar_sinusoidal_end(0.08, 32.0)) < 0.005
    assert abs(got - 36.60) < 0.01
