#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_solid3d_copper_slabs.py
@brief A copper layer thicker than 105 um is cut into ceil(t / 70 um) slabs (at most 8) in the 3D solid: the rule (equal to the FEM's), the counts and the memory law, the thickness, a
       closed-form 1D profile through a thick plate, the place where a part puts its heat, the energy balance, two plates against the independent 3D solver (tests/helpers/layered3d.py).
"""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "helpers"))
import layered3d as L3                                         # noqa: E402

from pcbthermal import Problem, femmesh, memory, solid3d       # noqa: E402
from pcbthermal.model import Materials                         # noqa: E402

GB = 1024.0 ** 3


def board(layers=2, copper_um=35.0, heater_layer=1, size=20.0, power=2.0):
    """!
    @brief A small board with a square part at the centre, films on both faces and insulated sides.
    @param layers Copper layers, count.
    @param copper_um Copper thickness of every layer, um (the board thickness grows so that the gaps stay as they are).
    @param heater_layer Layer of the part, 1 is the top.
    @param size Side of the board, mm.
    @param power Power of the part, W.
    @return Problem.
    """
    p = Problem.new(size, size, layers=layers, thickness_mm=1.6 + layers * (copper_um - 35.0) * 1e-3, copper_um=copper_um)
    p.board.h_top = p.board.h_bottom = 500.0
    p.board.h_side = None
    c = size / 2.0
    p.add_heater(heater_layer, power, rect=(c - 2.0, c - 2.0, c + 2.0, c + 2.0), name="U")
    p.add_full_copper(layers=None)
    return p


def test_the_rule_is_the_rule_of_the_fem():
    """One slab up to 105 um, ceil(t / 70 um) above it, at most 8: the same function of the thickness as femmesh.copper_slab_count, so the two models cut a plate alike."""
    for t_um in (17.5, 35.0, 70.0, 105.0, 105.5, 140.0, 141.0, 210.0, 350.0, 420.0, 560.0, 561.0, 3000.0, 10000.0):
        assert solid3d.copper_slab_count(t_um * 1e-6) == femmesh.copper_slab_count(t_um * 1e-6)
    assert [solid3d.copper_slab_count(t * 1e-6) for t in (35, 70, 105, 140, 210, 350, 560, 2000)] == [1, 1, 1, 2, 3, 5, 8, 8]


def test_thin_copper_is_unchanged_and_thick_copper_adds_slabs():
    """A 35 or 70 um board has the slabs it had (L copper slabs and the gap slabs); 420 um adds 5 slabs to every layer."""
    for um in (35.0, 70.0, 105.0):
        p = board(copper_um=um)
        assert solid3d.unknowns(p, 2.0)[1] == 2 + solid3d.slabs_per_gap(p)[0]
    p = board(copper_um=420.0)
    assert solid3d.unknowns(p, 2.0)[1] == 2 * 6 + solid3d.slabs_per_gap(p)[0]
    p = board(layers=4, copper_um=140.0)
    assert solid3d.unknowns(p, 2.0)[1] == 4 * 2 + sum(solid3d.slabs_per_gap(p))


def test_unknowns_counts_the_model_that_is_built_with_thick_copper():
    """The count the memory guard sees is the count of the matrix, with thick copper too (two layers, four layers, a one-layer board)."""
    for p in (board(copper_um=210.0), board(layers=4, copper_um=140.0), board(layers=1, copper_um=350.0)):
        for cell in (2.0, 3.3):
            n, ns, nx, ny = solid3d.unknowns(p, cell)
            net = solid3d.Solid(p, cell)
            assert (n, ns, nx, ny) == (net.n, net.ns, net.nx, net.ny)


def test_the_slabs_of_a_layer_add_up_to_its_thickness():
    """The sub-slabs of a layer are equal and their thicknesses sum to the copper thickness; the whole stack is as thick as the board."""
    p = board(layers=3, copper_um=300.0)
    net = solid3d.Solid(p, 2.0)
    tc = np.asarray(p.board.copper_thickness)
    for l, cs in enumerate(net.copper_slabs):
        assert len(cs) == solid3d.copper_slab_count(tc[l])
        dz = np.array([net.slabs[s]["dz"][5, 5] for s in cs])
        assert np.allclose(dz, tc[l] / len(cs), rtol=1e-12) and abs(dz.sum() - tc[l]) < 1e-15
        assert net.board_slab[l] == cs[0]
    total = sum(float(sl["dz"][5, 5]) for sl in net.slabs)
    assert abs(total - float(p.board.slab_thicknesses().sum())) < 1e-12


def test_a_part_on_an_outer_layer_feeds_the_outer_slab_and_an_inner_part_all_of_them():
    """The heat of a part on a thick outer layer enters the slab of the face it sits on; on an inner layer it is spread over the slabs (thin copper keeps its one slab)."""
    top = solid3d.Solid(board(copper_um=350.0, heater_layer=1), 2.0)
    q = top.Q.reshape(top.ns, top.ny, top.nx).sum(axis=(1, 2))
    assert q[top.copper_slabs[0][0]] == pytest.approx(2.0, abs=1e-12) and abs(q.sum() - 2.0) < 1e-12 and np.count_nonzero(q) == 1
    bottom = solid3d.Solid(board(copper_um=350.0, heater_layer=2), 2.0)
    q = bottom.Q.reshape(bottom.ns, bottom.ny, bottom.nx).sum(axis=(1, 2))
    assert q[bottom.copper_slabs[1][-1]] == pytest.approx(2.0, abs=1e-12) and np.count_nonzero(q) == 1
    inner = solid3d.Solid(board(layers=4, copper_um=210.0, heater_layer=2), 2.0)
    q = inner.Q.reshape(inner.ns, inner.ny, inner.nx).sum(axis=(1, 2))
    assert [q[s] for s in inner.copper_slabs[1]] == pytest.approx([2.0 / 3] * 3, abs=1e-12) and np.count_nonzero(q) == 3
    thin = solid3d.Solid(board(copper_um=35.0), 2.0)
    q = thin.Q.reshape(thin.ns, thin.ny, thin.nx).sum(axis=(1, 2))
    assert q[thin.board_slab[0]] == pytest.approx(2.0, abs=1e-12) and np.count_nonzero(q) == 1


def test_a_uniformly_heated_plate_is_a_straight_line_through_the_copper():
    """Closed form (the regression of this branch): a one-layer board heated over its whole area is 1D. The copper slabs sit on the line T(z) = T_amb + q (1 / h + t_lam / k_lam + (t - z) / k_cu), z from the top face, and their
    mean is the column. With one slab (the earlier model) the mean was right and the profile was not there."""
    t_cu, w = 3.0e-3, 12.0e-3
    p = Problem.new(w * 1e3, w * 1e3, layers=1, thickness_mm=3.2, copper_um=t_cu * 1e6, ambient=20.0, h_top=1e-6, h_bottom=250.0, h_side=None)
    p.add_full_copper(layers=None)
    P = 6.0
    p.add_heater(1, P, rect=(0.0, 0.0, w * 1e3, w * 1e3), name="U")
    net = solid3d.Solid(p, 2.0)
    theta, res = net.solve()
    m = p.board.materials
    q = P / (w * w)
    t_lam = float(p.board.slab_thicknesses()[0] - t_cu)
    n = len(net.copper_slabs[0])
    assert n == 8
    z = (np.arange(n) + 0.5) * t_cu / n
    expect = q * (1.0 / 250.0 + t_lam / m.k_fr4_through + (t_cu - z) / m.k_copper)
    got = theta[net.copper_slabs[0]][:, 2, 2]
    assert got == pytest.approx(expect, rel=1e-6)
    assert res < 1e-9 and got[0] > got[-1] + 0.5 * q * t_cu * (n - 1) / n / m.k_copper / 2          # the profile is there: the face slab is hotter than the inner one


def test_energy_balance_with_thick_copper_on_both_faces_and_inside():
    """The heat the films carry away equals the power, with the parts on the top, on an inner and on the bottom thick layer, a via and a thick plain heatsink."""
    p = board(layers=4, copper_um=210.0, heater_layer=1, size=24.0)
    p.add_heater(2, 1.5, rect=(3, 3, 7, 7), name="V")
    p.add_heater(4, 1.0, rect=(14, 14, 18, 18), name="W")
    p.add_via(12.0, 12.0, diameter=0.5)
    net = solid3d.Solid(p, 1.0)
    theta, res = net.solve()
    th = theta.ravel()
    lost = sum(float((g * th).sum()) for g in net.g.values()) + float((net.g_leak * th).sum())
    assert abs(net.Q.sum() - 4.5) < 1e-12
    assert abs(lost - net.Q.sum()) < 1e-8 * net.Q.sum() and res < 1e-9


def plate_solid_and_reference(kind, t_mm, k, a_mm, power, h, dx=1.0, w=50.0):
    """!
    @brief A plate as a Problem of the program and as the independent 3D solution (the 8 equal sub-slabs of the program through the thick metal).
    @param kind "one" for a metal plate (with the 1 um laminate that Problem.new gives it) or "two" for a plate on 1 mm of FR-4 with a 35 um bottom copper.
    @param t_mm Thickness of the metal, mm.
    @param k Conductivity of the metal, W/mK.
    @param a_mm Side of the square source, mm.
    @param power Power, W.
    @param h Film under the bottom, W/m2K.
    @param dx Cell, mm.
    @param w Side of the plate, mm.
    @return Tuple (column maximum under the source of the 3D solid in K, the same of the independent solver in K).
    """
    mat = Materials(k_copper=k, k_fr4_through=0.3, k_fr4_inplane=0.3)
    if kind == "one":
        p = Problem.new(w, w, layers=1, thickness_mm=1.0001 * t_mm, copper_um=t_mm * 1e3, ambient=0.0, h_top=1e-6, h_bottom=h, h_side=None, materials=mat)
    else:
        p = Problem.new(w, w, layers=2, thickness_mm=t_mm + 1.035, copper_um=35.0, ambient=0.0, h_top=1e-6, h_bottom=h, h_side=None, materials=mat)
        p.board.copper_thickness = [t_mm * 1e-3, 35e-6]
    p.add_full_copper(layers=None)
    c = w / 2.0
    rect = (c - a_mm / 2, c - a_mm / 2, c + a_mm / 2, c + a_mm / 2)
    p.add_heater(1, power, rect=rect, name="S")
    net = solid3d.Solid(p, dx)
    theta, _ = net.solve()
    cols = theta[net.copper_slabs[0]].mean(axis=0)
    mask = net.Q.reshape(net.ns, net.ny, net.nx)[net.copper_slabs[0][0]] > 0
    n = int(round(w / dx))
    if kind == "one":
        t_lam = float(p.board.slab_thicknesses()[0] - p.board.copper_thickness[0])
        slabs = [(t_mm * 1e-3, k, solid3d.copper_slab_count(t_mm * 1e-3)), (t_lam, 0.3, solid3d.slabs_per_gap(p)[0])]
    else:
        slabs = [(t_mm * 1e-3, k, solid3d.copper_slab_count(t_mm * 1e-3)), (1e-3, 0.3, solid3d.slabs_per_gap(p)[0]), (35e-6, k, 1)]
    r = L3.solve(dx * 1e-3, n, n, slabs, tuple(v * 1e-3 for v in rect), power, 0.0, h)
    nt = solid3d.copper_slab_count(t_mm * 1e-3)
    dz = np.array(r["dz"][:nt])
    ref = np.tensordot(dz / dz.sum(), r["T"][:nt], axes=(0, 0))
    return float(cols[mask].max()), float(ref[r["mask_source"]].max())


@pytest.mark.parametrize("kind, t_mm, k, a_mm, power, h", [("one", 10.0, 200.0, 10.0, 100.0, 1000.0), ("two", 2.0, 385.0, 4.0, 5.0, 50.0), ("one", 3.0, 385.0, 6.0, 10.0, 100.0)])
def test_thick_plates_agree_with_the_independent_3d_solver(kind, t_mm, k, a_mm, power, h):
    """!
    @brief The column under the source of a thick plate agrees with an independent 3D solver cut into the same slabs, to 1e-4 K of a rise of 40 to 50 K.
    @details The solver (tests/helpers/layered3d.py) imports nothing from the program and applies the flux on the face of the plate. The earlier model, with one slab through the metal,
             read the 10 mm aluminium plate 0.06 K away (measured in releases/2.9.0/solid3d-copper-slabs), so this tolerance would have failed it.
    @param kind "one" or "two", see plate_solid_and_reference.
    @param t_mm Thickness of the metal, mm.
    @param k Conductivity of the metal, W/mK.
    @param a_mm Side of the source, mm.
    @param power Power, W.
    @param h Film under the bottom, W/m2K.
    @return None.
    """
    got, ref = plate_solid_and_reference(kind, t_mm, k, a_mm, power, h)
    assert abs(got - ref) < 1e-4


def test_the_memory_law_follows_the_slabs_and_refuses_before_the_run(monkeypatch):
    """!
    @brief Thick copper raises the unknown count the law is applied to, so a machine that holds the 35 um board can refuse the 420 um one, before anything is built.
    @param monkeypatch pytest fixture.
    @return None.
    """
    thin, thick = board(layers=2, copper_um=35.0, size=100.0), board(layers=2, copper_um=420.0, size=100.0)
    n_thin, n_thick = solid3d.unknowns(thin, 1.0)[0], solid3d.unknowns(thick, 1.0)[0]
    assert n_thick > n_thin
    cells = 100 * 100
    e_thin = memory.estimate_bytes("solid3d", n_thin, cells, base=0.0)
    e_thick = memory.estimate_bytes("solid3d", n_thick, cells, base=0.0)
    assert e_thick > e_thin
    ram = int((e_thin * e_thick) ** 0.5 / 0.5)                   # a limit (half of this "RAM", fraction 0.5) between the two estimates, far from both
    monkeypatch.setenv(memory.MEMORY_ENV, str(ram))
    ok = memory.check(thin, ("solid3d",), 1.0, fraction=0.5, ram=ram, available=ram, base=0.0, refuse="return")[0]
    bad = memory.check(thick, ("solid3d",), 1.0, fraction=0.5, ram=ram, available=ram, base=0.0, refuse="return")[0]
    assert ok.verdict != "refuse" and bad.verdict == "refuse"
    with pytest.raises(memory.MemoryGuardError):
        solid3d.Solid(thick, 1.0, memory_fraction=0.5)           # the constructor checks too (api.simulate and the studies reach it)
