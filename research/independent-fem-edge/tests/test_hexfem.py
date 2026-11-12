#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_hexfem.py
@brief Tests of the finite-element solver against closed forms and conservation: a 1D series stack, a fin with a source, the energy balance of the canonical boards, mesh helpers.
@details Run: `.venv/bin/python -m pytest -q research/independent-fem-edge/tests`.
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import boards                                                                  # noqa: E402
import hexfem                                                                  # noqa: E402


def test_grid1d_hits_breaks_and_is_increasing():
    """!
    @brief The graded grid contains every break and has positive steps no larger than h_max.
    @return None.
    """
    x = hexfem.grid1d(10.0, [1.0, 4.0, 7.3], [(0, 0.6), (9.4, 10)], 0.1, 1.3, 0.5)
    assert x[0] == 0.0 and x[-1] == 10.0
    for b in (1.0, 4.0, 7.3):
        assert np.min(np.abs(x - b)) < 1e-12
    d = np.diff(x)
    assert d.min() > 0 and d.max() <= 0.5 * 1.35 and d[0] < 0.15


def test_series_stack_matches_closed_form():
    """!
    @brief A column with the heat in the top copper brick equals the series-resistance solution of the two-film stack (insulated sides).
    @return None.
    """
    hmat = 0.01
    m, hm, tc = boards.build(np.array([0.0, hmat]), np.array([0.0, hmat]), 2, 1.6e-3, lambda l, X, Y: np.ones_like(X, bool), (-1, -1, 1, 1), 2.0, 10.0, 25.0,
                             (0, 0, 0, 0), 0.9, 0.3, 8)
    r = m.solve()
    area = hmat * hmat
    gap = 1.6e-3 - 2 * boards.T_CU
    # exact: rise of the top copper (its own conduction is negligible, 35 um of copper) from the three resistances in series
    r_gap = gap / (0.3 * area)
    gt, gb = 10.0 * area, 25.0 * area
    # the same column as a network: P into the top node, films on both faces, the gap between
    a = np.array([[gt + 1.0 / r_gap, -1.0 / r_gap], [-1.0 / r_gap, gb + 1.0 / r_gap]])
    t = np.linalg.solve(a, [2.0, 0.0])
    out = boards.read_out(m, hm, tc, r)
    assert abs(out["mean"] / t[0] - 1) < 2e-4
    assert abs(out["balance"] - 1) < 1e-10


def test_fin_with_a_source_matches_closed_form():
    """!
    @brief A thin copper bar with a source in its first part and films on all four lateral faces equals the 1D fin solution (insulated ends).
    @return None.
    """
    k, hf = 385.0, 50.0
    t = 1e-3                                           # square bar section t x t, 1 mm
    L, a, q_tot = 0.05, 0.01, 0.2
    xn = hexfem.grid1d(L * 1e3, [a * 1e3], [(0, a * 1e3)], 0.25, 1.2, 2.0) * 1e-3
    yn, zn = np.array([0.0, t]), np.array([0.0, t])
    m = hexfem.Model(xn, yn, zn)
    m.kxy[:], m.kz[:] = k, k
    m.h_top = m.h_bottom = hf
    m.h_wall = (0.0, 0.0, hf, hf)
    xc = 0.5 * (xn[1:] + xn[:-1])
    q = q_tot / (t * t * a)
    m.q[:, :, xc < a] = q
    res = m.solve()
    mm = np.sqrt(hf * 4 * t / (k * t * t))             # m^2 = h P / (k A)
    # source region (0 <= x <= a): T = q/(k m^2) + A cosh(m x); fin region: T = B cosh(m (L - x)); match T and dT/dx at x = a
    tp = q / (k * mm * mm)
    # A cosh(m a) + tp = B cosh(m (L-a)); A m sinh(m a) = -B m sinh(m (L-a))
    mat = np.array([[np.cosh(mm * a), -np.cosh(mm * (L - a))], [mm * np.sinh(mm * a), mm * np.sinh(mm * (L - a))]])
    A, B = np.linalg.solve(mat, [-tp, 0.0])
    t_num = res["T"].mean(axis=(0, 1))                 # section mean at every node plane
    t_exact = np.where(xn <= a, tp + A * np.cosh(mm * xn), B * np.cosh(mm * (L - xn)))
    assert np.max(np.abs(t_num - t_exact)) / t_exact.max() < 2e-3
    assert abs(res["balance"] - 1) < 1e-10


def test_canonical_boards_close_the_heat_balance():
    """!
    @brief Every canonical board of the study closes the energy balance to rounding at a coarse mesh.
    @return None.
    """
    for build in (lambda: boards.strong_edge(1000.0, hf=0.4, n_gap=3, via_dist=3.0), lambda: boards.square(200.0, hf=0.8, n_gap=3), lambda: boards.t_outline(200.0, hf=0.8, n_gap=3)):
        m, hm, tc = build()
        out = boards.read_out(m, hm, tc, m.solve())
        assert abs(out["balance"] - 1) < 1e-9, out


def test_half_domain_t_equals_the_full_t():
    """!
    @brief The half-domain T board (symmetry plane x = 10 mm) gives the heater mean of the whole T (regression: the wall y = 0 of the stem had been left insulated, +2.3 % hot).
    @return None.
    """
    m0, h0, c0 = boards.t_outline(200.0, hf=0.4, n_gap=4)
    a = boards.read_out(m0, h0, c0, m0.solve())
    m, hm, tc = boards.t_outline_full(200.0)
    b = boards.read_out(m, hm, tc, m.solve())
    assert abs(a["mean"] / b["mean"] - 1) < 3e-3, (a["mean"], b["mean"])
