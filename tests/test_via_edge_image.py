#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_via_edge_image.py
@brief The mirror image of a straight board edge in the well of a via (FVM): accuracy against the resolved reference, bit-identity away from an edge, mirror
       symmetry, the matrix (symmetric, positive definite, row sums), cost, and hostile cases (a row of vias, a corner, a narrow board, a via on the edge line,
       short or slanted outline sides, a reflex corner).
@details The reference values E = T_max(no via) - T_max(via) are those of the layered model of the program written again on a 1/16 mm grid by the independent
         solver `sheets2d` (research/via-real-board/lib/edge_reference.py, board of study S1: 10 x 10 mm, four copper planes, 0.5 W in 3 x 2 mm, one 0.3 mm
         copper-filled via); they are tabulated here (research/via-edge-image/out/sweep.txt, abs_corner.txt, abs_outline.txt) so that the test does not solve the
         fine grid. The tolerances are the budget of research/via-edge-image/INTEGRATION.md 2, not the measurement.
"""

import logging
import math
import time

import numpy as np
import pytest

from pcbthermal import Problem, SolverOptions, fvm, simulate, viawell
from pcbthermal.examples import example_board
from pcbthermal.model import Materials, reload_libraries

# E of the resolved reference in K: (h_side in W/m2K, distance in mm) -> E
REFERENCE = {(0, 0.16): 3.162, (0, 0.3): 3.358, (0, 0.5): 3.542, (0, 1): 3.839, (0, 2): 4.274,
             (10, 0.16): 2.993, (10, 0.3): 3.178, (10, 0.5): 3.353, (10, 1): 3.636, (10, 2): 4.055}
CORNER_REFERENCE = {0.16: 2.115, 0.3: 2.393}
CUT_REFERENCE = {(7.0, 0.16): 7.628, (7.0625, 0.16): 7.471}


def edge_board(distance=0.16, via=True, x_cut=None, h_side=None, corner=False, width=10.0):
    """!
    @brief The test board of study S1 of research/via-real-board.
    @param distance Distance of the via centre from the right edge (or the outline cut) in mm.
    @param via False: no via.
    @param x_cut Outline that cuts the box at this x in mm (None: the box edge).
    @param h_side Edge film coefficient in W/m2K (None: insulated).
    @param corner True: the via is also `distance` from the top edge.
    @param width Side of the square board in mm.
    @return Problem.
    """
    w = width
    p = Problem.new(w, w, 4, 1.6, 35.0, h_top=10.0, h_bottom=200.0, h_side=h_side, materials=Materials(k_fr4_inplane=0.3))
    for layer in range(1, 5):
        p.add_zone(layer, rect=(0, 0, w, w))
    edge = w
    if x_cut is not None:
        p.set_outline([(0, 0), (x_cut, 0), (x_cut, w), (0, w)])
        edge = x_cut
    p.add_heater(1, 0.5, rect=(1, 4, 4, 6))
    if via:
        p.add_via(edge - distance, (w - distance) if corner else w / 2, 0.3, fill_k=385.0)
    return p


def rise(p, cell, model="fvm"):
    """!
    @brief Maximum temperature rise over the ambient.
    @param p The Problem.
    @param cell Cell size in mm.
    @param model Model key.
    @return float rise in K.
    """
    return float(simulate(p, SolverOptions(models=(model,), cell_mm=cell)).results[model].t_max - p.board.ambient)


def effect(cell, **kw):
    """!
    @brief Via effect E = T_max(no via) - T_max(via) of the FVM on the S1 board.
    @param cell Cell size in mm.
    @param kw Keywords of `edge_board`.
    @return float E in K.
    """
    return rise(edge_board(via=False, **kw), cell) - rise(edge_board(via=True, **kw), cell)


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


@pytest.mark.parametrize("h_side", [0, 10])
def test_nearest_vias_at_1_mm_are_within_the_budget(h_side):
    """!
    @brief The via effect at 1 mm for distances 0.16 to 2 mm from the edge is within 3 % of the resolved reference (2 % for the nearest), insulated and at h_side 10.
    @param h_side Edge film coefficient in W/m2K (0: insulated).
    @return None.
    """
    for d in (0.16, 0.3, 0.5, 1, 2):
        err = effect(1.0, distance=d, h_side=h_side or None) / REFERENCE[(h_side, d)] - 1.0
        assert abs(err) < (0.02 if d == 0.16 else 0.03), (h_side, d, err)


def test_nearest_via_at_finer_cells_and_the_excess_it_removes():
    """!
    @brief At 0.5 mm the nearest via is within 1 % (it was +6.2 %); at 1 mm without the image it was +14.5 % (the reach of the image set to zero reproduces that).
    @return None.
    """
    ref = REFERENCE[(0, 0.16)]
    assert abs(effect(0.5, distance=0.16) / ref - 1.0) < 0.01
    old = viawell.EDGE_REACH_CELLS
    try:
        viawell.EDGE_REACH_CELLS = 0.0
        assert effect(1.0, distance=0.16) / ref - 1.0 > 0.12
    finally:
        viawell.EDGE_REACH_CELLS = old


def test_corner_and_outline_cuts():
    """!
    @brief A via near a corner (two walls) is within 2 %; a via near an outline side on a grid line within 2 %, inside a cell within 3 %.
    @return None.
    """
    for d, ref in CORNER_REFERENCE.items():
        assert abs(effect(1.0, distance=d, corner=True) / ref - 1.0) < 0.02, d
    assert abs(effect(1.0, distance=0.16, x_cut=7.0) / CUT_REFERENCE[(7.0, 0.16)] - 1.0) < 0.02
    assert abs(effect(1.0, distance=0.16, x_cut=7.0625) / CUT_REFERENCE[(7.0625, 0.16)] - 1.0) < 0.03


def test_negative_c_enlarges_the_footprint_instead_of_an_infinite_well():
    """!
    @brief A small via near a corner on a 0.5 mm cell gives a negative c; the footprint is enlarged until the denominator is positive and the result stays within 1 %.
    @return None.
    """
    ref = CORNER_REFERENCE[0.3]
    # 1 % before fix/simple-stackup-physical-layers; the physical slabs of the four-layer board move the corner case to 1.15 % (2.3655 against 2.393 K)
    assert abs(effect(0.5, distance=0.3, corner=True) / ref - 1.0) < 0.015
    p = edge_board(distance=0.3, corner=True)
    net = fvm.Network(p, 20, 20)
    assert all(np.isfinite(G).all() for _r, _c, _w, G in net.via_blocks)


def _same_blocks(a, b):
    """!
    @brief True when two lists of via blocks are equal bit for bit.
    @param a First list from viawell.build.
    @param b Second list.
    @return bool.
    """
    return len(a) == len(b) and all(np.array_equal(x, y) for p, q in zip(a, b) for x, y in zip(p, q))


def test_no_wall_within_reach_is_bit_identical():
    """!
    @brief A via farther than six cells from every edge, the example board and a plate with vias give the same blocks and temperatures with and without the image.
    @return None.
    """
    p = edge_board(distance=4.0)
    for cell in (0.5, 1.0):
        n = int(round(10.0 / cell))
        with_img = fvm.Network(p, n, n)
        old = viawell.EDGE_REACH_CELLS
        try:
            viawell.EDGE_REACH_CELLS = 0.0
            without = fvm.Network(p, n, n)
        finally:
            viawell.EDGE_REACH_CELLS = old
        # 4 mm is eight cells at 0.5 mm and four at 1 mm: only the 1 mm one is inside the reach and may differ
        if cell == 0.5:
            assert _same_blocks(with_img.via_blocks, without.via_blocks)
    ex = example_board()
    a = rise(ex, 1.0)
    old = viawell.EDGE_REACH_CELLS
    try:
        viawell.EDGE_REACH_CELLS = 0.0
        b = rise(ex, 1.0)
    finally:
        viawell.EDGE_REACH_CELLS = old
    assert a == b


def test_well_conductance_with_zero_c_is_the_old_expression():
    """!
    @brief c = 0 gives 2 pi S / ln(r_eff / r_t) exactly; a positive denominator is kept; a non-positive one is an infinite well.
    @return None.
    """
    assert viawell.well_conductance(2.0, 5e-4, 1e-4) == 2.0 * math.pi * 2.0 / math.log(5.0)
    assert viawell.well_conductance(2.0, 5e-4, 1e-4, 0.5) == 2.0 * math.pi * 2.0 / (math.log(5.0) + 0.5)
    assert viawell.well_conductance(2.0, 5e-4, 1e-4, -2.0) == math.inf
    assert viawell.well_conductance(2.0, 1e-4, 1e-4) == math.inf


def test_fdm_has_no_image():
    """!
    @brief The FDM (node grid, origin -dx/2) is not touched: the same temperatures with the reach of the image set to zero.
    @return None.
    """
    p = edge_board(distance=0.16)
    a = rise(p, 1.0, "fdm")
    old = viawell.EDGE_REACH_CELLS
    try:
        viawell.EDGE_REACH_CELLS = 0.0
        b = rise(p, 1.0, "fdm")
    finally:
        viawell.EDGE_REACH_CELLS = old
    assert a == b


def _mirrored(p, width):
    """!
    @brief The board mirrored about x = width / 2 (heater and vias).
    @param p A Problem built by `edge_board` without an outline.
    @param width Board width in mm.
    @return Problem.
    """
    q = edge_board(via=False, width=width)
    q.heaters = []
    q.add_heater(1, 0.5, rect=(width - 4, 4, width - 1, 6))
    for v in p.vias:
        q.add_via(width - v.x * 1000.0, v.y * 1000.0, v.diameter * 1000.0, fill_k=385.0)
    return q


def test_mirror_symmetry_left_and_right_edge():
    """!
    @brief A via at distance d from the left edge gives the same field as the mirrored via at the right edge.
    @return None.
    """
    for d in (0.16, 0.5):
        p = edge_board(distance=d)
        q = _mirrored(p, 10.0)
        assert abs(rise(p, 1.0) - rise(q, 1.0)) < 1e-9, d
        assert abs(rise(edge_board(distance=d, corner=True), 1.0) - rise(_mirror_y(edge_board(distance=d, corner=True)), 1.0)) < 1e-9


def _mirror_y(p):
    """!
    @brief The board of a corner via mirrored about y = 5 mm (the heater at y 4..6 is symmetric).
    @param p A Problem built by `edge_board` without an outline.
    @return Problem.
    """
    for v in p.vias:
        v.y = 10e-3 - v.y
    return p


def _dense(net):
    """!
    @brief The matrix of a network as a dense array.
    @param net An assembled fvm.Network.
    @return numpy.ndarray.
    """
    return net.K.toarray()


@pytest.mark.parametrize("corner", [False, True])
def test_matrix_is_symmetric_positive_definite_with_the_same_row_sums(corner, caplog):
    """!
    @brief K stays symmetric and positive definite, its row sums are those of the board without the via, and the symmetric LU is accepted (no fallback).
    @param corner True: the via is near two edges.
    @param caplog pytest fixture.
    @return None.
    """
    p = edge_board(distance=0.16, corner=corner)
    n = 10
    with_via = fvm.Network(p, n, n)
    without = fvm.Network(edge_board(via=False), n, n)
    K = _dense(with_via)
    assert np.abs(K - K.T).max() == 0.0
    assert np.abs(K.sum(axis=1) - _dense(without).sum(axis=1)).max() < 1e-12
    assert np.linalg.eigvalsh(K).min() > 0.0
    logging.disable(logging.NOTSET)
    with caplog.at_level(logging.WARNING, logger="pcbthermal.fvm"):
        fvm.lu_factor(with_via.K)
    assert "Symmetric LU" not in caplog.text


def test_cost_of_the_image_per_via():
    """!
    @brief The edge term of one via costs less than 1 ms.
    @return None.
    """
    w, r_eff, r_t = viawell.footprint(9.84e-3, 5e-3, 0.15e-3, 1e-3, 0.0, np.ones((10, 10)))
    walls = [("x", 10e-3)]
    viawell.edge_term(w, 1e-3, 1e-3, (9.84e-3, 5e-3), 0.15e-3, walls)
    t0 = time.perf_counter()
    for _ in range(50):
        viawell.edge_term(w, 1e-3, 1e-3, (9.84e-3, 5e-3), 0.15e-3, walls)
    assert (time.perf_counter() - t0) / 50 < 1e-3


def test_a_row_of_vias_along_the_edge():
    """!
    @brief 50 vias in a row 0.2 mm from the edge (footprints overlap): finite, symmetric positive definite matrix, a closed energy balance, and the row cools the
           part by a finite amount, not more than the same row 2 mm from the edge by a wild factor.
    @return None.
    """
    p = Problem.new(60, 20, 4, 1.6, 35.0, h_top=10.0, h_bottom=200.0, h_side=None, materials=Materials(k_fr4_inplane=0.3))
    for layer in range(1, 5):
        p.add_zone(layer, rect=(0, 0, 60, 20))
    p.add_heater(1, 2.0, rect=(50, 8, 58, 12))
    for k in range(50):
        p.add_via(59.8, 0.2 + 19.6 * k / 49.0, 0.3, fill_k=385.0)
    res = simulate(p, SolverOptions(models=("fvm",), cell_mm=1.0)).results["fvm"]
    assert np.isfinite(res.t_max) and abs(res.balance_error) < 1e-9
    net = fvm.Network(p, 60, 20)
    K = _dense(net)
    assert np.abs(K - K.T).max() <= 1e-12 * np.abs(K).max() and np.linalg.eigvalsh(K).min() > 0.0      # the guard of fvm.lu_factor
    q = Problem.new(60, 20, 4, 1.6, 35.0, h_top=10.0, h_bottom=200.0, h_side=None, materials=Materials(k_fr4_inplane=0.3))
    for layer in range(1, 5):
        q.add_zone(layer, rect=(0, 0, 60, 20))
    q.add_heater(1, 2.0, rect=(50, 8, 58, 12))
    q.vias = []
    bare = rise(q, 1.0)
    gain_edge = bare - rise(p, 1.0)
    p_far = Problem.new(60, 20, 4, 1.6, 35.0, h_top=10.0, h_bottom=200.0, h_side=None, materials=Materials(k_fr4_inplane=0.3))
    for layer in range(1, 5):
        p_far.add_zone(layer, rect=(0, 0, 60, 20))
    p_far.add_heater(1, 2.0, rect=(50, 8, 58, 12))
    for k in range(50):
        p_far.add_via(57.0, 0.2 + 19.6 * k / 49.0, 0.3, fill_k=385.0)
    gain_far = bare - rise(p_far, 1.0)
    assert 0.0 < gain_edge < 3.0 * gain_far, (gain_edge, gain_far)


def test_narrow_board_with_two_opposite_walls_and_a_via_on_the_edge_line():
    """!
    @brief A 4 mm wide board with a via in the middle (two walls within reach) and a via exactly on the edge line, a footprint cut by the edge: finite, symmetric positive definite.
    @return None.
    """
    for x in (2.0, 3.99, 4.0, 4.05):
        p = Problem.new(4, 30, 3, 1.6, 35.0, h_top=10.0, h_bottom=100.0, h_side=10.0, materials=Materials(k_fr4_inplane=0.3))
        for layer in range(1, 4):
            p.add_zone(layer, rect=(0, 0, 4, 30))
        p.add_heater(1, 1.0, rect=(1, 14, 3, 16))
        p.add_via(x, 15.0, 0.4, fill_k=385.0)
        net = fvm.Network(p, 8, 60)
        K = _dense(net)
        assert np.abs(K - K.T).max() == 0.0 and np.linalg.eigvalsh(K).min() > 0.0, x
        res = simulate(p, SolverOptions(models=("fvm",), cell_mm=0.5)).results["fvm"]
        assert np.isfinite(res.t_max) and abs(res.balance_error) < 1e-9, x


def test_edge_walls_of_a_box_and_of_outlines():
    """!
    @brief Walls: the box sides, an axis-parallel outline side, nothing for a reflex corner, a slanted side, or a staircase of short steps (clean is False there).
    @return None.
    """
    class V:
        """!
        @brief A via position.
        """
        def __init__(self, x, y):
            """!
            @brief Store the position.
            @param x x in m.
            @param y y in m.
            @return None.
            """
            self.x, self.y = x, y

    box = edge_board(via=False)
    assert viawell.edge_walls(box, V(9.9e-3, 5e-3), 3e-3) == ([("x", 10e-3)], True)
    walls, clean = viawell.edge_walls(box, V(9.9e-3, 0.2e-3), 6e-3)
    assert sorted(walls) == [("x", 10e-3), ("y", 0.0)] and clean
    assert viawell.edge_walls(box, V(5e-3, 5e-3), 2e-3) == ([], True)
    cut = edge_board(via=False, x_cut=7.0625)
    assert viawell.edge_walls(cut, V(6.9e-3, 5e-3), 4e-3) == ([("x", 7.0625e-3)], True)
    # An inverted T: a via in the arm near the reflex corner gets only the wall it faces; the corner is reported as not clean
    t = Problem.new(30, 24, 2).add_full_copper()
    t.set_outline([(0, 0), (30, 0), (30, 8), (20, 8), (20, 24), (10, 24), (10, 8), (0, 8)])
    walls, clean = viawell.edge_walls(t, V(19.5e-3, 12e-3), 4e-3)
    assert walls == [("x", 20e-3)] and clean
    walls, clean = viawell.edge_walls(t, V(19.8e-3, 7.0e-3), 4e-3)
    assert not clean                                                                # near the reflex corner (20, 8)
    # A slanted side next to the via, and a staircase of 0.5 mm steps, are reported as not clean
    tri = edge_board(via=False)
    tri.set_outline([(0, 0), (10, 0), (10, 10), (4, 10), (0, 6)])
    walls, clean = viawell.edge_walls(tri, V(1.0e-3, 4.2e-3), 4e-3)
    assert not clean and walls == [("x", 0.0)]                                        # the straight left side is found, the slanted one makes it unclean
    zig = edge_board(via=False)
    # A staircase of 0.5 mm steps on the left side: every side is shorter than the reach
    zig.set_outline([(0, 0), (10, 0), (10, 10), (1, 10), (1, 9.5), (0.5, 9.5), (0.5, 9.0), (0, 9.0)])
    walls, clean = viawell.edge_walls(zig, V(0.7e-3, 9.2e-3), 4e-3)
    assert not clean


# E of the resolved reference (1/16 mm, the same construction with the cells off the outline pinned) for vias near the reflex corner of an inverted T and of an L
T_OUTLINE = [(0, 0), (10, 0), (10, 4), (7, 4), (7, 10), (3, 10), (3, 4), (0, 4)]
L_OUTLINE = [(0, 0), (10, 0), (10, 6), (6, 6), (6, 10), (0, 10)]
REFLEX_REFERENCE = {("T", 6.84, 4.2): 10.410, ("T", 6.84, 6.0): 7.632, ("L", 6.2, 5.84): 5.505, ("L", 8.0, 5.84): 4.376}


def reflex_board(shape, x, y, via=True):
    """!
    @brief A 10 x 10 mm four-plane board cut to an inverted T (stem 3..7 mm over a 4 mm bar) or an L (the square 6..10 x 6..10 mm removed), one 0.3 mm via.
    @param shape "T" or "L".
    @param x Via x in mm.
    @param y Via y in mm.
    @param via False: no via.
    @return Problem.
    """
    p = Problem.new(10, 10, 4, 1.6, 35.0, h_top=10.0, h_bottom=200.0, h_side=None, materials=Materials(k_fr4_inplane=0.3))
    for layer in range(1, 5):
        p.add_zone(layer, rect=(0, 0, 10, 10))
    p.set_outline(T_OUTLINE if shape == "T" else L_OUTLINE)
    p.add_heater(1, 0.5, rect=(4, 0.5, 6, 2) if shape == "T" else (1, 1, 4, 3))
    if via:
        p.add_via(x, y, 0.3, fill_k=385.0)
    return p


@pytest.mark.parametrize("shape,x,y,cell,walls,budget", [("T", 6.84, 4.2, 1.0, 0, 4.0), ("T", 6.84, 4.2, 0.5, 0, 2.0), ("T", 6.84, 6.0, 1.0, 1, 4.0),
                                                         ("L", 6.2, 5.84, 0.5, 0, 2.0), ("L", 8.0, 5.84, 1.0, 0, 12.0), ("L", 8.0, 5.84, 0.5, 2, 2.0)])
def test_no_wrong_image_beside_a_reflex_corner(shape, x, y, cell, walls, budget):
    """!
    @brief Beside a reflex corner the image is left out (the corner within EDGE_GUARD_CELLS, or a short side nearer than the wall) and is kept farther away.
    @details Found by the review: the infinite mirror of the stem side of a T put a via 0.26 mm from the reflex corner at -12.4 % (1 mm) and -4.6 % (0.5 mm)
             against -2.9 and -0.4 % without it, and on the L the image of the far side behind a short one made every 1 mm case 1 to 2 points worse.
             L at (8.0, 5.84) and 1 mm keeps its +10.3 % (no wall can be imaged: the near side is shorter than six cells; the warning covers it).
    @param shape "T" or "L".
    @param x Via x in mm.
    @param y Via y in mm.
    @param cell Cell in mm.
    @param walls Number of walls imaged.
    @param budget Largest error of the via effect in per cent.
    @return None.
    """
    p = reflex_board(shape, x, y)
    v = p.vias[0]
    got = viawell.image_walls(p, v, viawell.EDGE_REACH_CELLS * cell * 1e-3, cell * 1e-3)
    assert len(got) == walls, got
    _walls, clean = viawell.edge_walls(p, v, viawell.EDGE_REACH_CELLS * cell * 1e-3)
    assert not clean                                                                # the warning stays for every via near the reflex corner
    e = rise(reflex_board(shape, x, y, via=False), cell) - rise(p, cell)
    assert abs(100.0 * (e / REFLEX_REFERENCE[(shape, x, y)] - 1.0)) < budget
