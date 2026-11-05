#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_point_via.py
@brief The mean-potential via of the FVM and FDM: convergence with the cell size, energy balance, the Lumped model keeping its vias, the block SOR with the via
       couplings, the single footprint rule of the 3D solid and the warnings about vias at the board edge and at coarse cells.
@details The reference of the convergence tests is the copper-fill gain of the 3 x 3 via board (research/point-via-convergence): -4.51 K on a fine-grid solution of the
         same layered model with the vias drawn at their real size (independent solver), the program with the point link gave -4.78 K at 1 mm and -3.64 K at 0.125 mm.
"""

import copy
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest

from pcbthermal import Problem, SolverOptions, fdm, fvm, simulate, viawell
from pcbthermal.checks import check_via_limits
from pcbthermal.examples import example_board
from pcbthermal.model import Materials

GAIN_REFERENCE = -4.51        # K, fine-grid reference of the copper-fill gain of array_board (research/point-via-convergence, README 4)


def array_board(fill_k, diameter_mm=0.3, pitch_mm=3.5, n=3):
    """!
    @brief The 21 x 21 mm board of the via-fill study: four full-copper layers, a 10 x 10 mm source on top, an n x n array of vias under it.
    @param fill_k Fill conductivity in W/mK (0 open barrel, 385 copper).
    @param diameter_mm Via drill diameter in mm.
    @param pitch_mm Via pitch in mm.
    @param n Vias per side.
    @return Problem.
    """
    w = 21.0
    c = w / 2
    p = Problem.new(w, w, 4, 1.6, 35.0, h_top=10.0, h_bottom=200.0, h_side=None, materials=Materials(k_fr4_inplane=0.3))
    for layer in range(1, 5):
        p.add_zone(layer, rect=(0, 0, w, w))
    p.add_heater(1, 2.0, rect=(c - 5, c - 5, c + 5, c + 5))
    h = (n - 1) / 2
    for i in range(n):
        for j in range(n):
            p.add_via(c + (i - h) * pitch_mm, c + (j - h) * pitch_mm, diameter_mm, fill_k=fill_k)
    return p


def small_board(vias, fill_k=385.0, size=10.0, layers=3):
    """!
    @brief A small full-copper board with a source and the given vias, for the solver comparisons.
    @param vias List of (x, y, diameter) in mm.
    @param fill_k Fill conductivity in W/mK.
    @param size Side in mm.
    @param layers Copper layers.
    @return Problem.
    """
    p = Problem.new(size, size, layers, 1.6, 35.0, h_top=10.0, h_bottom=100.0, h_side=None, materials=Materials(k_fr4_inplane=0.3))
    for layer in range(1, layers + 1):
        p.add_zone(layer, rect=(0, 0, size, size))
    p.add_heater(1, 1.0, rect=(size / 2 - 1.5, size / 2 - 1.5, size / 2 + 1.5, size / 2 + 1.5))
    for x, y, d in vias:
        p.add_via(x, y, d, fill_k=fill_k)
    return p


def gain(p_open, p_cu, model, cell_mm):
    """!
    @brief Change of the maximum temperature caused by filling the vias with copper.
    @param p_open Board with open vias.
    @param p_cu Same board with copper-filled vias.
    @param model Model key.
    @param cell_mm Cell size in mm.
    @return float T_max(copper) - T_max(open) in K.
    """
    t = [simulate(p, SolverOptions(models=(model,), cell_mm=cell_mm)).results[model].t_max for p in (p_open, p_cu)]
    return t[1] - t[0]


@pytest.mark.parametrize("model", ["fvm", "fdm"])
def test_the_copper_fill_gain_converges_with_the_cell(model):
    """!
    @brief The gain stays within 0.3 K of the fine-grid reference from 1 to 0.125 mm; the point link left that band below 0.5 mm (-3.64 K at 0.125 mm).
    @param model fvm or fdm.
    @return None.
    """
    for cell in (1.0, 0.5, 0.25, 0.125):
        g = gain(array_board(0.0), array_board(385.0), model, cell)
        assert abs(g - GAIN_REFERENCE) < 0.3, (model, cell, g)


@pytest.mark.parametrize("cell", [1.0, 0.25])
def test_energy_balance_symmetry_and_zero_row_sum_of_the_via_couplings(cell):
    """!
    @brief The via blocks keep K symmetric, add no loss to the ambient, and the heat that leaves equals the power.
    @param cell Cell size in mm.
    @return None.
    """
    p = array_board(385.0)
    n = int(round(21.0 / cell))
    net = fvm.Network(p, n, n)
    theta, res = net.solve_steady()
    K = net.K
    assert abs(K - K.T).max() < 1e-12 * abs(K).max()
    assert float((net.g_amb * theta).sum()) == pytest.approx(float(net.Q.sum()), rel=1e-9)
    assert np.allclose(np.asarray(K.sum(axis=1)).ravel(), net.g_amb.ravel(), rtol=1e-9, atol=1e-12)
    assert res < 1e-9


def test_the_fdm_has_the_same_via_couplings():
    """!
    @brief The FDM matrix is symmetric, conserves the heat, and its via effect agrees with the FVM at a fine cell.
    @return None.
    """
    p = array_board(385.0)
    net = fdm.Network(p, cell_mm=0.5)
    K = net.K
    assert abs(K - K.T).max() < 1e-12 * abs(K).max()
    theta, _ = net.solve_steady()
    assert float((net.g_amb * theta).sum()) == pytest.approx(float(net.Q.sum()), rel=1e-9)
    f = simulate(p, SolverOptions(models=("fvm",), cell_mm=0.25)).results["fvm"].t_max
    d = simulate(p, SolverOptions(models=("fdm",), cell_mm=0.25)).results["fdm"].t_max
    assert abs(f - d) < 0.3


def test_a_board_without_vias_has_no_via_blocks():
    """!
    @brief No vias: no blocks, no point conductance, and the matrix is the dielectric stencil only.
    @return None.
    """
    p = array_board(0.0)
    p.vias = []
    net = fvm.Network(p, 42, 42)
    assert net.via_blocks == [] and not net.gz_via.any()


def test_the_lumped_model_keeps_its_vias():
    """!
    @brief The Lumped rings read gz + gz_via: the point barrel conductance of the cell of every via is in the ring sums (without it the vias vanish, +10 to +20 K).
    @return None.
    """
    p = example_board()
    net = fvm.Network(p, 100, 80, assemble=False)
    d = p.board.gap_thicknesses()
    m = p.board.materials
    barrel = sum(m.k_copper * v.thermal_area(p.board.via_plating, m.k_copper) / d for v in p.vias)
    assert net.gz_via.sum(axis=(1, 2)) == pytest.approx(barrel)                  # the barrel of every via, once
    assert net.gz.sum() < (net.gz + net.gz_via).sum()
    q = copy.deepcopy(p)
    q.vias = []
    with_vias = simulate(p, SolverOptions(models=("lumped",))).results["lumped"].t_max
    without = simulate(q, SolverOptions(models=("lumped",))).results["lumped"].t_max
    assert without - with_vias > 5.0


@pytest.mark.parametrize("name, vias, fill_k", [
    ("one filled via", [(5.0, 5.0, 0.3)], 8.0),
    ("0.8 mm copper-filled via", [(5.0, 5.0, 0.8)], 385.0),
    ("two vias in one cell", [(4.9, 5.0, 0.3), (5.2, 5.1, 0.3)], 385.0),
    ("array with touching footprints", [(3.0 + 1.0 * i, 3.0 + 1.0 * j, 0.5) for i in range(3) for j in range(3)], 385.0),
])
def test_sor_with_vias_equals_the_direct_solver(name, vias, fill_k):
    """!
    @brief The block SOR gives the direct solution to 1e-6 K on boards with vias (it did not converge to it when the via couplings were not seen by the sweeps).
    @param name Case name.
    @param vias List of (x, y, diameter) in mm.
    @param fill_k Fill conductivity in W/mK.
    @return None.
    """
    net = fvm.Network(small_board(vias, fill_k), 20, 20)
    direct, _ = net.solve_steady()
    sor, res, info = net.solve_sor(tol=1e-11)
    assert info["converged"], name
    assert float(np.abs(sor - direct).max()) < 1e-6, name


def test_sor_sweeps_with_vias_are_not_more_than_without():
    """!
    @brief On a dense array of vias the relaxed, coloured block step needs no more sweeps than the same board without vias (up to 5 %).
    @return None.
    """
    p = small_board([(3.0 + 1.0 * i, 3.0 + 1.0 * j, 0.5) for i in range(3) for j in range(3)])
    q = copy.deepcopy(p)
    q.vias = []
    with_vias = fvm.Network(p, 20, 20).solve_sor(tol=1e-9)[2]["iterations"]
    without = fvm.Network(q, 20, 20).solve_sor(tol=1e-9)[2]["iterations"]
    assert with_vias <= 1.05 * without


def test_sor_falls_back_to_the_direct_solver_when_a_block_is_too_large(monkeypatch):
    """!
    @brief When the dense inverse of a via block (75 n^2 bytes) is above a quarter of the memory limit the SOR solves directly and says so in its info.
    @param monkeypatch pytest fixture.
    @return None.
    """
    net = fvm.Network(small_board([(5.0, 5.0, 0.8)]), 20, 20)
    direct, _ = net.solve_steady()
    theta, res, info = net.solve_sor(memory_limit=1000.0)           # A 1 kB limit: no block fits
    assert info.get("fallback") == "direct"
    assert float(np.abs(theta - direct).max()) < 1e-9
    # The result the user sees says that the SOR was not used (it was only in the log)
    r = fvm.solve_steady(small_board([(5.0, 5.0, 0.8)]), cell_mm=0.5, method="sor", memory_limit=1000.0)
    assert r.extras.get("fallback_direct") == 1.0
    assert any("SOR not used" in w for w in r.warnings)


def test_the_footprint_keeps_only_cells_on_the_board():
    """!
    @brief A via next to a cut-away part of an outline has a footprint on the cells of the board only, weights that sum to 1.
    @return None.
    """
    cover = np.ones((20, 20))
    cover[:, 10:] = 0.0                                         # the right half is off the board
    cover[:, 9] = 0.5                                           # a cut cell
    dx = 1e-3
    w, r_eff, r_t = viawell.footprint(9.6e-3, 10e-3, 0.4e-3, dx, 0.0, cover)
    assert w and all(cover[k] > 0 for k in w)
    assert sum(w.values()) == pytest.approx(1.0)
    assert r_eff >= r_t * (1.0 - 1e-9)


def test_the_effective_radius_of_a_point_is_the_lattice_constant():
    """!
    @brief One cell: r_eff = exp(-pi kappa / 2) dx = 0.1985 dx, the equivalent radius of a point sink on the five-point lattice.
    @return None.
    """
    assert viawell.effective_radius({(0, 0): 1.0}, 1.0) == pytest.approx(0.19851, abs=1e-4)


def test_the_3d_solid_uses_one_footprint_rule_for_open_and_filled_vias():
    """!
    @brief The copper of the barrel is conserved on every cell size, and the copper-fill gain of the 3D solid stays within 0.3 K of the reference from 1 to 0.25 mm
           (the earlier rule gave -4.35 and -5.65 K at 0.5 and 0.25 mm).
    @return None.
    """
    from pcbthermal.solid3d import Solid
    for cell in (1.0, 0.5, 0.25):
        for fill in (0.0, 385.0):
            p = array_board(fill)
            s = Solid(p, int(round(21.0 / cell)), int(round(21.0 / cell)))
            a_via = p.vias[0].thermal_area(p.board.via_plating, p.board.materials.k_copper)
            assert s.via_frac.sum() * s.dx * s.dy == pytest.approx(len(p.vias) * a_via, rel=1e-9)
    for cell in (1.0, 0.5, 0.25):
        g = gain(array_board(0.0), array_board(385.0), "solid3d", cell)
        assert abs(g - GAIN_REFERENCE) < 0.3, (cell, g)


def mirror_row_board(vy, height):
    """!
    @brief A 60 mm wide board of the given height with a row of five copper-filled vias under a 4 x 2 mm source centred at height vy.
    @param vy Height of the row in mm.
    @param height Board height in mm.
    @return Problem.
    """
    p = Problem.new(60.0, height, 4, 1.6, 35.0, h_top=10.0, h_bottom=10.0, materials=Materials(k_fr4_inplane=0.3))
    for layer in range(1, 5):
        p.add_zone(layer, rect=(0, 0, 60.0, height))
    p.add_heater(1, 2.0, rect=(28.0, vy - 1.0, 32.0, vy + 1.0))
    for k in range(-2, 3):
        p.add_via(30.0 + 0.8 * k, vy, 0.3, fill_k=385.0)
    return p


@pytest.mark.parametrize("height, cell", [(41.0, 2.0), (41.3, 1.0), (41.3, 0.5)])
def test_the_footprint_rows_use_dy_when_the_cells_are_not_square(height, cell):
    """!
    @brief The board mirrored top to bottom gives the same temperature (FVM, FDM and the 3D solid's cell rows) when dy differs from dx.
    @details The grid is round(W / cell) by round(H / cell), so a 41.3 mm side at 1 mm has dy = 1.0073 mm against dx = 1 mm. The footprint used to read the
             rows with dx and put the vias up to one cell away near the top: the mirrored pair differed by 1.6 K (FVM, 2 mm), 4.7 K (FVM, 1 mm) and
             0.7 K (FDM, 0.5 mm).
    @param height Board height in mm.
    @param cell Cell size in mm.
    @return None.
    """
    for model in ("fvm", "fdm"):
        a = simulate(mirror_row_board(6.0, height), SolverOptions(models=(model,), cell_mm=cell)).results[model].t_max
        b = simulate(mirror_row_board(height - 6.0, height), SolverOptions(models=(model,), cell_mm=cell)).results[model].t_max
        assert abs(a - b) < 1e-6, (model, height, cell, a, b)
    # The footprint of the 3D solid lands on the row of the via (dy, not dx): a 1.2 mm via at 38 mm on a 41 mm board at 2 mm (dy = 2.05 mm) is in row 18
    # (read with dx it straddled rows 18 and 19)
    w = viawell.tuned_footprint(30e-3, 38e-3, 0.6e-3, 2e-3, 0.0, np.ones((20, 30)), 2.05e-3)
    assert {k[0] for k in w} == {18}


def test_warning_for_a_via_touching_the_board_edge():
    """!
    @brief A via within one cell of the edge is reported for what the mirror image of the FVM does not cover (the FDM, the 3D solid, a cell of 2 mm or more, a
           via cut by the edge); the FVM at a fine cell with a straight edge, and a via in the middle, get none.
    @return None.
    """
    edge = small_board([(0.3, 5.0, 0.3)])
    middle = small_board([(5.0, 5.0, 0.3)])
    assert not any("touching the board edge" in w for w in check_via_limits(edge, ("fvm",), 1.0))        # covered by the image
    assert any("touching the board edge" in w for w in check_via_limits(edge, ("fvm",), 2.0))            # a coarse cell
    assert any("half-volume edge nodes" in w for w in check_via_limits(edge, ("fvm", "fdm"), 1.0))
    assert any("touching the board edge" in w for w in check_via_limits(edge, ("solid3d",), 1.0))
    assert not any("touching the board edge" in w for w in check_via_limits(middle, ("fvm", "fdm", "solid3d"), 1.0))
    assert not any("touching the board edge" in w for w in check_via_limits(edge, ("lumped",), 1.0))
    # A via cut by the edge (centre within its radius of the wall) and a via beside a slanted side are not covered
    cut = small_board([(0.1, 5.0, 0.4)])
    assert any("touching the board edge" in w for w in check_via_limits(cut, ("fvm",), 1.0))
    tri = small_board([(5.0, 0.4, 0.3)])
    tri.set_outline([(0, 0), (10, 0), (10, 10), (4, 10), (0, 6)])
    assert any("touching the board edge" in w for w in check_via_limits(tri, ("fvm",), 1.0))


def test_warning_for_a_coarse_cell_next_to_vias():
    """!
    @brief From a 2 mm cell the FVM and FDM warn about the vias; a finer cell, other models and boards without vias do not.
    @return None.
    """
    p = small_board([(5.0, 5.0, 0.3)])
    assert any("coarse for the vias" in w for w in check_via_limits(p, ("fvm", "fdm"), 2.0))
    assert not any("coarse for the vias" in w for w in check_via_limits(p, ("fvm",), 1.0))
    assert not any("coarse for the vias" in w for w in check_via_limits(p, ("lumped", "analytic"), 2.0))
    p.vias = []
    assert check_via_limits(p, ("fvm",), 2.0) == []
