#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_analytic_edge.py
@brief Tests of the edge-treatment prototypes of research/analytic-edge-spatial/lib.

@details Run from the repository root: .venv/bin/python -m pytest -q research/analytic-edge-spatial/tests
"""

import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))

import analytic_edge as ae                       # noqa: E402
from robin_basis import Basis                    # noqa: E402
from pcbthermal import Problem, analytic         # noqa: E402
from pcbthermal.examples import example_board    # noqa: E402


def uniform(w=60, h=40, layers=2, t=1.6, h_side=50.0, x0=None, y0=None, hf=10.0):
    """!
    @brief A full-copper board with a 10 mm, 2 W part.
    @param w Width in mm.
    @param h Height in mm.
    @param layers Layers.
    @param t Thickness in mm.
    @param h_side Edge coefficient (None = insulated).
    @param x0 Part corner x in mm (default centred).
    @param y0 Part corner y in mm (default centred).
    @param hf Face coefficient.
    @return Problem.
    """
    p = Problem.new(width_mm=w, height_mm=h, layers=layers, thickness_mm=t, copper_um=35.0, ambient=25.0, h_top=hf, h_bottom=hf, h_side=h_side)
    for k in range(1, layers + 1):
        p.add_zone(k, rect=(0, 0, w, h))
    x0 = (w - 10.0) / 2 if x0 is None else x0
    y0 = (h - 10.0) / 2 if y0 is None else y0
    p.add_heater(1, 2.0, rect=(x0, y0, x0 + 10.0, y0 + 10.0))
    return p


def test_basis_orthogonal_and_robin():
    """!
    @brief The eigenfunctions are orthogonal, satisfy the Robin condition and project like their quadrature.
    @return None.
    """
    b = Basis(0.1, 30.0, 30)
    x = np.linspace(0, 0.1, 40001)
    P = b.evaluate(x)
    G = np.trapezoid(P[:, :, None] * P[:, None, :], x, axis=0)
    assert np.abs(G - np.diag(b.norm)).max() / b.norm.max() < 1e-7
    assert np.abs(np.trapezoid(P, x, axis=0) - b.project(0, 0.1)).max() < 1e-8
    # phi'(0) = beta phi(0) and phi'(L) = -beta phi(L), by a centred difference
    h = 1e-6
    dp = (b.evaluate([h]) - b.evaluate([-h])) / (2 * h)
    assert np.allclose(dp[0], 30.0 * b.evaluate([0.0])[0], rtol=1e-4, atol=1e-3)


def test_basis_beta_zero_is_cosine():
    """!
    @brief beta = 0 returns the cosine basis of the program.
    @return None.
    """
    b = Basis(0.06, 0.0, 10)
    assert np.allclose(b.lam, np.arange(10) * np.pi / 0.06)


def test_faces_reproduces_program():
    """!
    @brief The copy with the faces treatment equals analytic.solve_steady (uniform board, and the example board with its vias and heatsinks).
    @return None.
    """
    for p in (uniform(), uniform(h_side=200.0, x0=0.0, y0=0.0)):
        ref = analytic.solve_steady(p, cell_mm=1.0)
        mine = ae.solve(p, 1.0, edge="faces")
        assert np.abs(mine["T"] - ref.T).max() < 1e-9
    p = example_board()
    ref = analytic.solve_steady(p, cell_mm=1.0)
    mine = ae.solve(p, 1.0, edge="faces")
    assert np.abs(mine["T"] - ref.T).max() < 1e-6


def test_none_is_insulated():
    """!
    @brief edge="none" equals the program on the same board with h_side None.
    @return None.
    """
    p = uniform()
    q = uniform(h_side=None)
    assert abs(ae.solve(p, 1.0, edge="none")["t_max"] - analytic.solve_steady(q, 1.0).t_max) < 1e-9


def test_robin_energy_balance():
    """!
    @brief Heat out through faces and edge equals the power (Robin treatment), for a corner part with a large edge coefficient.
    @return None.
    """
    p = uniform(h_side=200.0, x0=0.0, y0=0.0)
    r = ae.solve(p, 1.0, edge="robin", n_terms=300)
    assert r["p_faces"] + r["p_edge"] == pytest.approx(2.0, rel=2e-3)


def test_robin_series_against_one_dimensional_finite_differences():
    """!
    @brief The Robin series solves S theta'' - h theta = -q 1[x1, x2] with theta' = +-beta theta at the ends (independent finite differences).
    @return None.
    """
    from scipy.sparse import diags
    from scipy.sparse.linalg import spsolve
    L, beta, S, h, x1, x2 = 0.05, 40.0, 0.02, 15.0, 0.003, 0.012
    n = 4000
    dx = L / n
    xc = (np.arange(n) + 0.5) * dx
    q = np.where((xc > x1) & (xc < x2), 1.0, 0.0)
    main = np.full(n, 2.0 * S / dx ** 2 + h)
    off = np.full(n - 1, -S / dx ** 2)
    # Robin end: the flux S beta theta leaves through the end cell (half a cell to the face, series with the film S beta)
    g_end = 1.0 / (dx / (2.0 * S) + 1.0 / (S * beta)) / dx
    main[0] += g_end - S / dx ** 2
    main[-1] += g_end - S / dx ** 2
    T = spsolve(diags([off, main, off], [-1, 0, 1], format="csc"), q)
    b = Basis(L, beta, 400)
    a = (b.project(x1, x2) / b.norm) / (S * b.eig2 + h)
    ts = b.evaluate(xc) @ a
    assert np.abs(ts - T).max() / T.max() < 2e-3


def test_3d_reference_energy_and_series_circuit():
    """!
    @brief The independent 3D solver closes the heat balance and reproduces a one-dimensional series circuit.
    @details A source covering the whole top face of a plate with an insulating-by-size edge (h_side 0) is one-dimensional: rise = P (1/(h A) + sum(d/k A)/... ) as a series
             of the top film, the half slabs and the bottom film.
    @return None.
    """
    import layered3d_side as l3
    dx, nx, ny = 1e-3, 12, 10
    slabs = [(35e-6, 385.0, 385.0, 1), (0.4e-3, 0.9, 0.3, 4), (35e-6, 385.0, 385.0, 1)]
    top, out = l3.solve_3d(dx, nx, ny, slabs, (0.0, 0.0, nx * dx, ny * dx), 3.0, 10.0, 0.0)
    assert out == pytest.approx(3.0, rel=1e-9)
    area = nx * ny * dx * dx
    # series: top film (applied behind half of the first cell), the through resistances to the bottom film; temperature of the top slab centre
    r_film = 1.0 / (10.0 * area)
    r_to_bottom = (0.4e-3 / 0.3 + 35e-6 / 385.0) / area
    # heat flows both up through the top film and down through the stack to the bottom film (two parallel paths from the top node)
    r_down = r_to_bottom + r_film
    r_par = 1.0 / (1.0 / r_film + 1.0 / r_down)
    assert top.mean() == pytest.approx(3.0 * r_par, rel=0.01)
    # with the side film the balance still closes
    top2, out2 = l3.solve_3d(dx, 30, 20, slabs, (10 * dx, 5 * dx, 20 * dx, 15 * dx), 2.0, 10.0, 200.0)
    assert out2 == pytest.approx(2.0, rel=1e-9)


def test_muzychka_equation_21_against_finite_volumes_and_fin_limit():
    """!
    @brief Equation 21 of Muzychka, Culham and Yovanovich (Part II) reproduces an independent 3D finite-volume solution of the edge-cooled flux channel.
    @details 50 x 50 mm channel of k = 50 W/mK and 1 mm, 10 x 10 mm source at the centre, adiabatic top outside the source, h = 100 on the bottom, h_e = 200 on the four edges:
             the mean source rise over the power from the series, from the 3D solver (0.5 mm cells, 8 sub-slabs) and from the thin-sheet series of the Robin basis.
    @return None.
    """
    import muzychka as mz
    import layered3d_side as l3
    a = b = 5e-3
    c = d = 25e-3
    t, k, h, he = 1e-3, 50.0, 100.0, 200.0
    r21 = mz.eq21(a, b, c, d, t, k, h, he, he)
    dx = 0.5e-3
    n = 100
    top, out = l3.solve_3d(dx, n, n, [(t, k, k, 8)], (20e-3, 20e-3, 30e-3, 30e-3), 1.0, h, he, h_top=0.0)
    xs = (np.arange(n) + 0.5) * dx
    m = (xs[None, :] > 20e-3) & (xs[None, :] < 30e-3) & (xs[:, None] > 20e-3) & (xs[:, None] < 30e-3)
    r3d = float(top[m].mean())
    assert out == pytest.approx(1.0, rel=1e-9)
    assert r21 == pytest.approx(r3d, rel=0.01)
    rfin = mz.fin_limit(a, b, c, d, t, k, h, he, he)
    assert rfin == pytest.approx(r21, rel=0.03)         # thin sheet: tau = t / sqrt(A_s) = 0.1


def test_step_response_ends_at_the_steady_resistance():
    """!
    @brief The unit-step response of the copy tends to the steady resistance of the same treatment (rise per watt at the hottest point), and Robin time constants are finite.
    @return None.
    """
    p = uniform(h_side=200.0, x0=0.0, y0=0.0)
    for edge in ("faces", "robin"):
        times, z, rth, t63 = ae.step_response(p, edge, n_terms=120)
        steady = (ae.solve(p, 1.0, edge=edge, n_terms=120)["t_max"] - 25.0) / 2.0
        assert rth == pytest.approx(steady, rel=1e-6)
        assert z[-1] == pytest.approx(rth, rel=1e-3)
        assert 0.0 < t63 < times[-1]


@pytest.mark.parametrize("beta", [1e-30, 1e-15, 1e-10, 1e-7, 1e-3, 1.0, 1e3, 1e8, 1e14])
def test_basis_roots_any_beta(beta):
    """!
    @brief Regression (review): the roots are found for every edge parameter, they solve the eigen-equations and they are ordered, one per interval.
    @details The prototype's brentq on d tan d failed below beta Lh of about 1e-9 times the highest root and above about 1e12 (no sign change at the ends of
             the bracket in floating point); a guard of the program needs the same behaviour.
    @param beta Edge parameter in 1/m.
    @return None.
    """
    L = 0.06
    b = Basis(L, beta, 600)
    d = b.lam * L / 2
    assert np.all(np.diff(d) > 0)
    k = np.arange(600) // 2
    lo = np.where(b.kind == 0, k * np.pi, k * np.pi + 0.5 * np.pi)
    assert np.all(d >= lo - 1e-12) and np.all(d <= lo + 0.5 * np.pi + 1e-12)
    bl = beta * L / 2
    res = np.where(b.kind == 0, d * np.sin(d) - bl * np.cos(d), d * np.cos(d) + bl * np.sin(d))
    assert np.abs(res).max() <= 1e-9 * max(1.0, bl) * d.max()


def test_small_beta_is_continuous_with_the_cosine():
    """!
    @brief Regression (review): a vanishing edge coefficient tends to the insulated board linearly (no jump at the switch to the cosine basis).
    @return None.
    """
    p0 = uniform(h_side=None, x0=0.0, y0=0.0)
    t0 = ae.solve(p0, 1.0, n_terms=120, edge="robin")["t_max"]
    d = []
    for hs in (1e-3, 1e-5, 1e-7, 1e-9):
        p = uniform(h_side=hs, x0=0.0, y0=0.0)
        d.append(t0 - ae.solve(p, 1.0, n_terms=120, edge="robin")["t_max"])
    assert all(x >= 0.0 for x in d)
    assert d[0] / d[1] == pytest.approx(100.0, rel=0.02)
    assert d[3] < 1e-8
