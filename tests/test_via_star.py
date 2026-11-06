#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_via_star.py
@brief The star coupling of the via (viawell.py, docs/theory.md 2.6): calibration, matrix structure, the cases of research/via-partial-copper and the solvers.

@details The barrel of a layer is a node reached from the cells of the footprint through g_a = c S w_a, the barrel nodes are eliminated. Held here:
         * the calibration of c against an independent dense solve of the bordered system (a lone via in a uniform sheet keeps the resistance of the Peaceman well), also with the
           edge matrix;
         * the dense block of a via is symmetric, positive semidefinite, has zero row sums and no positive off-diagonal entry, also where the copper covers only part of the footprint;
         * the documented board (docs/theory.md 2.2) has a via effect that no longer depends on the cell, the copper edge and the track against the tabulated 3D values of
           research/via-partial-copper, the dense array against the 3D solid at 0.1 mm, the periodic unit cell converges with the cell;
         * the symmetric LU is used without a fallback and direct, CG and SOR agree.
"""

import logging
import math
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "research", "via-partial-copper", "lib"))

import cases                                                                  # noqa: E402
from pcbthermal import Problem, fdm, fvm, viawell                            # noqa: E402
from pcbthermal.model import Materials, reload_libraries                     # noqa: E402
from test_maximum_principle import copper_edge_board, network               # noqa: E402


@pytest.fixture(autouse=True)
def _libraries():
    """!
    @brief Load the shipped libraries and silence the warnings of the runs.
    @return None.
    """
    reload_libraries()
    logging.disable(logging.WARNING)
    yield
    logging.disable(logging.NOTSET)


def effect(make, kind, cell):
    """!
    @brief Via effect, the maximum rise over the copper without the via minus with it.
    @param make Function (with_via) -> Problem.
    @param kind "fvm" or "fdm".
    @param cell Cell in mm.
    @return float K.
    """
    out = []
    for v in (False, True):
        p = make(v)
        theta, _ = network(p, kind, cell).solve_steady()
        out.append(float(theta[:p.board.layers].max()))
    return out[0] - out[1]


def bordered_delta(cells, w, c, kmat):
    """!
    @brief Potential of the star node over the far-field logarithm for a unit flux, from a dense solve of the bordered system (independent of the eigen form).
    @param cells Array (n, 2) of cell indices.
    @param w Weights (sum 1).
    @param c Star conductance over the sheet conductance (dimensionless).
    @param kmat Edge matrix or None.
    @return float delta (S = 1).
    """
    n = len(w)
    d = cells[:, None, :] - cells[None, :, :]
    C = (viawell.lattice_kernel(d[..., 0], d[..., 1]) - viawell.KAPPA) / 4.0
    if kmat is not None:
        C = C + kmat / (2.0 * math.pi)
    A = np.zeros((n + 1, n + 1))
    A[:n, :n] = np.diag(1.0 / (c * w)) - C
    A[:n, n] = -1.0
    A[n, :n] = 1.0
    rhs = np.zeros(n + 1)
    rhs[n] = 1.0
    return float(np.linalg.solve(A, rhs)[n])


@pytest.mark.parametrize("cell_mm", [0.05, 0.1, 0.25, 0.5])
@pytest.mark.parametrize("walls", [False, True])
def test_the_calibration_keeps_the_resistance_of_a_lone_via(cell_mm, walls):
    """!
    @brief For footprints at several positions the star conductance solves the bordered system: delta equals ln(h / r_t) / (2 pi) to 1e-9 (S = 1), with and without an edge matrix.
    @param cell_mm Cell in mm.
    @param walls True: add the edge matrix of a wall 0.2 mm from the via.
    @return None.
    """
    dx = cell_mm * 1e-3
    r_via = 0.15e-3
    cover = np.ones((60, 60))
    rng = np.random.default_rng(int(cell_mm * 1000))
    for _ in range(6):
        x, y = (30.0 + rng.uniform(-0.5, 0.5, 2)) * dx
        w, _r_eff, r_t = viawell.footprint(x, y, r_via, dx, 0.0, cover, dx, 0.0)
        keys = list(w)
        cells = np.array(keys, dtype=int)
        wv = np.array([w[k] for k in keys])
        kmat = viawell.edge_kernel(keys, dx, dx, (x, y), r_via, [("x", x + 0.2e-3)]) if walls else None
        c = viawell.star_scale(cells, wv, kmat, dx / r_t)
        target = math.log(dx / r_t) / (2.0 * math.pi)
        if c < viawell.STAR_CAP:
            assert bordered_delta(cells, wv, c, kmat) == pytest.approx(target, abs=1e-9)
        else:
            # An equipotential footprint is already as resistive as the well asks for: nothing finite to calibrate
            assert bordered_delta(cells, wv, c, kmat) >= target - 1e-6


def test_the_edge_matrix_contracts_to_the_edge_term():
    """!
    @brief sum_ab w_a w_b K_ab of `edge_kernel` is the number `edge_term` of the mean-potential well, at a wall and at a corner.
    @return None.
    """
    dx = 0.25e-3
    cover = np.ones((60, 60))
    for walls in ([("x", 5.1e-3)], [("x", 5.1e-3), ("y", 5.2e-3)]):
        x, y = 4.95e-3, 5.05e-3
        w, _, _ = viawell.footprint(x, y, 0.15e-3, dx, 0.0, cover, dx, 0.0)
        keys = list(w)
        wv = np.array([w[k] for k in keys])
        K = viawell.edge_kernel(keys, dx, dx, (x, y), 0.15e-3, walls)
        assert float(wv @ K @ wv) == pytest.approx(viawell.edge_term(w, dx, dx, (x, y), 0.15e-3, walls), abs=1e-12)


@pytest.mark.parametrize("cell", [0.5, 0.25])
def test_the_via_block_is_a_laplacian_where_the_copper_ends_inside_the_footprint(cell):
    """!
    @brief The dense block of the via of the documented board (FVM) is symmetric, positive semidefinite, has zero row sums and no positive off-diagonal entry,
           and the cells of the top layer are not coupled alike (the copper cells carry the heat, the bare ones almost none).
    @param cell Cell in mm.
    @return None.
    """
    net = network(copper_edge_board(), "fvm", cell)
    assert len(net.via_blocks) == 1
    bl = net.via_blocks[0]
    M = bl.M
    scale = float(np.abs(M).max())
    assert np.abs(M - M.T).max() == 0.0
    assert np.abs(M.sum(axis=1)).max() <= 1e-9 * scale
    off = M - np.diag(np.diag(M))
    assert off.max() <= 1e-12 * scale                                         # no positive off-diagonal entry
    assert np.linalg.eigvalsh(M).min() >= -1e-9 * scale
    assert np.isfinite(bl.G).all() and (bl.G >= 0).all()
    n0 = len(bl.layer_cells[0])
    top, bottom = np.diag(M)[:n0], np.diag(M)[n0:]
    assert top.max() > 10.0 * top.min()                                       # the top copper ends inside the footprint
    assert bottom.max() < 1.01 * bottom.min()                                 # the bottom plane is whole


def test_a_via_on_whole_copper_has_the_same_footprint_in_every_layer():
    """!
    @brief Away from any copper change every layer of the via takes the geometric footprint of the earlier treatment.
    @return None.
    """
    p = Problem.new(20, 20, 4)
    for layer in range(1, 5):
        p.add_zone(layer, rect=(0, 0, 20, 20))
    p.add_via(10.07, 9.93, 0.3)
    net = fvm.Network(p, 80, 80)
    bl = net.via_blocks[0]
    w, _, _ = viawell.footprint(10.07e-3, 9.93e-3, 0.15e-3, 0.25e-3, 0.0, net.cover, 0.25e-3, 0.0)
    for cells in bl.layer_cells:
        assert sorted(map(tuple, cells.tolist())) == sorted(w)


@pytest.mark.parametrize("cell", [0.5, 0.25, 0.125])
def test_the_documented_board_via_effect_no_longer_depends_on_the_cell(cell):
    """!
    @brief The via effect of the board of docs/theory.md 2.2 lies in 12.0 to 13.5 K at 0.5 to 0.125 mm (the program read 7.3 to 8.3 K with a cold spot of 8 to 14 K).
    @param cell Cell in mm.
    @return None.
    """
    def make(v):
        p = copper_edge_board()
        if not v:
            p.vias = []
        return p
    assert 12.0 <= effect(make, "fvm", cell) <= 13.5


def test_the_documented_board_spread_is_below_one_kelvin():
    """!
    @brief From 0.5 to 0.125 mm the via effect of the documented board varies by less than 1 K (the 3D solid has not converged there, so this is a cell-independence test).
    @return None.
    """
    def make(v):
        p = copper_edge_board()
        if not v:
            p.vias = []
        return p
    values = [effect(make, "fvm", c) for c in (0.5, 0.25, 0.125)]
    assert max(values) - min(values) < 1.0


@pytest.mark.parametrize("cell", [0.5, 0.25])
def test_the_copper_edge_through_the_via_against_the_3d_solid(cell):
    """!
    @brief 10 mm board, copper ending through the via: within 15 % of the 3D solid at 1/20 mm for the smeared barrel (7.39 K) and the barrel with its wall (8.71 K).
    @details The program read -41 and -37 % of 7.39 K at 0.5 and 0.25 mm.
    @param cell Cell in mm.
    @return None.
    """
    e = effect(lambda v: cases.edge(delta=0.0, with_via=v), "fvm", cell)
    assert abs(e / 7.39 - 1.0) <= 0.15 and abs(e / 8.71 - 1.0) <= 0.15, e


@pytest.mark.parametrize("cell", [0.5, 0.25])
def test_the_track_ending_at_the_via_against_the_3d_solid(cell):
    """!
    @brief 10 mm board, a 1.0 mm track ending at the via: within 25 % of the 3D solid at 1/20 mm (25.80 K); the program read -52 and -49 %.
    @param cell Cell in mm.
    @return None.
    """
    e = effect(lambda v: cases.track(width=1.0, with_via=v), "fvm", cell)
    assert abs(e / 25.80 - 1.0) <= 0.25, e


@pytest.mark.parametrize("cell", [0.5, 0.25])
def test_the_dense_array_against_the_3d_solid(cell):
    """!
    @brief 16 mm four-layer board, 3 W on an 8 mm part, 10 x 10 copper-filled vias at 0.8 mm pitch: the via effect is within 2 % of the 3D solid (50.31 K at 0.2 mm, 50.39 K at 0.1 mm).
    @details The mean-potential via read 50.27 and 50.22 K (-0.2 and -0.3 %); both are inside the 3D pair's own spread of 0.2 %.
    @param cell Cell in mm.
    @return None.
    """
    def make(v):
        p = Problem.new(16, 16, 4, h_top=10.0, h_bottom=100.0)
        for layer in (1, 2, 3, 4):
            p.add_zone(layer, rect=(0.5, 0.5, 15.5, 15.5))
        p.add_heater(1, 3.0, rect=(4, 4, 12, 12), name="Q1")
        if v:
            for i in range(10):
                for j in range(10):
                    p.add_via(8.0 + (i - 4.5) * 0.8, 8.0 + (j - 4.5) * 0.8, 0.3, fill_k=385.0)
        return p
    assert abs(effect(make, "fvm", cell) / 50.39 - 1.0) < 0.02


def test_a_lone_via_in_a_periodic_cell_converges_with_the_cell():
    """!
    @brief The unit cell of a via lattice (3.5 mm pitch, 1 W, no convection): the effect changes by less than 0.1 % between the cells pitch/20 and pitch/70.
    @details This holds the calibration of c on real grids: a drift of the lone-via resistance with the footprint would show here (the first version of the root finder gave +5 % at pitch/70).
    @return None.
    """
    pitch = 3.5
    values = []
    for div in (20.0, 35.0, 70.0):
        def make(v):
            p = Problem.new(pitch, pitch, 2, 1.6, 35.0, h_top=0.0, h_bottom=10.0, h_side=None, materials=Materials(k_fr4_inplane=0.3))
            for layer in (1, 2):
                p.add_zone(layer, rect=(0, 0, pitch, pitch))
            p.add_heater(1, 1.0, rect=(0, 0, pitch, pitch))
            if v:
                p.add_via(pitch / 2, pitch / 2, 0.3, fill_k=385.0)
            return p
        values.append(effect(make, "fvm", pitch / div))
    assert max(values) - min(values) < 1e-3 * values[0]


def test_symmetric_lu_is_kept_and_the_solvers_agree_on_partial_copper(caplog):
    """!
    @brief The matrix with star couplings passes the guards of `fvm.lu_factor` (no fallback warning) and direct, CG and SOR agree to 1e-8 K.
    @param caplog pytest log capture.
    @return None.
    """
    logging.disable(logging.NOTSET)
    p = copper_edge_board()
    net = fvm.Network(p, 60, 60)
    with caplog.at_level(logging.WARNING, logger="pcbthermal.fvm"):
        ref, res = net.solve_steady("direct")
    assert not [r for r in caplog.records if "Symmetric LU" in r.getMessage()]
    assert res < 1e-9
    cg, _ = fvm.Network(p, 60, 60).solve_steady("cg")
    sor, _res, info = fvm.Network(p, 60, 60).solve_sor(omega=None, tol=1e-12)
    assert info["converged"] and "fallback" not in info
    assert np.abs(cg - ref).max() < 1e-8 and np.abs(sor - ref).max() < 1e-8


def test_the_fdm_has_no_positive_entries_and_keeps_the_balance():
    """!
    @brief The FDM matrix of the documented board has no positive off-diagonal entry and conserves the heat.
    @return None.
    """
    net = fdm.Network(copper_edge_board(), cell_mm=0.5)
    coo = net.K.tocoo()
    assert not ((coo.row != coo.col) & (coo.data > 1e-12 * np.abs(net.K.diagonal()).max())).any()
    theta, _ = net.solve_steady()
    assert float((net.g_amb * theta).sum()) == pytest.approx(float(net.Q.sum()), rel=1e-9)


def test_the_star_scale_is_cached_by_footprint_shape():
    """!
    @brief Two vias at the same place in the cell share one calibration; the cache holds one entry for them.
    @return None.
    """
    viawell._STAR_CACHE.clear()
    dx = 0.25e-3
    cover = np.ones((40, 40))
    for shift in (0, 7):
        w, _, r_t = viawell.footprint((10.3 + shift) * dx, (10.6 + shift) * dx, 0.15e-3, dx, 0.0, cover, dx, 0.0)
        keys = list(w)
        viawell.star_scale(np.array(keys, dtype=int), np.array([w[k] for k in keys]), None, dx / r_t)
    assert len(viawell._STAR_CACHE) == 1
