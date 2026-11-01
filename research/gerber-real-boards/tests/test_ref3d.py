#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_ref3d.py
@brief Tests of the independent 3D reference (lib/ref3d.py): a one-dimensional series circuit, the energy balance, the isotropic case against tests/helpers/layered3d.py, and the convergence in the number of sub-slabs.
"""

import sys
from pathlib import Path

import numpy as np

import ref3d

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tests" / "helpers"))
import layered3d      # noqa: E402  (the helper of the program's tests, imports nothing from pcbthermal)


def _board(n=12, patterned=False, n_sub=4, kxy=0.9):
    """!
    @brief A two-layer board of n x n pixels of 0.5 mm; top copper solid or with a slot, bottom solid.
    @param n Pixels per side.
    @param patterned True: a bare stripe in the top copper.
    @param n_sub Sub-slabs of the gap.
    @param kxy In-plane conductivity of the laminate.
    @return model of ref3d.build.
    """
    top = np.ones((n, n), bool)
    if patterned:
        top[:, n // 2 - 1:n // 2 + 1] = False
    return ref3d.build([top, np.ones((n, n), bool)], 0.5e-3, 35e-6, [1.53e-3], kxy_lam=kxy, kz_lam=0.3, n_sub=n_sub)


def test_series_circuit_uniform_board():
    """!@brief A uniform board heated over its whole top face is one-dimensional: the top node rise is q / (g_top + 1 / (R_down + R_bottom)) per column. @return None."""
    m = _board(n=6, n_sub=4)
    heater = np.ones((6, 6), bool)
    res = ref3d.solve(m, heater, 1.0)
    dz, kz, A = m["dz"], m["kz"][:, 0, 0], (0.5e-3) ** 2
    g_top = A / (0.1 + dz[0] / (2 * kz[0]))
    r_down = sum(dz[k] / (2 * kz[k] * A) + dz[k + 1] / (2 * kz[k + 1] * A) for k in range(len(dz) - 1))
    g_bot = A / (0.1 + dz[-1] / (2 * kz[-1]))
    q = 1.0 / 36
    expect = q / (g_top + 1.0 / (r_down + 1.0 / g_bot))
    assert abs(res["top"][2, 2] / expect - 1) < 1e-9


def test_energy_balance():
    """!@brief The heat leaving through the two films equals the heat in, on a patterned board with a small heater. @return None."""
    m = _board(n=16, patterned=True)
    h = np.zeros((16, 16), bool)
    h[4:8, 3:7] = True
    res = ref3d.solve(m, h, 2.5)
    assert abs(res["heat_out"] / 2.5 - 1) < 1e-9


def test_isotropic_against_layered3d():
    """!@brief With an isotropic laminate and a patterned top layer the mean rise of the heated cells agrees with the helper solver of the program's tests within 1e-5. @return None."""
    n = 16
    m = _board(n=n, patterned=True, n_sub=4, kxy=0.3)
    h = np.zeros((n, n), bool)
    h[4:8, 2:6] = True
    res = ref3d.solve(m, h, 1.0)
    dx = 0.5e-3
    bare = np.isin(np.arange(n), [n // 2 - 1, n // 2])[None, :] * np.ones((n, 1), bool)
    top_k = np.where(bare, 0.3, 385.0)
    slabs = [(35e-6, top_k, 1), (1.53e-3, 0.3, 4), (35e-6, 385.0, 1)]
    ref = layered3d.solve(dx, n, n, slabs, (2 * dx, 4 * dx, 6 * dx, 8 * dx), 1.0, 10.0, 10.0, film_under_source=True)
    mine = res["top"][h].mean()
    assert abs(mine / ref["cell_mean_source"] - 1) < 1e-5, (mine, ref["cell_mean_source"])      # measured 4.5e-7 (review): the same scheme, so far tighter than the 1 % of the first version


def test_convergence_in_subslabs():
    """!@brief The sub-slabs of the gap converge: 8 against 16 differ by under 0.5 % in the heater mean, and 2 against 16 by more (the laminate carries heat sideways beside the bare stripe). @return None."""
    n = 20
    h = np.zeros((n, n), bool)
    h[8:12, 4:8] = True
    v = {k: ref3d.solve(_board(n=n, patterned=True, n_sub=k), h, 1.0)["top"][h].mean() for k in (2, 8, 16)}
    assert abs(v[8] / v[16] - 1) < 0.005, v
    assert abs(v[2] / v[16] - 1) > abs(v[8] / v[16] - 1), v


def test_cg_matches_direct():
    """!@brief The conjugate-gradient path gives the direct answer (a check of the factorisation). @return None."""
    m = _board(n=10, patterned=True, n_sub=2)
    h = np.zeros((10, 10), bool)
    h[3:5, 3:5] = True
    a = ref3d.solve(m, h, 1.0)["top"]
    b = ref3d.solve(m, h, 1.0, method="cg")["top"]
    assert np.abs(a - b).max() < 1e-6 * a.max()


def _series_top(slabs_bottom_up, a, x0, x1, h, power, modes=300, mid=False):
    """!
    @brief Closed form of the steady rise of a layered square block (adiabatic sides, film h on both faces, uniform flux on a centred square of the top), averaged over the heated square.
    @details Cosine series in the plane; through the thickness every slab is anisotropic (k_xy, k_z) and is crossed by its exact transfer matrix of (T, k_z dT/dz), mode by mode
             (beta = lambda sqrt(k_xy / k_z)). With mid=True the heat is put in, and the temperature read, at the mid-plane of the top slab (the node convention of ref3d) instead of the surface.
             Written for this test from the heat equation; it shares nothing with ref3d but the problem statement.
    @param slabs_bottom_up List of (thickness m, k_xy, k_z) from the bottom face up.
    @param a Side of the block in m.
    @param x0 Lower edge of the heated square (both axes) in m.
    @param x1 Upper edge of the heated square in m.
    @param h Film coefficient of both faces in W/m2K.
    @param power Heat in W.
    @param modes Cosine modes per axis.
    @param mid True: source and reading at the mid-plane of the top slab.
    @return float, mean rise of the heated square in K.
    """
    m = np.arange(modes)
    lx = m * np.pi / a
    ix = np.where(m == 0, x1 - x0, (a / np.maximum(m, 1) / np.pi) * (np.sin(lx * x1) - np.sin(lx * x0)))
    eps = np.where(m == 0, 1.0, 2.0)
    LX, LY = np.meshgrid(lx, lx, indexing="ij")
    lam = np.sqrt(LX ** 2 + LY ** 2)

    def prop(z, g, d, kxy, kz):
        """!@brief Cross one slab: z the temperature, g = k_z dT/dz (downward flux), both per mode. @param z Temperature. @param g Flux. @param d Thickness. @param kxy In-plane k. @param kz Through k. @return tuple (z, g) on the far side, rescaled together."""
        be = lam * np.sqrt(kxy / kz)
        c, s = np.cosh(be * d), np.sinh(be * d)
        sk = np.where(be > 0, s / (kz * np.where(be > 0, be, 1.0)), d / kz)
        zn, gn = z * c + g * sk, z * kz * be * s + g * c
        sc = np.maximum(np.abs(zn), 1.0)                       # scale both: only their ratio matters
        return zn / sc, gn / sc

    z, g = np.ones_like(lam), np.full_like(lam, h)             # bottom face: k_z dT/dz = h T
    *below, (d, kxy, kz) = slabs_bottom_up
    for s in below:
        z, g = prop(z, g, *s)
    if mid:
        z, g = prop(z, g, d / 2.0, kxy, kz)
        zu, uu = prop(np.ones_like(lam), np.full_like(lam, h), d / 2.0, kxy, kz)   # from the top face down to the mid-plane (upward flux into the film)
        resp = zu / (g * zu / z + uu)                          # the source splits between the two sides; T continuous at the plane
    else:
        z, g = prop(z, g, d, kxy, kz)
        resp = z / (g + h * z)
    q = np.outer(eps * ix, eps * ix) / (a * a) * power / (x1 - x0) ** 2
    return float((q * resp * np.outer(ix, ix) / (x1 - x0) ** 2).sum())


def test_anisotropic_against_closed_form():
    """!@brief Uniform layers with the anisotropic FR-4 of the study (0.9 / 0.3): full copper on both layers and a bare top on a solid bottom, against the closed form (review of README 10). @return None."""
    a, pix, x0, x1 = 6e-3, 0.1e-3, 1.8e-3, 4.2e-3
    n = int(round(a / pix))
    xs = (np.arange(n) + 0.5) * pix
    hm = (xs[None, :] > x0) & (xs[None, :] < x1) & (xs[:, None] > x0) & (xs[:, None] < x1)
    lam, cu, tc, gap = (0.9, 0.3), (385.0, 385.0), 35e-6, 1.53e-3
    for top, slabs, tol in ((True, [(tc,) + cu, (gap,) + lam, (tc,) + cu], 1e-3), (False, [(tc,) + cu, (gap,) + lam, (tc,) + lam], 3e-3)):
        m = ref3d.build([np.full((n, n), top), np.ones((n, n), bool)], pix, tc, [gap], n_sub=16)      # 16: the bare top converges slowly in the slabs (on this board 8 slabs 0.31 %, 16 0.10 %, 32 0.04 %)
        mine = ref3d.solve(m, hm, 1.0)["top"][hm].mean()
        exact = _series_top(slabs, a, x0, x1, 10.0, 1.0, mid=True)
        assert abs(mine / exact - 1) < tol, (top, mine, exact)
