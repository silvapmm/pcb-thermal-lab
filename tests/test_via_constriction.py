#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_via_constriction.py
@brief The constriction resistance of the vias in the Lumped (micro well, capped cluster well) and Analytic (tile rule, bilinear spread, self-term) models.
@details Independent references: the radial integral of a sink in a circular cell (no code of the program), the FVM with the mean-potential via at a fine cell, and the
         fixed points of the tile rule. Before the correction the two models joined the planes through the barrel conductance only: the copper-fill gain of the example board
         was 6.3 to 6.8 K against 4.2 K of the FVM, a 3 x 3 array at 3.5 mm pitch was 57 % (Lumped) and 36 % (Analytic) too large. Boards without vias must not change at all.
"""

import copy
import math

import numpy as np
import pytest
from scipy.integrate import quad

from pcbthermal import Problem, SolverOptions, simulate, viaconstriction
from pcbthermal.checks import check_model_limits
from pcbthermal.examples import example_board
from pcbthermal.model import Materials


def board(layers=4, side=21.0, source=10.0, power=2.0, centre=None, h_top=10.0):
    """!
    @brief Square board with full copper on every layer and a square source on the top copper (no vias).
    @param layers Copper layers.
    @param side Board side in mm.
    @param source Side of the source in mm.
    @param power Source power in W.
    @param centre Centre of the source in mm (None: the board centre).
    @param h_top Top film coefficient in W/m2K.
    @return Problem.
    """
    c = side / 2 if centre is None else centre
    p = Problem.new(side, side, layers, 1.6, 35.0, h_top=h_top, h_bottom=200.0, h_side=None, materials=Materials(k_fr4_inplane=0.3))
    for layer in range(1, layers + 1):
        p.add_zone(layer, rect=(0, 0, side, side))
    p.add_heater(1, power, rect=(c - source / 2, c - source / 2, c + source / 2, c + source / 2))
    return p


def array(n, pitch, fill_k=385.0, **kw):
    """!
    @brief An n x n via array centred under the source of `board`.
    @param n Vias per side.
    @param pitch Pitch in mm.
    @param fill_k Fill conductivity in W/mK.
    @param kw Arguments of `board`.
    @return Problem.
    """
    p = board(**kw)
    c = p.board.width * 500.0
    h = (n - 1) / 2
    for i in range(n):
        for j in range(n):
            p.add_via(c + (i - h) * pitch, c + (j - h) * pitch, 0.3, fill_k=fill_k)
    return p


def effect(p, model, cell):
    """!
    @brief Via effect of a model: maximum temperature without the vias minus with them.
    @param p Problem with vias.
    @param model Model key.
    @param cell Cell size in mm.
    @return float Effect in K.
    """
    q = copy.deepcopy(p)
    q.vias = []
    opts = SolverOptions(models=(model,), cell_mm=cell)
    return simulate(q, opts).results[model].t_max - simulate(p, opts).results[model].t_max


# ------------------------------------------------------------------------------------------------ the closed form

@pytest.mark.parametrize("ratio", [3.0, 10.0, 80.0])
def test_krogh_against_the_radial_integral(ratio):
    """!
    @brief Mean-to-wall resistance of the cell of a via against the integral of the radial flow (nothing of the closed form used).
    @details Uniform source q per area, insulated rim: the flow towards the sink at radius r is q pi (R^2 - r^2), dT/dr = -q (R^2 - r^2) / (2 S r); the mean is taken over the annulus.
    @param ratio R / a.
    @return None.
    """
    s, a = 0.05, 0.15e-3
    r_cell = ratio * a
    flow = lambda r: math.pi * (r_cell ** 2 - r ** 2)                                  # W per unit q
    t = lambda r: quad(lambda x: flow(x) / (2.0 * math.pi * s * x), a, r)[0]           # rise above the wall per unit q
    mean = quad(lambda r: 2.0 * math.pi * r * t(r), a, r_cell)[0] / (math.pi * (r_cell ** 2 - a ** 2))
    assert viaconstriction.krogh(s, r_cell, a) == pytest.approx(mean / flow(a), rel=2e-4)
    assert viaconstriction.krogh(s, a, a) == 0.0


# ------------------------------------------------------------------------------------------------ against the FVM

def test_unit_cell_against_the_fvm():
    """!
    @brief Periodic cell of a lattice of vias (only the constriction is present): Lumped within 6 % and Analytic within 4 % of the FVM at a fine cell.
    @details Before: +11 % (Lumped) and +2 % (Analytic) on the cell of 3.5 mm; the 8 mm cell was +35 % (Analytic).
    @return None.
    """
    for pitch in (3.5, 8.0):
        p = board(layers=2, side=pitch, source=pitch, power=1.0, h_top=0.0)
        p.add_via(pitch / 2, pitch / 2, 0.3, fill_k=385.0)
        ref = effect(p, "fvm", pitch / 70.0)
        for model in ("lumped", "analytic"):
            assert effect(p, model, pitch / 7.0) == pytest.approx(ref, rel=0.06 if model == "lumped" else 0.04), (model, pitch)


def test_copper_fill_gain_of_the_example_board():
    """!
    @brief The gain of filling the nine vias of the example board with copper: 4.2 K in the FVM, 6.3 (Analytic) and 6.8 K (Lumped) before the correction.
    @return None.
    """
    gains = {}
    for model in ("fvm", "lumped", "analytic"):
        open_, cu = example_board(), example_board()
        for v in cu.vias:
            v.fill_k = 385.0
        for v in open_.vias:
            v.fill_k = 0.0
        opts = SolverOptions(models=(model,), cell_mm=0.5)
        gains[model] = simulate(open_, opts).results[model].t_max - simulate(cu, opts).results[model].t_max
    assert gains["lumped"] == pytest.approx(gains["fvm"], abs=0.7)
    assert gains["analytic"] == pytest.approx(gains["fvm"], abs=0.7)
    assert 3.5 < gains["lumped"] < 5.2 and 3.5 < gains["analytic"] < 5.2


def test_sparse_array_and_rows_against_the_fvm():
    """!
    @brief 2 x 2 array at 3.5 mm pitch and a row of five: the program was +57 % / +36 % (array) and +84 % / +48 % (row) off in the Lumped / Analytic models.
    @return None.
    """
    p = array(2, 3.5)
    ref = effect(p, "fvm", 0.25)
    assert effect(p, "analytic", 0.5) == pytest.approx(ref, rel=0.05)
    assert effect(p, "lumped", 0.5) == pytest.approx(ref, rel=0.25)          # measured +19 %: the cluster well of a sparse array is generous
    r = board(layers=2, side=16.0, source=3.0, power=0.5)
    for i in range(5):
        r.add_via(8.0 + 1.5 + 1.0 + i * 1.5, 8.0, 0.3, fill_k=385.0)
    ref = effect(r, "fvm", 0.25)
    assert effect(r, "analytic", 0.5) == pytest.approx(ref, rel=0.06)
    assert effect(r, "lumped", 0.5) == pytest.approx(ref, rel=0.25)          # measured +15 %


def test_thermal_pad_and_dense_arrays_against_the_fvm():
    """!
    @brief Pads at 1.2 and 0.5 mm pitch (the tile follows the pitch): the Analytic within 4 %, the Lumped (capped cluster well) within 10 %.
    @return None.
    """
    for pitch, tol in ((1.2, 0.04), (0.5, 0.04)):
        p = array(5, pitch, side=30.0, source=6.0, power=3.0)
        ref = effect(p, "fvm", 0.25)
        assert effect(p, "analytic", 0.5) == pytest.approx(ref, rel=tol), pitch
        assert effect(p, "lumped", 0.5) == pytest.approx(ref, rel=0.10), pitch


# ------------------------------------------------------------------------------------------------ nothing changes without vias

def test_boards_without_vias_are_unchanged():
    """!
    @brief The temperatures of the Lumped and Analytic models on boards without vias are those of the program before the correction (stored from it).
    @return None.
    """
    p = example_board()
    p.vias = []
    stored = {("lumped", 0.5): (94.69317856820783, 50.41009237427764), ("lumped", 1.0): (96.5103448282088, 50.40227481692728),
              ("analytic", 0.5): (94.7149725526851, 50.842489306804865), ("analytic", 1.0): (94.55801736064181, 50.8424906244942)}
    for (model, cell), (t_max, t_mean) in stored.items():
        r = simulate(p, SolverOptions(models=(model,), cell_mm=cell)).results[model]
        assert r.t_max == pytest.approx(t_max, rel=1e-12, abs=0) and r.t_mean == pytest.approx(t_mean, rel=1e-12, abs=0), (model, cell)
    # A board with a heatsink and no vias uses the tiles of the program (2.5 to 5 mm), not the via rule
    q = Problem.new(40, 30, 2)
    q.add_full_copper()
    q.add_heater(1, 2.0, rect=(10, 10, 18, 16))
    q.add_heatsink(1, 200.0, rect=(20, 5, 30, 12))
    for (model, cell), (t_max, t_mean) in {("lumped", 0.5): (95.30638364936246, 68.13580022840694), ("analytic", 0.5): (103.09955553667217, 72.68787455758647),
                                           ("analytic", 1.0): (102.96314995913453, 72.68787455758647)}.items():
        r = simulate(q, SolverOptions(models=(model,), cell_mm=cell)).results[model]
        assert r.t_max == pytest.approx(t_max, rel=1e-12, abs=0) and r.t_mean == pytest.approx(t_mean, rel=1e-12, abs=0), (model, cell)


# ------------------------------------------------------------------------------------------------ the tile rule and the groups

def lattice_set(n, pitch, side=60.0):
    """!
    @brief ViaSet of an n x n lattice.
    @param n Vias per side.
    @param pitch Pitch in mm.
    @param side Board side in mm.
    @return ViaSet.
    """
    return viaconstriction.ViaSet(array(n, pitch, side=side, source=min(side - 4.0, (n - 1) * pitch + 2.0)))


@pytest.mark.parametrize("pitch,tile_mm", [(3.5, 1.0), (1.5, 1.0), (1.2, 0.9), (0.6, 0.45), (0.45, 0.3375), (0.2, 0.25)])
def test_tile_rule_fixed_points(pitch, tile_mm):
    """!
    @brief Tile = min(1 mm, 0.75 d_nn), floor 0.25 mm, for a lattice of 4 x 4 vias.
    @param pitch Pitch in mm.
    @param tile_mm Expected tile in mm.
    @return None.
    """
    vs = lattice_set(4, pitch, side=20.0)
    rule, final = viaconstriction.tile_size(vs, 0.02, 0.02)
    assert rule == pytest.approx(tile_mm * 1e-3, rel=1e-9) and final == rule
    grid = viaconstriction.tile_grid(vs, 0.02, 0.02, (4, 4, 0.005, 0.005))
    assert grid[2] <= tile_mm * 1e-3 * (1 + 1e-9) and grid[2] * grid[0] == pytest.approx(0.02)


def test_tile_never_above_the_program_tile_and_coarsened_for_many_vias():
    """!
    @brief The grid is the program's when the rule gives a tile at or above it; 576 vias at 1 mm pitch lift the tile above the rule (1200 active tiles at most).
    @return None.
    """
    vs = lattice_set(3, 3.5, side=30.0)
    prog = (6, 6, 0.005, 0.005)
    assert viaconstriction.tile_grid(vs, 0.03, 0.03, (3, 3, 0.0007, 0.0007)) == (3, 3, 0.0007, 0.0007)
    assert viaconstriction.tile_grid(vs, 0.03, 0.03, prog)[2] == pytest.approx(0.001, rel=0.02)
    big = lattice_set(24, 1.0, side=40.0)
    rule, final = viaconstriction.tile_size(big, 0.04, 0.04)
    assert rule == pytest.approx(0.75e-3) and final > 1.0 * rule
    # The estimate of the active tiles is min(4 n, tiles of the rule); the tile grows by the square root of its ratio to 1200
    assert final == pytest.approx(rule * math.sqrt(min(4 * len(big), (0.04 / rule) ** 2) / viaconstriction.MAX_ACTIVE_TILES))
    nt = viaconstriction.tile_grid(big, 0.04, 0.04, prog)
    assert nt[2] == pytest.approx(0.04 / nt[0]) and nt[2] >= final * 0.97


def test_tile_and_groups_do_not_depend_on_the_order_of_the_vias():
    """!
    @brief Shuffling the vias changes neither the tile nor the groups (as a partition).
    @return None.
    """
    p = array(3, 1.5, side=40.0, source=8.0, centre=10.0)
    for i in range(3):                                                    # a second lattice far from the first
        for j in range(3):
            p.add_via(30.0 + i * 1.5, 30.0 + j * 1.5, 0.3)
    q = copy.deepcopy(p)
    rng = np.random.default_rng(3)
    q.vias = [q.vias[i] for i in rng.permutation(len(q.vias))]
    a, b = viaconstriction.ViaSet(p), viaconstriction.ViaSet(q)
    assert viaconstriction.tile_size(a, 0.04, 0.04) == viaconstriction.tile_size(b, 0.04, 0.04)

    def partition(vs):
        out = {}
        for i, g in enumerate(vs.group):
            out.setdefault(g, []).append((round(vs.x[i], 9), round(vs.y[i], 9)))
        return sorted(sorted(v) for v in out.values())
    assert partition(a) == partition(b) and len(partition(a)) == 2        # the two lattices


def test_groups_by_single_linkage():
    """!
    @brief A row is one group, two rows far apart are two, a lone via has an infinite nearest-neighbour distance.
    @return None.
    """
    pts = np.array([[0.0, 0.0], [1.0, 0.0], [2.0, 0.0], [3.0, 0.0], [20.0, 0.0], [21.0, 0.0]]) * 1e-3
    d = viaconstriction.nearest_neighbour(pts)
    g = viaconstriction.via_groups(pts, d)
    assert len(set(g[:4])) == 1 and len(set(g[4:])) == 1 and g[0] != g[4]
    one = np.array([[1.0, 2.0]])
    assert np.isinf(viaconstriction.nearest_neighbour(one)[0]) and list(viaconstriction.via_groups(one, viaconstriction.nearest_neighbour(one))) == [0]


def test_spread_weights():
    """!
    @brief A lone via is shared bilinearly (weights add to 1, first moment kept); one with a close neighbour or just outside a footprint stays on its tile.
    @return None.
    """
    tw = th = 1e-3
    w = viaconstriction.spread_weights(5.3e-3, 7.8e-3, tw, th, 20, 20, math.inf, 0.0)
    assert sum(w.values()) == pytest.approx(1.0) and len(w) == 4
    x = sum(wt * (c + 0.5) * tw for (r, c), wt in w.items())
    y = sum(wt * (r + 0.5) * th for (r, c), wt in w.items())
    assert (x, y) == pytest.approx((5.3e-3, 7.8e-3), abs=1e-12)
    assert viaconstriction.spread_weights(5.3e-3, 7.8e-3, tw, th, 20, 20, 0.5e-3, 0.0) == {(7, 5): 1.0}
    assert viaconstriction.spread_weights(5.3e-3, 7.8e-3, tw, th, 20, 20, math.inf, 0.3e-3) == {(7, 5): 1.0}


# ------------------------------------------------------------------------------------------------ Lumped network

def test_lumped_couplings_are_symmetric_positive_and_reach_non_adjacent_sheets():
    """!
    @brief The reduced star of the barrels couples every pair of sheets of the rings that hold vias, with positive conductances, and conserves heat in the solved network.
    @return None.
    """
    p = array(3, 3.5)
    res = simulate(p, SolverOptions(models=("lumped",), cell_mm=0.5)).results["lumped"]
    out = res.power_out
    assert sum(out.values()) == pytest.approx(res.power_in, rel=1e-6)           # heat balance of the network
    from pcbthermal import lumped
    from pcbthermal.fvm import Network
    net = Network(p, 42, 42, assemble=False, with_blocks=True)
    cov = lumped._footprint_coverage(net, p.heaters[0])
    rn = lumped._heater_network(net, cov, 0, 2.0, 10, viaconstriction.ViaSet(p))
    assert rn["residual"] < 1e-10
    k = rn["K"]
    assert np.allclose(k, k.T) and np.all(np.linalg.eigvalsh(k) > 0)
    R = rn["R"]
    assert k[0 * R, 3 * R] < 0                                                  # sheet 1 is coupled to sheet 4 by the barrels
    plain = lumped._heater_network(net, cov, 0, 2.0, 10, None)
    assert plain["theta"][0, 0] < rn["theta"][0, 0]                              # without the constriction the vias cool the footprint too much


def test_lumped_transient_with_vias_matches_the_steady_state():
    """!
    @brief The time models build the same network: the final value of the unit step response is the steady rise of the heater.
    @return None.
    """
    from pcbthermal import lumped
    p = array(3, 3.5)
    times, z, rth = lumped.step_responses(p, rings=10, cell_mm=0.5)
    assert np.isfinite(z).all() and z[0, -1] == pytest.approx(rth[0], rel=0.02)
    steady = simulate(p, SolverOptions(models=("lumped",), cell_mm=0.5)).results["lumped"]
    assert steady.t_max - p.board.ambient == pytest.approx(rth[0] * p.heaters[0].power, rel=0.03)


# ------------------------------------------------------------------------------------------------ many vias, warnings

def test_four_hundred_vias_run_and_the_tile_is_coarsened():
    """!
    @brief 400 vias on a 40 mm board (stress): both models finish, the Analytic tile is coarsened and warned about, and the answers stay within 10 % (Analytic) and 15 % (Lumped) of the FVM.
    @return None.
    """
    p = array(20, 1.0, side=40.0, source=24.0, power=4.0)
    ref = effect(p, "fvm", 0.5)
    assert effect(p, "analytic", 1.0) == pytest.approx(ref, rel=0.10)
    assert effect(p, "lumped", 1.0) == pytest.approx(ref, rel=0.15)           # measured +10 %
    text = " ".join(str(w) for w in check_model_limits(p, ("analytic",), 1.0))
    assert "coarsened" in text


def test_via_warnings_carry_the_measured_numbers():
    """!
    @brief The Lumped warnings quote the range measured on 46 boards (the branch and its review) and the lone-via range; the Analytic ones appear for one via, a pitch
           under 0.45 mm and a huge system only.
    @return None.
    """
    p = array(3, 3.5)
    w = [str(x) for x in check_model_limits(p, ("lumped",), 1.0)]
    assert len(w) == 1 and "46 boards" in w[0] and "21 % too small" in w[0] and "33 % too large" in w[0] and "36 more" in w[0] and "14 % of its rise" in w[0] and "80 %" not in w[0]
    assert check_model_limits(p, ("analytic",), 1.0) == []                       # nine vias at 3.5 mm: inside what was tested
    lone = board()
    lone.add_via(3.0, 3.0, 0.3)
    wl = [str(x) for x in check_model_limits(lone, ("lumped", "analytic"), 1.0)]
    assert any("22 % too small to 65 % too large" in x for x in wl) and any("one or two vias" in x for x in wl)
    dense = array(4, 0.4, fill_k=385.0)
    assert any("below the 0.45 mm tested" in str(x) for x in check_model_limits(dense, ("analytic",), 1.0))
    assert check_model_limits(dense, ("fvm", "fdm"), 1.0) == []


def test_plan_keeps_the_dense_system_small_for_scattered_vias():
    """!
    @brief Scattered lone vias are spread over four tiles each: the guard enlarges the tile until the active tiles times the layers are within MAX_UNKNOWNS.
    @details The tile rule alone gave 8000 unknowns, 5 s and 1.9 GB for 500 vias on 100 x 80 mm (20 times the memory of the program before the correction).
    @return None.
    """
    rng = np.random.default_rng(5)
    p = board(layers=4, side=80.0, source=10.0)
    for x, y in rng.uniform(2.0, 78.0, size=(800, 2)):
        p.add_via(float(x), float(y), 0.3)
    vs = viaconstriction.ViaSet(p)
    pl = viaconstriction.plan(p, vs, (16, 16, 0.005, 0.005), 4)
    assert pl["active"] * 4 <= viaconstriction.MAX_UNKNOWNS
    assert pl["t_final"] > pl["t_rule"]
    assert all(sum(w.values()) == pytest.approx(1.0) for w in pl["weights"])
    res = simulate(p, SolverOptions(models=("analytic",), cell_mm=1.0)).results["analytic"]
    assert np.isfinite(res.T).all() and res.t_max > p.board.ambient
    text = " ".join(str(w) for w in check_model_limits(p, ("analytic",), 1.0))
    assert "coarsened" in text or "dense system" in text


def test_the_guard_counts_the_tiles_of_heatsinks_and_blocks():
    """!
    @brief Heatsinks and metal blocks share the dense system with the vias: at the 1 mm via tile the 60 x 50 mm block of the example was 12000 unknowns (25 s, 5 GB).
    @details Found by the review: `plan` counted only the via tiles. The tile is now enlarged until via, heatsink and block tiles together fit MAX_UNKNOWNS, and the
             via effect stays within 2 % of the FVM at 0.25 mm on that board (16.59 K; 16.67 K at the 1.63 mm tile).
    @return None.
    """
    from pcbthermal.examples import example_block_board
    p = example_block_board()
    for v in p.vias:
        v.fill_k = 385.0
    vs = viaconstriction.ViaSet(p)
    pl = viaconstriction.plan(p, vs, (40, 32, 0.0025, 0.0025), 4)
    assert pl["active"] * 4 <= viaconstriction.MAX_UNKNOWNS and pl["t_final"] > pl["t_rule"]
    assert pl["active"] >= len(viaconstriction.heatsink_tiles(p, pl["grid"]))
    q = copy.deepcopy(p)
    q.vias = []
    opts = SolverOptions(models=("analytic",), cell_mm=1.0)
    e = simulate(q, opts).results["analytic"].t_max - simulate(p, opts).results["analytic"].t_max
    assert e == pytest.approx(16.59, rel=0.03)
    assert any("coarsened" in str(w) for w in check_model_limits(p, ("analytic",), 1.0))
