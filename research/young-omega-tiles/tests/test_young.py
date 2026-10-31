#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_young.py
@brief Tests of `lib/young.py` (S3): the textbook Poisson matrix, the torus and Young's relation against dense eigenvalues, the estimators against the exact radius, the independent
       red-black SOR against the program's `solve_sor`, and the adaptive estimate on a synthetic decay.
@details Run from the repository root: `.venv/bin/python -m pytest -q research/young-omega-tiles/tests/test_young.py`.
"""

import math
import os
import sys

import numpy as np
import pytest

LIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib")
sys.path.insert(0, LIB)

import young as yg                                                          # noqa: E402


def test_poisson_radius_is_cosine():
    """!
    @brief rho_J of the 5-point Laplacian with fixed edges is cos(pi / (n + 1)) (Saad 2003, section 4.2.5; Young).
    @return None.
    """
    for n in (4, 7, 10):
        assert yg.rho_exact(yg.poisson_matrix(n)) == pytest.approx(math.cos(math.pi / (n + 1)), abs=1e-12)


def test_young_relation_against_dense_sor_radius():
    """!
    @brief The spectral radius of the natural-order SOR matrix equals Young's relation for the consistently ordered Poisson matrix, below and above the optimum.
    @return None.
    """
    K = yg.poisson_matrix(6)
    mu = yg.rho_exact(K)
    for w in (1.0, 1.3, 1.6, yg.omega_young(mu), 1.8, 1.95):
        assert yg.sor_iteration_radius(K, w) == pytest.approx(yg.rho_sor(w, mu), abs=1e-7)


def test_optimum_is_the_minimum_of_the_dense_radius():
    """!
    @brief No omega on a fine grid gives a smaller dense SOR radius than Young's optimum.
    @return None.
    """
    K = yg.poisson_matrix(7)
    w_opt = yg.omega_young(yg.rho_exact(K))
    r_opt = yg.sor_iteration_radius(K, w_opt)
    for w in np.linspace(1.05, 1.98, 30):
        assert yg.sor_iteration_radius(K, float(w)) >= r_opt - 1e-9


def test_omega_inverse_and_program_formula():
    """!
    @brief omega_young and rho_from_omega_young are inverse; the program's factor is Young's optimum of a Poisson matrix of n - 1 interior points.
    @return None.
    """
    for w in (1.2, 1.7, 1.96):
        assert yg.omega_young(yg.rho_from_omega_young(w)) == pytest.approx(w, abs=1e-12)
    n = 30
    assert yg.omega_program(n, n) == pytest.approx(yg.omega_young(math.cos(math.pi / n)), abs=1e-12)


def test_torus_rayleigh_is_exact():
    """!
    @brief On a periodic plate with a uniform loss the uniform vector is the exact dominant eigenvector: the Rayleigh bound, the Lanczos value and the closed form all equal 4g/(4g+a).
    @return None.
    """
    K = yg.torus_matrix(12, 12, 1.0, 0.05)
    exact = 4.0 / 4.05
    assert yg.rho_exact(K) == pytest.approx(exact, abs=1e-12)
    assert yg.rho_rayleigh(K)[0] == pytest.approx(exact, abs=1e-12)
    assert yg.rho_lanczos(K, 3)[0] == pytest.approx(exact, abs=1e-12)
    assert yg.rho_closed_form(0, 0.05 * 144, diag_sum=float(K.diagonal().sum())) == pytest.approx(exact, abs=1e-12)


def test_torus_needs_even_sizes():
    """!
    @brief An odd torus is not two-colourable and is refused.
    @return None.
    """
    with pytest.raises(ValueError):
        yg.torus_matrix(7, 8)


def test_estimators_are_lower_bounds_and_lanczos_rises():
    """!
    @brief On a layered plate with an edge-only loss the Rayleigh bound and every Ritz value are below the exact radius, Ritz values do not decrease, and 20 steps beat the bound.
    @return None.
    """
    n, nl = 14, 3
    g = np.zeros((nl, n, n))
    g[:, :, 0] = 0.05
    K = yg.plate_matrix(nl, n, n, 1.0, 1.0, 0.5, g)
    rho = yg.rho_exact(K)
    rq = yg.rho_rayleigh(K)[0]
    r20, prods, hist = yg.rho_lanczos(K, 20)
    assert rq <= rho + 1e-12
    assert all(h <= rho + 1e-10 for h in hist)
    assert all(b >= a - 1e-12 for a, b in zip(hist, hist[1:]))
    assert prods == 20
    assert r20 > rq
    assert (1 - r20) < (1 - rq)


def test_closed_form_equals_rayleigh_on_a_plate():
    """!
    @brief The conductance totals give the Rayleigh bound without a product: sum of the row sums over the sum of the diagonal.
    @return None.
    """
    K = yg.plate_matrix(2, 10, 12, 1.0, 2.0, 0.7, 0.003)
    g_amb_total = float(np.asarray(K @ np.ones(K.shape[0])).sum())
    assert yg.rho_closed_form(0, g_amb_total, diag_sum=float(K.diagonal().sum())) == pytest.approx(yg.rho_rayleigh(K)[0], abs=1e-12)
    assert g_amb_total == pytest.approx(0.003 * 2 * 10 * 12, rel=1e-9)


def test_power_method_on_plain_jacobi_fails_but_shifted_converges():
    """!
    @brief The spectrum of J_s is symmetric, so the plain power method does not settle on rho_J, while the shifted one approaches it.
    @return None.
    """
    K = yg.plate_matrix(1, 12, 12, 1.0, 1.0, 0.0, 0.02)
    rho = yg.rho_exact(K)
    sh, _ = yg.rho_power(K, 400, start="random", seed=3)
    assert sh == pytest.approx(rho, abs=2e-3)
    assert sh <= rho + 1e-12


def test_independent_red_black_sor_solves_and_matches_the_dense_prediction():
    """!
    @brief The independent red-black SOR converges to the direct solution and its sweeps at Young's omega are far fewer than at omega = 1.5.
    @return None.
    """
    import scipy.sparse.linalg as spla
    K = yg.plate_matrix(2, 12, 12, 1.0, 1.0, 0.5, 0.002)
    b = np.zeros(K.shape[0])
    b[40] = 1.0
    col = yg.parity_colour(2, 12, 12)
    w = yg.omega_young(yg.rho_exact(K))
    x, it, ok = yg.sor_rb_matrix(K, b, col, w, 1e-10, 20000)
    x_ref = spla.spsolve(K.tocsc(), b)
    assert ok
    assert np.abs(x - x_ref).max() < 1e-7 * np.abs(x_ref).max() + 1e-10
    _x2, it2, _ok2 = yg.sor_rb_matrix(K, b, col, 1.5, 1e-10, 20000)
    assert it < it2


def test_adaptive_omega_recovers_young_from_a_geometric_decay():
    """!
    @brief Corrections that decay at the SOR rate of (omega0, mu) give back Young's omega for mu; omega0 above the optimum is left alone.
    @return None.
    """
    mu = 0.995
    w0 = 1.6
    lam = yg.rho_sor(w0, mu)
    steps = [lam ** k for k in range(20)]
    w, mu_hat, lam_hat = yg.adaptive_omega(steps, w0)
    assert lam_hat == pytest.approx(lam, rel=1e-9)
    assert mu_hat == pytest.approx(mu, abs=1e-9)
    assert w == pytest.approx(yg.omega_young(mu), abs=1e-8)
    w_over, _m, _l = yg.adaptive_omega([(1.99 - 1.0) ** k for k in range(20)], 1.99)
    assert w_over == 1.99


def test_lanczos_matches_scipy_on_a_poisson_matrix():
    """!
    @brief Many Lanczos steps from a random start reach the exact radius of the Poisson matrix.
    @return None.
    """
    K = yg.poisson_matrix(9)
    r, _p, _h = yg.rho_lanczos(K, 60, start="random", seed=5)
    assert r == pytest.approx(math.cos(math.pi / 10), abs=1e-9)


def test_program_sor_and_independent_sor_agree_on_a_program_board():
    """!
    @brief `Network.solve_sor` of the program and the independent red-black SOR take the same number of sweeps on the program's own matrix (same iteration, same stopping cadence).
    @return None.
    """
    import s3boards as sb
    sb.load_libraries()
    net = sb.net_program(sb.plate(2, 10.0, h_top=10.0, h_bottom=10.0), 1.0)
    w = yg.omega_young(yg.rho_exact(net.K))
    r = sb.sweeps_program(net, w, 1e-9, 20000)
    _x, it, ok = yg.sor_rb_matrix(net.K, np.asarray(net.Q, float).ravel(), yg.parity_colour(net.nl, net.ny, net.nx), w, 1e-9, 20000)
    assert r["converged"] and ok
    assert abs(r["iterations"] - it) <= 10
