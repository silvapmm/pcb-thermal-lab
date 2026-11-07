#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_analytic_edge.py
@brief The Analytic model puts the convective board edge in the eigenfunctions of the series (Robin basis; Muzychka, Culham and Yovanovich 2003, AIAA 2003-4188, Part II).

@details Checks: (1) the basis itself: orthogonality, the edge condition, the roots for any edge parameter from 1e-30 to 1e14 1/m, beta = 0 is the cosine basis; (2) a closed form,
         the 1D fin with Robin ends (uniform source, films on the faces); (3) the same sheets solved by an independent 2D finite-difference solver with a source in a corner
         (odd functions needed); (4) the heat balance with vias, a heatsink and a metal block; (5) mirror symmetry; (6) the uniform boards against the FVM; (7) bit identity without
         an edge coefficient; (8) the number of modes at a large edge parameter; (9) the modal transient shares the basis (steady resistance and time to 63 % against the FVM);
         (10) the warning of the shared edge parameter, firing and silent; (11) the real outline perimeter; (12) hostile edge coefficients.
"""

import math

import numpy as np
import pytest
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from pcbthermal import Problem, SolverOptions, simulate
from pcbthermal import analytic, laminate
from pcbthermal.api import step_response

T_AMB = 25.0


def _plate(w, h, src, h_side, layers=2, thickness=1.6, h_face=10.0, pos="centre"):
    """!
    @brief A uniform board (full copper on every layer) with a square source of 2 W on layer 1.
    @param w Width in mm.
    @param h Height in mm.
    @param src Side of the square source in mm.
    @param h_side Edge coefficient in W/m2K (None = insulated).
    @param layers Number of copper layers.
    @param thickness Board thickness in mm.
    @param h_face Coefficient of both faces in W/m2K.
    @param pos "centre" or "corner" (the source at the origin, which needs the odd functions of the basis).
    @return Problem.
    """
    p = Problem.new(width_mm=w, height_mm=h, layers=layers, thickness_mm=thickness, copper_um=35.0, ambient=T_AMB, h_top=h_face, h_bottom=h_face, h_side=h_side)
    for layer in range(1, layers + 1):
        p.add_zone(layer, rect=(0, 0, w, h))
    x0, y0 = ((w - src) / 2, (h - src) / 2) if pos == "centre" else (0.0, 0.0)
    p.add_heater(1, 2.0, rect=(x0, y0, x0 + src, y0 + src))
    return p


def _rise(p, model, cell=1.0):
    """!
    @brief Maximum rise of one model.
    @param p Problem.
    @param model Model key.
    @param cell Cell size in mm.
    @return float Rise above the ambient in K.
    """
    return simulate(p, SolverOptions(cell_mm=cell, models=(model,))).results[model].t_max - T_AMB


# ------------------------------------------------------------------------------------------------ the basis

@pytest.mark.parametrize("beta", [3.0, 58.0, 580.0, 5.0e4])
def test_basis_is_orthogonal_and_satisfies_the_edge_condition(beta):
    """The eigenfunctions are orthogonal for the weight 1 with the stated norms, and d/dn + beta = 0 holds at both ends."""
    L = 0.06
    b = analytic._EdgeBasis(L, beta, 12)
    x = np.linspace(0.0, L, 40001)
    phi = b.evaluate(x)
    gram = np.trapezoid(phi[:, :, None] * phi[:, None, :], x, axis=0)
    assert np.allclose(np.diag(gram), b.norm, rtol=1e-6)
    off = gram - np.diag(np.diag(gram))
    assert np.abs(off).max() < 1e-7 * L
    # derivative at the ends: even cos(lam u) and odd sin(lam u) in u = x - L/2
    u = np.array([-L / 2, L / 2])
    d_even = -b.lam * np.sin(np.outer(u, b.lam))
    d_odd = b.lam * np.cos(np.outer(u, b.lam))
    d = np.where(b.kind[None, :] == 0, d_even, d_odd)                 # d phi / du at u = -L/2, +L/2
    val = b.evaluate(np.array([0.0, L]))
    assert np.allclose(-d[0] + beta * val[0], 0.0, atol=1e-9 * (1 + beta) * 1.0 * np.maximum(1.0, b.lam.max()))     # outward normal at x = 0 is -u
    assert np.allclose(d[1] + beta * val[1], 0.0, atol=1e-9 * (1 + beta) * np.maximum(1.0, b.lam.max()))


@pytest.mark.parametrize("beta", [1e-30, 1e-12, 1e-6, 1.0, 58.0, 1e4, 1e8, 1e12, 1e14])
def test_basis_roots_any_beta(beta):
    """The roots are found, ordered and satisfy the eigen-equation for an edge parameter from 1e-30 to 1e14 1/m, 600 modes."""
    L = 0.06
    Lh = 0.5 * L
    b = analytic._EdgeBasis(L, beta, 600)
    assert np.all(np.isfinite(b.lam)) and np.all(np.diff(b.lam) > 0.0) and b.lam[0] > 0.0
    d = b.lam * Lh
    bl = beta * Lh
    even, odd = b.kind == 0, b.kind == 1
    # the pole-free forms of the eigen-equations, scaled by the size of each term
    res_e = np.abs(d[even] * np.sin(d[even]) - bl * np.cos(d[even])) / (d[even] + bl)
    res_o = np.abs(d[odd] * np.cos(d[odd]) + bl * np.sin(d[odd])) / (d[odd] + bl)
    assert res_e.max() < 1e-9 and res_o.max() < 1e-9


def test_beta_zero_is_the_cosine_basis():
    """beta = 0 is exactly cos(m pi x / L): wavenumbers, norms, values and projections."""
    L = 0.05
    b = analytic._EdgeBasis(L, 0.0, 30)
    assert b.cosine
    assert np.array_equal(b.lam, np.arange(30) * np.pi / L)
    assert np.array_equal(b.norm, np.where(np.arange(30) == 0, L, L / 2))
    assert np.array_equal(b.weight, np.where(np.arange(30) == 0, 1.0, 2.0))
    assert np.array_equal(b.project(0.01, 0.03), analytic._cos_projection(0.01, 0.03, L, 30))


def test_small_beta_is_continuous_with_the_cosine():
    """A vanishing edge coefficient tends to the insulated board linearly."""
    L = 0.05
    cos = analytic._EdgeBasis(L, 0.0, 20)
    prev = None
    for beta in (1e-3, 1e-4, 1e-5):
        b = analytic._EdgeBasis(L, beta, 20)
        dev = np.abs(b.lam[1:] - cos.lam[1:]).max() / cos.lam[1:].max()
        assert dev < 5e-3 * beta * L * 100 + 1e-12
        if prev is not None:
            assert dev < prev
        prev = dev


def test_basis_rejects_a_bad_parameter():
    """A negative or non-finite edge parameter is refused (not silently turned into an insulated edge)."""
    for beta in (-1.0, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            analytic._EdgeBasis(0.05, beta, 4)


# ------------------------------------------------------------------------------------------------ closed form and independent solver

@pytest.mark.parametrize("beta", [5.8, 58.0, 580.0])
def test_one_dimensional_fin_with_robin_ends(beta):
    """A uniform source on a sheet with a face film h and convective ends: theta = theta_inf (1 - C cosh(m u)), C = beta / (m sinh(m Lh) + beta cosh(m Lh)),
    m = sqrt(h / S). The series of the eigenfunctions (the coefficients of the program's modal equation) reproduces it."""
    L, S, h, q = 0.06, 0.3, 10.0, 1000.0
    Lh = 0.5 * L
    b = analytic._EdgeBasis(L, beta, 600)
    a = q * b.project(0.0, L) / b.norm / (S * b.eig2 + h)             # modal coefficients: (S lam^2 + h) a = q proj / norm
    x = np.linspace(0.0, L, 61)
    theta = b.evaluate(x) @ a
    m = math.sqrt(h / S)
    c = beta / (m * math.sinh(m * Lh) + beta * math.cosh(m * Lh))
    exact = (q / h) * (1.0 - c * np.cosh(m * (x - Lh)))
    assert np.abs(theta - exact).max() < 2e-4 * exact.max()


def _fd_hottest(p, dx_mm=0.25):
    """!
    @brief Independent finite-difference solution of the sheet of a one-layer board (the data of analytic._effective_sheet, edge condition S dtheta/dn = -h_eff s theta).
    @param p Problem with one layer and one heater.
    @param dx_mm Cell in mm.
    @return Tuple (hottest rise of the finite-difference solution, hottest rise of the Analytic series) in K.
    """
    q = laminate.series_bottom_problem(p)
    sh = analytic._effective_sheet(q, 1.0)
    b = sh["b"]
    S, slab, W, H = float(sh["S"][0]), float(sh["slab"][0]), sh["W"], sh["H"]
    dx = dx_mm * 1e-3
    nx, ny = int(round(W / dx)), int(round(H / dx))
    idx = np.arange(nx * ny).reshape(ny, nx)
    rows, cols, vals = [], [], []
    diag = np.full(nx * ny, (b.h_top + b.h_bottom) * dx * dx)
    for a_, c_ in ((idx[:, :-1], idx[:, 1:]), (idx[:-1, :], idx[1:, :])):
        rows += [a_.ravel(), c_.ravel()]
        cols += [c_.ravel(), a_.ravel()]
        vals += [np.full(a_.size, -S)] * 2
        diag[a_.ravel()] += S
        diag[c_.ravel()] += S
    ge = 1.0 / (dx / (2 * S * dx) + 1.0 / (sh["h_eff"] * slab * dx))     # the edge: h_eff s per metre behind half a cell of sheet
    for edge in (idx[:, 0], idx[:, -1], idx[0, :], idx[-1, :]):
        diag[edge] += ge
    xs, ys = (np.arange(nx) + 0.5) * dx, (np.arange(ny) + 0.5) * dx
    ht = p.heaters[0]
    x1, x2, y1, y2 = analytic._equivalent_rectangle(ht.polygon, W, H)
    fx = np.clip(np.minimum(xs + dx / 2, x2) - np.maximum(xs - dx / 2, x1), 0, None) / dx
    fy = np.clip(np.minimum(ys + dx / 2, y2) - np.maximum(ys - dx / 2, y1), 0, None) / dx
    src = (ht.power / ((x2 - x1) * (y2 - y1)) * np.outer(fy, fx) * dx * dx).ravel()
    K = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(nx * ny,) * 2).tocsr() + sp.diags(diag)
    fd = float(spla.spsolve(K.tocsc(), src).max())
    return fd, analytic.solve_steady(p, cell_mm=dx_mm).t_max - T_AMB


@pytest.mark.parametrize("pos,h_side", [("centre", 50.0), ("corner", 50.0), ("corner", 200.0)])
def test_series_against_an_independent_finite_difference_solver(pos, h_side):
    """The same sheet solved by 2D finite differences (the source in the corner needs the odd functions): within 0.1 % (measured -0.014 to -0.008 %, the finite-difference error of the 0.25 mm cell)."""
    p = _plate(40, 30, 8, h_side, layers=1, pos=pos)
    fd, series = _fd_hottest(p)
    assert series == pytest.approx(fd, rel=0.001)


# ------------------------------------------------------------------------------------------------ balance, symmetry

def test_heat_balance_with_vias_heatsink_and_edge():
    """Every watt leaves through the faces, the heatsink or the edge, with the local (Green function) corrections on and off."""
    p = _plate(60, 40, 8, 25.0, layers=4, thickness=1.6, pos="corner")
    p.add_via_array((3, 3, 11, 11), 4, 4, diameter=0.3)
    p.add_heatsink(4, 200.0, rect=(0, 0, 20, 20))
    for local in (True, False):
        r = analytic.solve_steady(p, cell_mm=1.0, local_corrections=local)
        out = r.power_out
        assert out["sides"] > 0.0
        assert sum(out.values()) == pytest.approx(r.power_in, rel=1e-6)


def test_heat_balance_with_a_metal_block():
    """The block board of the program with an edge coefficient closes its heat balance (block, faces, edge)."""
    p = Problem.new(width_mm=60, height_mm=40, layers=2, thickness_mm=1.6, copper_um=35.0, ambient=T_AMB, h_top=10.0, h_bottom=10.0, h_side=40.0)
    for layer in (1, 2):
        p.add_zone(layer, rect=(0, 0, 60, 40))
    p.add_heater(1, 3.0, rect=(8, 8, 18, 18))
    p.add_heatsink(2, 20.0, rect=(4, 4, 30, 30), thickness_mm=3.0)
    r = analytic.solve_steady(p, cell_mm=1.0)
    assert r.power_out["sides"] > 0.0 and r.power_out["blocks"] > 0.0
    assert sum(r.power_out.values()) == pytest.approx(r.power_in, rel=1e-6)


def test_edge_loss_share_matches_the_fvm():
    """The share of the heat that leaves through the edge agrees with the FVM within a few percent of the power on a small board."""
    p = _plate(40, 30, 10, 10.0)
    sim = simulate(p, SolverOptions(cell_mm=1.0, models=("fvm", "analytic")))
    share_a = sim.results["analytic"].power_out["sides"] / 2.0
    share_f = sim.results["fvm"].power_out["sides"] / 2.0
    assert abs(share_a - share_f) < 0.01


def test_mirror_symmetry_of_a_part_in_opposite_corners():
    """A part in the corner (0, 0) and the same part in the opposite corner give fields that are each other's 180 degree rotation (odd and even functions together)."""
    a = _plate(40, 30, 8, 80.0, layers=2, pos="corner")
    b = _plate(40, 30, 8, 80.0, layers=2, pos="corner")
    b.heaters[0].polygon = np.array([[40.0 - x, 30.0 - y] for x, y in a.heaters[0].polygon * 1e3]) * 1e-3
    ta = analytic.solve_steady(a, cell_mm=1.0).T
    tb = analytic.solve_steady(b, cell_mm=1.0).T
    assert np.allclose(ta, tb[:, ::-1, ::-1], atol=1e-9)


# ------------------------------------------------------------------------------------------------ against the FVM

@pytest.mark.parametrize("w,h,src,pos,hs", [(40, 30, 5, "centre", 10.0), (40, 30, 20, "centre", 10.0), (60, 40, 20, "centre", 10.0), (100, 80, 20, "centre", 10.0),
                                            (60, 40, 10, "corner", 50.0), (60, 40, 10, "corner", 200.0)])
def test_uniform_boards_against_the_fvm(w, h, src, pos, hs):
    """Measured against the FVM at 1 mm: within 0.4 % (the faces transfer was -0.3 to -0.7 % here for the centred sources and 12 to 37 % off at the corners)."""
    p = _plate(w, h, src, hs, pos=pos)
    err = 100.0 * (_rise(p, "analytic") / _rise(p, "fvm") - 1.0)
    assert abs(err) < 0.5, err


def test_edge_cooled_bar_cooler_and_monotone():
    """More edge coefficient, cooler board; the insulated board is the upper bound."""
    rises = [_rise(_plate(40, 30, 10, hs), "analytic") for hs in (None, 10.0, 50.0)]
    assert rises[0] > rises[1] > rises[2]


@pytest.mark.parametrize("n_terms", [100, 200, 600])
def test_number_of_modes_at_a_large_edge_parameter(n_terms):
    """A corner part at h_side 200 (beta about 580 1/m): 100, 200 and 600 modes agree with 300 within 5 mK (research: 1.4 mK from 60 to 600)."""
    p = _plate(60, 40, 10, 200.0, pos="corner")
    ref = analytic.solve_steady(p, cell_mm=1.0, n_terms=300).t_max
    assert analytic.solve_steady(p, cell_mm=1.0, n_terms=n_terms).t_max == pytest.approx(ref, abs=5e-3)


# ------------------------------------------------------------------------------------------------ no edge coefficient

@pytest.mark.parametrize("h_side", [None, 0.0, 1e-250])
def test_no_edge_loss_is_the_insulated_cosine_series(h_side):
    """Without an edge coefficient nothing changes: no extra key, the cosine basis, a_00 closed form; None, 0 and a vanishing coefficient give the same numbers."""
    p = _plate(60, 40, 20, h_side)
    r = analytic.solve_steady(p, cell_mm=1.0)
    sh = analytic._effective_sheet(p, 1.0)
    bx, by = analytic._bases(sh, 300)
    assert bx.cosine and by.cosine
    if not h_side:
        assert "sides" not in r.power_out
        assert np.all(sh["h_edge"] == 0.0) and sh["beta"] == 0.0
        assert sh["h_tot"] == 20.0                                    # h_top + h_bottom exactly
    assert sum(r.power_out.values()) == pytest.approx(r.power_in, rel=1e-6)
    q = _plate(60, 40, 20, None)
    assert np.array_equal(r.T, analytic.solve_steady(q, cell_mm=1.0).T)


def test_insulated_numbers_are_those_of_the_cosine_code():
    """A value stored from the cosine code before the Robin basis (develop, insulated edge, 1 mm): a 4-layer board with vias and a heatsink (the review found that this
    test stored no value; the number below was printed by develop and by the Robin branch alike until the barrel length d + 0.5 t_cu of fix/via-barrel-and-rim-uncoupling moved it
    from 71.02539703239057 (+0.091 K, 0.15 % of the rise: the sixteen vias conduct less), and the T board is pinned in test_part_across_outline)."""
    p = _plate(60, 40, 8, None, layers=4)
    p.add_via_array((26, 16, 34, 24), 4, 4, diameter=0.3)
    p.add_heatsink(4, 200.0, rect=(10, 10, 20, 20))
    r = analytic.solve_steady(p, cell_mm=1.0)
    assert r.t_max == pytest.approx(71.11675482396726, abs=1e-9)
    assert r.power_out["heatsinks"] == pytest.approx(0.5136421134196508, abs=1e-12)
    assert sum(r.power_out.values()) == pytest.approx(r.power_in, rel=1e-6)


# ------------------------------------------------------------------------------------------------ transient

def test_transient_modal_matrix_has_the_basis_wavenumbers():
    """The edge is in the basis, not in the surface coefficients: the (0, 0) row sum of the modal matrix is the faces plus S lam_00^2, and the total used for lengths
    and the time constant still holds the edge coefficients."""
    p = _plate(40, 30, 10, 10.0, layers=2)
    sh = analytic._effective_sheet(p, 1.0)
    A = analytic._modal_matrix(p, sh, 4, 1.0)
    bx, by = analytic._bases(sh, 4)
    expected = 20.0 + sh["S"].sum() * (bx.eig2[0] + by.eig2[0])
    assert A[0, 0].sum() == pytest.approx(expected, rel=1e-9)
    assert bx.eig2[0] > 0.0 and sh["beta"] > 0.0
    assert sh["h_tot"] == pytest.approx(20.0 + 10.0 * 2 * (0.040 + 0.030) * 1.6e-3 / (0.040 * 0.030), rel=1e-12)
    p0 = _plate(40, 30, 10, None, layers=2)
    A0 = analytic._modal_matrix(p0, analytic._effective_sheet(p0, 1.0), 4, 1.0)
    assert A0[0, 0].sum() == pytest.approx(20.0, rel=1e-12)


def _t63(sr):
    """!
    @brief Time to 63.2 % of the steady resistance of the first heater from a StepResponse.
    @param sr profiles.StepResponse.
    @return Tuple (t63 in s, steady resistance in K/W).
    """
    t, z, rth = np.asarray(sr.times, float), np.asarray(sr.z[0], float), float(sr.rth[0])
    target = (1.0 - math.exp(-1.0)) * rth
    k = int(np.argmax(z >= target))
    f = (target - z[k - 1]) / (z[k] - z[k - 1])
    return math.exp(math.log(t[k - 1]) + f * (math.log(t[k]) - math.log(t[k - 1]))), rth


@pytest.mark.parametrize("w,h,pos,hs", [(40, 30, "centre", 50.0), (60, 40, "corner", 50.0), (60, 40, "centre", 200.0)])
def test_step_response_against_the_fvm(w, h, pos, hs):
    """Unit step of a uniform board with edge loss: the steady resistance within 2 % and the time to 63 % within 7 % of the FVM (research: -3.3 to +6.0 %)."""
    p = _plate(w, h, 10, hs, pos=pos)
    o = lambda m: SolverOptions(models=(m,), cell_mm=2.0)         # noqa: E731
    ta, ra = _t63(step_response(p, "analytic", o("analytic")))
    tf, rf = _t63(step_response(p, "fvm", o("fvm")))
    assert ra == pytest.approx(rf, rel=0.02)
    assert ta == pytest.approx(tf, rel=0.07)


# ------------------------------------------------------------------------------------------------ warning

def test_warning_when_the_shared_edge_parameter_is_a_poor_model():
    """Fires on a one-layer board and on a two-layer board with very different copper when the edge takes more than 30 % of the loss; silent on the uniform boards
    and when the edge share is small (measured against the FVM: one layer -7.3 %, top full / bottom 0.2 -8.6 %, at h_side 200)."""
    one = _plate(60, 40, 10, 200.0, layers=1, pos="corner")
    assert any("edge convection" in w for w in analytic.solve_steady(one, cell_mm=1.0).warnings)
    two = _plate(60, 40, 10, 200.0, layers=2, pos="corner")
    two.zones[1].fill = 0.2
    assert any("edge convection" in w for w in analytic.solve_steady(two, cell_mm=1.0).warnings)
    # the same two boards with a small edge share, and the uniform boards, stay silent
    for p in (_plate(60, 40, 10, 10.0, layers=1, pos="corner"), _plate(60, 40, 10, 200.0, layers=2, pos="corner"), _plate(60, 40, 10, 200.0, layers=4, pos="corner")):
        assert not any("edge convection" in w for w in analytic.solve_steady(p, cell_mm=1.0).warnings)
    two_small = _plate(60, 40, 10, 10.0, layers=2, pos="corner")
    two_small.zones[1].fill = 0.2
    assert not any("edge convection" in w for w in analytic.solve_steady(two_small, cell_mm=1.0).warnings)


# ------------------------------------------------------------------------------------------------ outline, hostile input

def _t_board(h_side):
    """!
    @brief The T of the frozen-number boards (80 x 60 mm box, 2 layers of full copper, a 10 mm part of 4 W in the stem).
    @param h_side Edge coefficient in W/m2K (None = insulated).
    @return Problem.
    """
    p = Problem.new(width_mm=80, height_mm=60, layers=2, thickness_mm=1.6, copper_um=35.0, ambient=T_AMB, h_top=10.0, h_bottom=15.0, h_side=h_side)
    p.set_outline([[0, 60], [0, 40], [30, 40], [30, 0], [50, 0], [50, 40], [80, 40], [80, 60]])
    for layer in (1, 2):
        p.add_zone(layer, rect=(0, 0, 80, 60))
    p.add_heater(1, 4.0, rect=(35, 10, 45, 20))
    return p


def test_outline_uses_the_perimeter_of_the_real_edge():
    """On a board with an outline the Analytic runs on the rectangle of the same area, but the edge that loses heat is the real one:
    280 mm for the T against 198 mm for the rectangle. The heat through the edge agrees with the FVM on the real shape within 10 % of it (6.6 % short here: the
    rectangle puts the part in a different place; with the rectangle's own perimeter it would be 30 % short)."""
    eq, _ = _t_board(10.0).equivalent_rectangle()
    assert eq.board.edge_perimeter == pytest.approx(0.280, rel=1e-12)
    sim = simulate(_t_board(10.0), SolverOptions(cell_mm=1.0, models=("fvm", "analytic")))
    side_a = sim.results["analytic"].power_out["sides"]
    side_f = sim.results["fvm"].power_out["sides"]
    assert side_a == pytest.approx(side_f, rel=0.10)
    assert sum(sim.results["analytic"].power_out.values()) == pytest.approx(4.0, rel=1e-6)
    # the perimeter is not a saved field: a board without outline uses its box
    q = Problem.new(width_mm=40, height_mm=30, layers=2, thickness_mm=1.6, copper_um=35.0, h_side=10.0)
    assert getattr(q.equivalent_rectangle()[0].board, "edge_perimeter", None) is None


@pytest.mark.parametrize("h_side,balance", [(1e-9, 1e-6), (1e-3, 1e-6), (1e4, 1e-6), (1e5, 1e-3)])
def test_extreme_edge_coefficients_run_and_balance(h_side, balance):
    """A tiny or a huge edge coefficient does not stop the model: finite field, the temperature between ambient and the insulated board, and the heat balance closed
    (to 1e-6 up to 1e4 W/m2K, to 1e-3 at 1e5, the largest value `Board.validate` accepts; larger ones are refused, see below)."""
    p = _plate(40, 30, 10, h_side, pos="corner")
    r = analytic.solve_steady(p, cell_mm=1.0)
    assert np.all(np.isfinite(r.T))
    if balance:
        assert sum(r.power_out.values()) == pytest.approx(r.power_in, rel=balance)
    insulated = analytic.solve_steady(_plate(40, 30, 10, None, pos="corner"), cell_mm=1.0).t_max
    assert T_AMB < r.t_max <= insulated + 1e-9
    if h_side <= 1e-3:
        assert r.t_max == pytest.approx(insulated, rel=1e-4)


@pytest.mark.parametrize("h_side", [1e6, 1e12])
def test_huge_edge_coefficient_is_refused(h_side):
    """An edge coefficient above 1e5 W/m2K is refused (maintainer decision), where the truncation error of the series made the closure poor."""
    with pytest.raises(ValueError, match="must not exceed"):
        analytic.solve_steady(_plate(40, 30, 10, h_side), cell_mm=1.0)


def test_not_a_number_edge_coefficient_is_refused():
    """A NaN edge coefficient is an input error, not a silent insulated edge."""
    p = _plate(40, 30, 10, float("nan"))
    with pytest.raises(ValueError):
        analytic.solve_steady(p, cell_mm=1.0)


@pytest.mark.parametrize("h_side", [float("nan"), float("inf"), -1.0])
@pytest.mark.parametrize("model", ["fvm", "analytic"])
def test_bad_edge_coefficient_is_refused_by_the_board(h_side, model):
    """Board.validate refuses a NaN, infinite or negative edge coefficient for every model (the review found that the FVM ran a negative one, the edge acting as
    a heat source, 170.33 degC against 169.41 for the insulated board at 1 mm, and that only the Analytic refused it, from inside its basis)."""
    p = _plate(40, 30, 10, h_side, pos="corner")
    with pytest.raises(ValueError, match="edge heat transfer coefficient"):
        p.validate()
    with pytest.raises(ValueError):
        simulate(p, SolverOptions(cell_mm=2.0, models=(model,)))


# ------------------------------------------------------------------------------------------------ the published formula

def _eq21(a, b, c, d, t, k, h, he, n=300):
    """!
    @brief Equation 21 of Muzychka, Culham and Yovanovich (2003, Part II): total resistance of the edge-cooled rectangular flux channel (source 2a x 2b at the centre of the top
           face, adiabatic top elsewhere, film h on the bottom, edge coefficient he on the four edges), written from the eigenvalues delta tan delta = he c / k.
    @param a Half width of the source along x in m.
    @param b Half width of the source along y in m.
    @param c Half width of the channel along x in m.
    @param d Half width of the channel along y in m.
    @param t Thickness in m.
    @param k Conductivity in W/mK.
    @param h Bottom film coefficient in W/m2K.
    @param he Edge coefficient in W/m2K.
    @param n Terms per direction.
    @return float Resistance in K/W.
    """
    from scipy.optimize import brentq
    roots = lambda bi: np.array([brentq(lambda x: x * np.tan(x) - bi, j * np.pi + 1e-14, j * np.pi + 0.5 * np.pi - 1e-12, xtol=1e-14) for j in range(n)])   # noqa: E731
    dx, dy = roots(he * c / k), roots(he * d / k)
    lx, ly = dx / c, dy / d
    beta = np.sqrt(lx[:, None] ** 2 + ly[None, :] ** 2)
    hk = h / k
    phi = (beta + hk * np.tanh(beta * t)) / (hk + beta * np.tanh(beta * t))
    num = (np.sin(dx * a / c) ** 2)[:, None] * (np.sin(dy * b / d) ** 2)[None, :] * phi
    den = dx[:, None] * dy[None, :] * beta * ((np.sin(2 * dx) / 2 + dx)[:, None]) * ((np.sin(2 * dy) / 2 + dy)[None, :])
    return float(c * d / (k * a ** 2 * b ** 2) * (num / den).sum())


@pytest.mark.parametrize("k,t,he", [(385.0, 0.2e-3, 50.0), (385.0, 1e-3, 200.0), (385.0, 1e-3, 1000.0), (50.0, 0.2e-3, 200.0), (50.0, 1e-3, 1000.0)])
def test_thin_sheet_series_against_equation_21(k, t, he):
    """The sheet solved with the program's basis (S = k t, bottom film h, edge parameter he / k) is the thin-sheet limit of equation 21 of the paper: within 1.5 %
    (measured on these five -0.03 to -1.1 %, the largest at k 50, t 1 mm, Bi_e 0.5; the paper's channel keeps the through-thickness variation that no layered model has)."""
    a = b = 5e-3
    c = d = 25e-3
    h = 100.0
    r21 = _eq21(a, b, c, d, t, k, h, he)
    n = 400
    bx, by = analytic._EdgeBasis(2 * c, he / k, n), analytic._EdgeBasis(2 * d, he / k, n)
    px, py = bx.project(c - a, c + a), by.project(d - b, d + b)
    amp = np.outer(px / bx.norm, py / by.norm) / (4 * a * b) / (k * t * (bx.eig2[:, None] + by.eig2[None, :]) + h)
    sheet = float((amp * np.outer(px, py)).sum() / (4 * a * b))
    assert sheet == pytest.approx(r21, rel=0.015)
