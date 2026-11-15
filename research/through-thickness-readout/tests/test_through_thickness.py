#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_through_thickness.py
@brief Tests of the through-thickness investigation: the closed forms of the read-out, the parabolic read-out and the sub-layer emulation against the independent 3D solver, the energy balance
       of the stack, the patched 3D solid equal to the program's at one slab, and the size of the term on 35 um copper.
@details Run from the repository root: .venv/bin/python -m pytest -q research/through-thickness-readout/tests   (about 15 s, under 1 GB)
"""

import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
for p in (ROOT, os.path.join(HERE, "..", "lib"), os.path.join(ROOT, "tests", "helpers")):
    sys.path.insert(0, p)
import layered3d as L                                          # noqa: E402
import solid3d_sublayers                                       # noqa: E402
import sublayers                                               # noqa: E402
import surface_readout as sr                                   # noqa: E402
from pcbthermal import SolverOptions, simulate, solid3d        # noqa: E402

W, T, K, H, P = 20.0, 2.0, 150.0, 400.0, 5.0                   # a small plate: mm, mm, W/mK, W/m2K, W
RECT = (6.0, 6.0, 14.0, 14.0)
CENTRE = (slice(9, 11), slice(9, 11))                          # the four cells around the centre of the 1 mm grid


def reference():
    """!
    @brief The independent 3D solution of the small plate: surface and column mean at the centre.
    @return Tuple (surface, column mean) in K above the ambient.
    """
    r = L.solve(1e-3, 20, 20, [(T * 1e-3, K, 8)], tuple(v * 1e-3 for v in RECT), P, 0.0, H)
    dz = np.array(r["dz"])
    col = np.tensordot(dz / dz.sum(), r["T"], axes=(0, 0))
    return float(r["surface_top"][CENTRE].mean()), float(col[CENTRE].mean())


def test_offsets_closed_forms():
    """!
    @brief The parabola gives q t/2k for a column and q t/3k when nothing leaves through the other face; the two faces add up to (q_top + q_bot) t / 6k.
    """
    t, k, q = 1e-3, 100.0, 5e4
    d_top, d_bot = sr.offsets(t, k, q, -q)
    assert d_top == pytest.approx(q * t / (2 * k), rel=1e-12) and d_bot == pytest.approx(-q * t / (2 * k), rel=1e-12)
    assert sr.offsets(t, k, q, 0.0)[0] == pytest.approx(q * t / (3 * k), rel=1e-12)
    a, b = sr.offsets(t, k, 3e4, -1e4)
    assert a + b == pytest.approx((3e4 - 1e4) * t / (6 * k), rel=1e-12)
    assert sr.column_bound(t, k, -q) == pytest.approx(q * t / (2 * k))


def test_parabola_against_independent_3d():
    """!
    @brief For t/a = 0.25 the parabolic read-out matches the independent 3D difference (surface minus column mean) within 8 %.
    """
    surf, col = reference()
    q = P / (8e-3 * 8e-3)
    d, _ = sr.offsets(T * 1e-3, K, q, sr.bottom_flux(col, H, T * 1e-3, K))
    assert d == pytest.approx(surf - col, rel=0.08)
    assert sr.column_bound(T * 1e-3, K, q) > 1.2 * (surf - col)        # the bound is not the read-out: it overshoots by a third


@pytest.mark.parametrize("n", [1, 4])
def test_sublayer_stack_conserves_and_matches_the_column_mean(n):
    """!
    @brief The stack of n sub-layers conserves the power and its column mean equals the independent column mean within 0.1 K (the plate, 33 K rise).
    @param n Sub-layers.
    """
    surf, col = reference()
    p = sublayers.stack_problem(n, W, W, T, K, H, sources=[(RECT, P)], ambient=0.0)
    r = simulate(p, SolverOptions(models=("fvm",), cell_mm=1.0)).results["fvm"]
    assert sum(r.power_out.values()) == pytest.approx(P, rel=1e-9)
    Tn = np.asarray(r.T)
    assert Tn.mean(axis=0)[CENTRE].mean() == pytest.approx(col, abs=0.1)


def test_sublayers_surface_converges_to_the_3d_surface():
    """!
    @brief Option B: top sub-layer node plus half a sub-layer reads the 3D surface within 0.05 K at N = 4 (the bound read-out of N = 1 is 0.15 K high).
    """
    surf, col = reference()
    q = P / (8e-3 * 8e-3)
    err = {}
    for n in (1, 4):
        p = sublayers.stack_problem(n, W, W, T, K, H, sources=[(RECT, P)], ambient=0.0)
        Tn = np.asarray(simulate(p, SolverOptions(models=("fvm",), cell_mm=1.0)).results["fvm"].T)
        err[n] = float(Tn[0][CENTRE].mean() + q * (T * 1e-3 / n) / (2 * K) - surf)
    assert abs(err[4]) < 0.05 < abs(err[1])


def test_patched_solid_is_the_program_at_one_slab_and_resolves_at_four():
    """!
    @brief The text-patched 3D solid with one copper slab is identical to the program's; with four slabs the column mean is unchanged within 0.05 K and the top slab is hotter.
    """
    p = sublayers.stack_problem(1, W, W, T, K, H, sources=[(RECT, P)], ambient=0.0)
    a = solid3d.Solid(p, 1.0).solve()[0]
    b = solid3d_sublayers.load(1).Solid(p, 1.0).solve()[0]
    assert np.abs(a - b).max() == 0.0
    net = solid3d_sublayers.load(4).Solid(p, 1.0)
    th = net.solve()[0]
    i = net.board_slab[0]
    assert th[i:i + 4][:, CENTRE[0], CENTRE[1]].mean() == pytest.approx(a[net.board_slab[0]][CENTRE].mean(), abs=0.05)
    assert th[i][CENTRE].mean() > th[i + 3][CENTRE].mean() + 0.1


def test_thin_copper_term_is_millikelvin():
    """!
    @brief 35 um copper, a 2 W part on 5 x 5 mm: the bound q t / (2 k) is below 5 mK, 1e-4 of a 50 K rise, so a read-out that replaces the node changes every frozen record (tolerance 1e-8 K).
    """
    q = 2.0 / (5e-3 * 5e-3)
    b = float(sr.column_bound(35e-6, 385.0, q))
    assert 1e-8 < b < 5e-3
