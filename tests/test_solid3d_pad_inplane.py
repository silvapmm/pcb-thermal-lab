#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_solid3d_pad_inplane.py
@brief The interface pad of a metal block in the 3D solid conducts across only (a contact resistance): the slab conductivities, a pad over a uniform plate against the independent anisotropic
       solver (tests/helpers/stack3d.py, itself certified against tests/helpers/layered3d.py), a closed-form column, the energy balance and the unknown count of the memory law.
"""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "helpers"))
import layered3d as L3                                         # noqa: E402
import stack3d                                                 # noqa: E402

from pcbthermal import Problem, solid3d                        # noqa: E402

CELL = 2.0
H = 10.0
HEATER = (16.0, 10.0, 24.0, 18.0)


def top_block_board(rc, rect, t_mm=5.0, power=3.0):
    """!
    @brief A 40 x 30 mm two-layer board with full copper, a part under a block on the top face.
    @param rc Contact resistance of the block in m2K/W.
    @param rect Block rectangle (x0, y0, x1, y1) in mm.
    @param t_mm Block thickness in mm.
    @param power Power of the part in W.
    @return Problem.
    """
    p = Problem.new(width_mm=40.0, height_mm=30.0, layers=2, h_top=H, h_bottom=H, h_side=None)
    p.add_full_copper([1, 2])
    p.add_heater(1, power, rect=HEATER, name="U1")
    p.add_heatsink(1, 0.0, rect=rect, name="blk", thickness_mm=t_mm, contact_r=rc)
    return p


def mask(rect, nx, ny, w=40.0, h=30.0):
    """!
    @brief Cells whose centre lies inside a rectangle.
    @param rect (x0, y0, x1, y1) in mm.
    @param nx Cells along x.
    @param ny Cells along y.
    @param w Board width in mm.
    @param h Board height in mm.
    @return Boolean array (ny, nx).
    """
    xs, ys = (np.arange(nx) + 0.5) * w / nx, (np.arange(ny) + 0.5) * h / ny
    return (xs[None, :] > rect[0]) & (xs[None, :] < rect[2]) & (ys[:, None] > rect[1]) & (ys[:, None] < rect[3])


def solid_and_reference(rc, rect):
    """!
    @brief Column maximum under the part in the 3D solid and in the independent solver with a pad that has no in-plane conduction.
    @param rc Contact resistance in m2K/W.
    @param rect Block rectangle in mm.
    @return Tuple (3D solid, independent) of rises in K.
    """
    p = top_block_board(rc, rect)
    net = solid3d.Solid(p, CELL)
    theta, _ = net.solve()
    m = mask(HEATER, net.nx, net.ny)
    got = float(theta[net.copper_slabs[0][0]][m].max())
    bm = mask(rect, net.nx, net.ny)
    hs = p.heatsinks[0]
    nb = 20
    blk = [{"dz": hs.thickness / nb, "kx": np.where(bm, hs.k, 0.0), "kz": np.where(bm, hs.k, 0.0), "wall": H} for _ in range(nb)]
    pad = {"dz": rc, "kx": 0.0, "kz": np.where(bm, 1.0, 0.0)}
    # The board slabs (copper and gap slabs: thickness and conductivity of the program's laminate model, uniform here) are read from the program once
    board = [{"dz": float(net.slabs[s]["dz"][0, 0]), "kx": float(net.slabs[s].get("kphys", net.slabs[s]["kx"])[0, 0]), "kz": float(net.slabs[s]["kz"][0, 0])}
             for s in range(net.first_board, net.last_board + 1)]
    ref = stack3d.solve(0.040 / net.nx, 0.030 / net.ny, blk + [pad] + board, len(blk) + 1, m, 3.0, H, H)
    return got, float(np.nanmax(ref["T"][len(blk) + 1][m]))


def test_the_independent_stack_solver_meets_the_layered_solver_without_a_pad():
    # Certification of the reference of this file against tests/helpers/layered3d.py on the Cu / FR-4 / Cu coupon of Culham and Yovanovich (2.5 W on a 16 mm square, h 5, 2.5 W): the same equations,
    # so they agree to the half 35 um cell between the face and the node where the flux enters (measured 0.01 %)
    n, dx = 25, 2.0e-3
    slabs = [(35.6e-6, 400.0, 1), (1.5789e-3, 0.4, 8), (35.6e-6, 400.0, 1)]
    ref = L3.solve(dx, n, n, slabs, (16.0e-3, 16.0e-3, 32.0e-3, 32.0e-3), 2.5, 5.0, 5.0, film_under_source=True)["cell_max_source"]
    m = np.zeros((n, n), bool)
    m[n // 2 - 4:n // 2 + 4, n // 2 - 4:n // 2 + 4] = True
    st = [{"dz": 35.6e-6, "kx": 400.0, "kz": 400.0}] + [{"dz": 1.5789e-3 / 8, "kx": 0.4, "kz": 0.4}] * 8 + [{"dz": 35.6e-6, "kx": 400.0, "kz": 400.0}]
    got = stack3d.solve(dx, dx, st, 0, m, 2.5, 5.0, 5.0)
    assert float(np.nanmax(got["T"][0][m])) == pytest.approx(ref, rel=1e-3)
    assert got["heat_out"] == pytest.approx(2.5, rel=1e-9)


@pytest.mark.parametrize("rect", [(12.0, 8.0, 28.0, 22.0), (0.0, 0.0, 40.0, 30.0)], ids=["block over the part", "block over the whole board"])
def test_a_pad_over_a_uniform_plate_meets_the_independent_solver(rect):
    # Measured at the 2 mm cell, rise under the part at 5e-3 m2K/W: before the fix the 3D solid read 145.47 K (block 16 x 14 mm) and 131.38 K (whole board) against 146.24 and 132.55 K of the
    # independent solver (-0.52 and -0.88 %, the pad spread the heat sideways at 1 W/mK); after, 146.23 and 132.54 K (-0.006 and -0.005 %). The bound is 0.1 %
    for rc in (5.0e-4, 5.0e-3, 5.0e-2):
        got, ref = solid_and_reference(rc, rect)
        assert got == pytest.approx(ref, rel=1.0e-3), rc


def test_the_pad_slab_conducts_across_only():
    p = top_block_board(5.0e-3, (12.0, 8.0, 28.0, 22.0))
    net = solid3d.Solid(p, CELL)
    pad = next(sl for sl in net.slabs if sl["kind"] == "pad")
    under = pad["kz"] > 1.0e-6
    assert np.all(pad["kx"][under] == pytest.approx(solid3d.K_PAD_INPLANE * 1.0))     # the cover is exact (1) on a block that lies on cell edges
    assert np.all(pad["kz"][under] == pytest.approx(solid3d.K_PAD))
    assert np.allclose(pad["dz"][under], 5.0e-3 * solid3d.K_PAD)                      # the height, hence the resistance, is unchanged
    assert solid3d.K_PAD_INPLANE <= 1.0e-2 * solid3d.K_PAD


def test_the_unknown_count_of_the_memory_law_is_unchanged():
    # The pad slab already existed: the count the guard uses is the count of the model, with one block on each face
    p = top_block_board(5.0e-3, (12.0, 8.0, 28.0, 22.0))
    p.add_heatsink(2, 0.0, rect=(8, 6, 32, 24), name="bottom", thickness_mm=3.0, contact_r=5.0e-4)
    n, ns, nx, ny = solid3d.unknowns(p, CELL)
    net = solid3d.Solid(p, CELL)
    assert (n, ns) == (net.n, net.ns)


def test_a_one_dimensional_column_and_the_energy_balance():
    # A block of 3 mm over the whole 20 x 20 mm board, insulated edges, a part over the whole top copper: the column is one-dimensional, so the pad (across only) and the closed form
    # agree whatever its in-plane conductivity; the only lateral loss is the film on the walls of the metal (h_eff = h (1 + perimeter t / A)). Node to node from the top copper
    for rc, tb in ((5.0e-4, 1.0e-3), (5.0e-3, 3.0e-3)):
        p = Problem.new(width_mm=20, height_mm=20, layers=2, h_top=30.0, h_bottom=12.0, h_side=None)
        p.add_full_copper([1, 2])
        power = 4.0
        p.add_heater(1, power, rect=(0, 0, 20, 20), name="all")
        p.add_heatsink(2, 0.0, rect=(0, 0, 20, 20), name="b", thickness_mm=tb * 1e3, contact_r=rc)
        b = p.board
        area, t, d, k = 4.0e-4, b.copper_thickness[0], b.gap_thicknesses()[0], b.materials.k_copper
        kz = b.gap_properties()[0][0]
        h_eff = b.h_bottom * (1.0 + 0.08 * tb / area)
        r_up = t / (2 * k) + 1.0 / b.h_top
        r_dn = t / (2 * k) + d / kz + t / k + rc + tb / p.heatsinks[0].k + 1.0 / h_eff
        expect = power / area * r_up * r_dn / (r_up + r_dn)
        net = solid3d.Solid(p, 5.0)
        theta, res = net.solve()
        assert float(theta[net.copper_slabs[0][0]].max()) == pytest.approx(expect, abs=0.02), (rc, tb)
        th = theta.ravel()
        lost = sum(float((g * th).sum()) for g in net.g.values()) + float((net.g_leak * th).sum())
        assert abs(lost - power) < 1e-8 * power and res < 1e-9
