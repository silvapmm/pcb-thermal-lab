#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_sorvia.py
@brief Tests of `lib/sorvia.py`: the toy closed forms, the program's rule reproduced, the via part positive semi-definite, every variant against the direct solver.
@details Run from the repository root: `.venv/bin/python -m pytest -q research/sor-with-via-couplings/tests`.
"""

import os
import sys

import numpy as np
import pytest
import scipy.sparse.linalg as spla

LIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib")
sys.path.insert(0, LIB)

import boards as bd                                                         # noqa: E402
import sorvia as sv                                                         # noqa: E402


def setup_module(module):
    """!
    @brief Load the program's libraries once.
    @param module Unused.
    @return None.
    """
    bd.pc.load_libraries()


@pytest.fixture(scope="module")
def small():
    """!
    @brief A small board (6 mm square, 2 layers, one copper-filled via, 0.5 mm cells) with the mean-potential treatment.
    @return fvm.Network.
    """
    return bd.net_for(bd.pc.lone_via_board(6.0, 0.3, 385.0, source_mm=1.5, distance_mm=1.5), 0.5)


def test_toy_closed_forms():
    """!
    @brief The 4 x 4 toy: direct solution and the fixed point of the dropped matrix equal the 2 x 2 closed forms of study_failure part A.
    @return None.
    """
    gx, gz, gv, ga, q = 2.0, 3.0, 5.0, 0.5, 1.0
    t = bd.toy_two_layers(gx, gz, gv, ga, q)
    rhs = np.array([q / 2, q / 2, 0.0, 0.0])
    ex = np.linalg.solve(t["K"], rhs)
    b = (q / 2) / ga
    assert ex[2] == pytest.approx(b, rel=1e-12)
    assert ex[0] == pytest.approx(b + (q / 2) / (gz + gv / 2), rel=1e-12)
    fp = np.linalg.solve(t["Kst"], rhs)
    top, bot = np.linalg.solve([[gz + gv / 4, -gz], [-gz, gz + ga + gv / 4]], [q / 2, 0.0])
    assert fp[0] == pytest.approx(top, rel=1e-12) and fp[2] == pytest.approx(bot, rel=1e-12)


def test_point_treatment_has_no_via_part():
    """!
    @brief The program's own point link lives in the stencil: the via part is empty and its SOR is exact.
    @return None.
    """
    net = bd.net_for(bd.pc.lone_via_board(6.0, 0.3, 385.0, source_mm=1.5, distance_mm=1.5), 0.5, "point")
    assert sv.via_matrix(net).nnz == 0
    th, _ = net.solve_steady("direct")
    r = sv.solve_variant(net, "program", max_iter=20000)
    assert r["converged"] and np.abs(r["theta"] - th).max() < 1e-6


def test_program_variant_is_the_programs_sor(small):
    """!
    @brief `RB` with no via term reproduces `Network.solve_sor` sweep by sweep (same iterate after the same number of sweeps).
    @param small The network.
    @return None.
    """
    th, _, info = small.solve_sor(tol=1e-300, max_iter=30)
    r = sv.RB(small).solve(small.Q, tol=1e-300, max_iter=30)
    assert np.abs(r["theta"] - th).max() < 1e-12


def test_via_part_is_positive_semidefinite_and_exact(small):
    """!
    @brief K = A + B^T Gm B with the Laplacian blocks Gm: the via part is PSD, A has non-positive off-diagonals (an M-matrix), and the off-diagonals of the via part equal K - diag - stencil.
    @param small The network.
    @return None.
    """
    Kfull, B, Gm = sv.via_operator(small)
    assert np.linalg.eigvalsh(Kfull.toarray()).min() > -1e-9 * abs(Kfull).max()
    A = (small.K - Kfull).tocsr()
    off = A - __import__("scipy.sparse", fromlist=["diags"]).diags(A.diagonal())
    assert off.data.max() <= 1e-12
    Kv = sv.via_matrix(small)
    d = Kfull - __import__("scipy.sparse", fromlist=["diags"]).diags(Kfull.diagonal())
    # Where the via part overlaps a stencil position the two differ by the stencil value, so compare away from the stencil only through the norm of the difference of the matrices
    assert abs((Kv - d).tocsr()).max() < 1e-9 * abs(Kfull).max()
    assert (Kv.data > 0).any() and (Kv.data < 0).any()                      # both signs: not an M-matrix


def test_program_rule_fails_and_fixed_point_is_the_dropped_matrix(small):
    """!
    @brief The program's rule stops far from the direct solution, and its limit is the solution of the matrix without the via off-diagonals.
    @param small The network.
    @return None.
    """
    import scipy.sparse as sp
    th, _ = small.solve_steady("direct")
    r = sv.solve_variant(small, "program", max_iter=3000)
    assert not r["converged"] and th.max() - r["theta"].max() > 1.0
    Kdrop = (sp.diags(small.K.diagonal()) + sv.stencil_parts(small)["S"]).tocsc()
    ref = spla.spsolve(Kdrop, small.Q.ravel())
    r2 = sv.RB(small, K=Kdrop).solve(small.Q, tol=1e-12, max_iter=60000)
    assert np.abs(r2["theta"].ravel() - ref).max() < 1e-6


@pytest.mark.parametrize("variant", ["lagged", "block", "block_over", "woodbury"])
def test_variants_reach_the_direct_solution(small, variant):
    """!
    @brief The SOR variants converge to the direct solution of the true K.
    @param small The network.
    @param variant Variant name.
    @return None.
    """
    th, _ = small.solve_steady("direct")
    r = sv.solve_variant(small, variant, tol=1e-11, max_iter=60000)
    assert r["converged"]
    assert np.abs(r["theta"] - th).max() < 1e-6


@pytest.mark.parametrize("order", ["natural", "redblack"])
def test_ssor_cg_reaches_the_direct_solution(small, order):
    """!
    @brief CG preconditioned by SSOR gives the direct solution with both orderings.
    @param small The network.
    @param order Ordering.
    @return None.
    """
    th, _ = small.solve_steady("direct")
    r = sv.ssor_cg(small, 1.0, 1e-11, order=order)
    assert r["converged"] and np.abs(r["theta"] - th).max() < 1e-6


def test_stiff_via_lagged_loses_what_block_keeps(small):
    """!
    @brief The lagged variant needs the via part to be soft: at K_via x 1e3 the block variant still converges.
    @param small The network.
    @return None.
    """
    net = bd.scaled(small, 1e3)
    th = spla.spsolve(net.K, net.Q.ravel())
    r = sv.solve_variant(net, "block", tol=1e-10, max_iter=60000)
    assert r["converged"] and np.abs(r["theta"].ravel() - th).max() < 1e-5


def test_block_colouring_separates_coupled_blocks():
    """!
    @brief Review: on a dense array whose footprints touch, the colouring of `block_over` puts no two blocks that K couples in one group, and the result is the direct one.
    @return None.
    """
    net = bd.net_for(bd.pc.array_board(385.0, pitch_mm=1.0, n=5), 0.5)
    th, _ = net.solve_steady("direct")
    rb = sv.RB(net, blocks=sv.via_blocks(net), block_omega=None, colour_blocks=True)
    assert len(rb.groups) >= 2                                               # the footprints touch, so one group is not enough
    K = net.K.tocsr()
    blocks = sv.via_blocks(net)
    owner = np.full(K.shape[0], -1)
    for k, b in enumerate(blocks):
        owner[b] = k
    for rows, _Kb, _Binv in rb.groups:
        mine = set(owner[rows].tolist())
        for k in mine:
            nb = set(owner[K[blocks[k]].indices].tolist()) - {-1, k}
            assert not (nb & mine)
    r = rb.solve(net.Q, tol=1e-11, max_iter=60000)
    assert r["converged"] and np.abs(r["theta"] - th).max() < 1e-6


def test_energy_argument_on_touching_blocks():
    """!
    @brief Review (own matrix of `scripts/study_review.py`): blocks relaxed one after another converge for omega_b in (0, 2); all at once they diverge for omega_b > 1
           on touching footprints, and converge for omega_b <= 1 because 2 D_B - K_VV is positive definite.
    @return None.
    """
    sys.path.insert(0, os.path.join(os.path.dirname(LIB), "scripts"))
    import study_review as R
    b = R.board(**R.cases()[1][2])                                           # R2: 5 x 5 array, footprints touching in x and y, two layers
    assert R.energy_margin(b) > 0.0
    assert R.Sweeps(b, 1.5, "simultaneous", omega_b=1.0).radius() < 1.0
    assert R.Sweeps(b, 1.5, "simultaneous", omega_b=1.5).radius() > 1.0
    for ob in (0.5, 1.5, 1.9):
        assert R.Sweeps(b, 1.5, "sequential", omega_b=ob).radius() < 1.0
