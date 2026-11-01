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
    """!@brief With an isotropic laminate and a patterned top layer the mean rise of the heated cells agrees with the helper solver of the program's tests within 1 %. @return None."""
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
    assert abs(mine / ref["cell_mean_source"] - 1) < 0.01, (mine, ref["cell_mean_source"])


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
