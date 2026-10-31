#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_sor_omega.py
@brief The relaxation factor of the SOR: the Rayleigh-quotient estimate of Young's optimum (`fvm.Network.sor_omega`), its safety (below 2), the linked-node mask
       and the sweep counts against the earlier formula 2 / (1 + sin(pi / n)); the temperatures do not change.
@details Reference of the estimate: research/young-omega-tiles (Young's relation; the Rayleigh quotient is a lower bound of the Jacobi radius, so omega stays below the optimum).
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest

from pcbthermal import Problem, fvm
from pcbthermal.examples import example_board
from pcbthermal.model import Materials


def old_omega(net):
    """!
    @brief The relaxation factor of the program before the estimate: the optimum of a plate with fixed edges.
    @param net Network.
    @return float 2 / (1 + sin(pi / max(nx, ny))).
    """
    return 2.0 / (1.0 + np.sin(np.pi / max(net.nx, net.ny)))


def board(kind):
    """!
    @brief Small test boards: plain plate, partial copper, round board, vias.
    @param kind "plate", "partial", "round" or "vias".
    @return Problem.
    """
    w = 40.0
    p = Problem.new(w, w, 4, 1.6, 35.0, h_top=10.0, h_bottom=100.0, h_side=None, materials=Materials(k_fr4_inplane=0.3))
    if kind == "partial":
        for layer in range(1, 5):
            p.add_zone(layer, rect=(5, 5, 35, 30))
    else:
        for layer in range(1, 5):
            p.add_zone(layer, rect=(0, 0, w, w))
    p.add_heater(1, 2.0, rect=(17, 17, 23, 23))
    if kind == "round":
        t = np.linspace(0, 2 * np.pi, 96, endpoint=False)
        p.set_outline(np.c_[20 + 20 * np.cos(t), 20 + 20 * np.sin(t)])
    if kind == "vias":
        p.add_via_array((15, 15, 25, 25), 5, 5, 0.4, fill_k=385.0)
    return p


@pytest.mark.parametrize("kind", ["plate", "partial", "round", "vias"])
def test_sor_equals_direct_and_needs_fewer_sweeps(kind):
    """!
    @brief The temperatures are the direct solution to 1e-6 K and the sweeps are clearly fewer (2.5 times, 1.5 on partial copper) than with the earlier omega.
    @param kind Board kind.
    @return None.
    """
    net = fvm.Network(board(kind), 40, 40)
    direct, _ = net.solve_steady()
    new, res, info = net.solve_sor(tol=1e-11)
    old, _, info_old = net.solve_sor(omega=old_omega(net), tol=1e-11)
    assert info["converged"] and info_old["converged"]
    assert float(np.abs(new - direct).max()) < 1e-6
    assert info["omega"] < 2.0
    # Partial copper has a loose lower bound (1.9 times fewer sweeps measured); the others 3.3 times
    factor = 1.5 if kind == "partial" else 2.5
    assert info["iterations"] * factor < info_old["iterations"], (kind, info["iterations"], info_old["iterations"])


def test_example_board_sor_matches_direct():
    """!
    @brief The example board (vias, partial copper) at 2 mm: SOR equals the direct solve to 1e-6 K with fewer sweeps than the earlier omega.
    @return None.
    """
    net = fvm.Network(example_board(), 50, 40)
    direct, _ = net.solve_steady()
    new, _, info = net.solve_sor(tol=1e-11)
    _, _, info_old = net.solve_sor(omega=old_omega(net), tol=1e-11)
    assert info["converged"] and float(np.abs(new - direct).max()) < 1e-6
    assert info["iterations"] * 2.0 < info_old["iterations"]


def test_estimate_ignores_decoupled_nodes_of_a_round_board():
    """!
    @brief The cells off a round board are pinned and have no link; counted in the quotient they would drive omega towards 1. The estimate stays near 2.
    @return None.
    """
    net = fvm.Network(board("round"), 40, 40)
    assert net.sor_omega() > 1.8
    # Without the mask the quotient collapses (the regression this test guards)
    K = net.K.tocsr()
    d = K.diagonal()
    one = np.ones(K.shape[0])
    rho = 1.0 - float(one @ (K @ one)) / float(one @ d)
    assert 2.0 / (1.0 + np.sqrt(1.0 - rho * rho)) < net.sor_omega() - 0.1


@pytest.mark.parametrize("kind", ["plate", "partial", "round", "vias"])
def test_estimate_is_on_the_safe_side(kind):
    """!
    @brief omega is below 2 and not above the best of a scan around it (it is a lower bound of Young's optimum, so a larger omega never needs far fewer sweeps).
    @param kind Board kind.
    @return None.
    """
    net = fvm.Network(board(kind), 40, 40)
    w = net.sor_omega()
    assert 1.0 <= w < 2.0
    n_w = net.solve_sor(omega=w, tol=1e-9)[2]["iterations"]
    n_hi = net.solve_sor(omega=min(w + 0.5 * (2.0 - w), 1.999), tol=1e-9)[2]["iterations"]
    assert n_w <= 1.8 * n_hi             # the bound is loose on partial copper (1.7 measured), tight on the others


def test_the_estimate_costs_little():
    """!
    @brief One product with K: the estimate takes under 1 % of the time of the SOR.
    @return None.
    """
    import time
    net = fvm.Network(board("plate"), 80, 80)
    t0 = time.perf_counter()
    net.sor_omega()
    t_est = time.perf_counter() - t0
    t0 = time.perf_counter()
    net.solve_sor(tol=1e-9)
    t_sor = time.perf_counter() - t0
    assert t_est < 0.01 * t_sor


@pytest.mark.parametrize("kind", ["plate", "partial", "round", "vias"])
def test_estimate_is_below_young_optimum_of_the_exact_radius(kind):
    """!
    @brief The Rayleigh bound never exceeds the exact Jacobi radius of the full K (dense eigenvalues on a 16 x 16 grid), so omega is at or below Young's optimum.
    @details The radius is the largest modulus of the spectrum of D^-1/2 (D - K) D^-1/2; with the via blocks K has positive entries, so both ends are checked.
    @param kind Board kind.
    @return None.
    """
    net = fvm.Network(board(kind), 16, 16)
    K = net.K.toarray()
    s = 1.0 / np.sqrt(np.diag(K))
    lam = np.linalg.eigvalsh(np.eye(len(s)) - s[:, None] * K * s[None, :])
    rho = float(max(abs(lam[0]), abs(lam[-1])))
    omega_opt = 2.0 / (1.0 + np.sqrt(1.0 - rho * rho))
    assert net.sor_omega() <= omega_opt + 1e-12


def test_tiny_networks_converge():
    """!
    @brief A network of one or two cells per side: the earlier formula gave omega = 2 at n = 1 (no convergence); the estimate stays below 2 and the SOR equals the direct solve.
    @return None.
    """
    p = Problem.new(10.0, 10.0, 2, 1.6, 35.0, h_top=10.0, h_bottom=10.0)
    for layer in (1, 2):
        p.add_zone(layer, rect=(0, 0, 10, 10))
    p.add_heater(1, 1.0, rect=(4, 4, 6, 6))
    for n in (1, 2):
        net = fvm.Network(p, n, n)
        direct, _ = net.solve_steady()
        theta, _, info = net.solve_sor(tol=1e-10, max_iter=5000)
        assert info["converged"] and info["omega"] < 2.0
        assert float(np.abs(theta - direct).max()) < 1e-6
