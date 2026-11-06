#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_part_across_outline.py
@brief A part that crosses the board outline heats only the board part of the cells it covers: the weight is the share of the cell that is in
       both the part and the board, scaled to the board cover the model uses, so a cut cell does not get 1/cover too much power density
       (FVM, FDM and 3D solid); the heater and zone statistics leave out the cells off the board.
"""

import math

import numpy as np
import pytest

from pcbthermal import Problem, analysis, api, fdm, fvm, solid3d
from pcbthermal.examples import example_board
from pcbthermal.geometry import coverage_fraction, part_weights, polygon_area

A = 31.0 / 3.0                                  # The stem of the small T starts here (mm); on a grid line for a cell of 1/3 mm


def small_t():
    """!
    @brief A small T board (30 x 24 mm, two copper planes) with a 2 W part over its re-entrant corner.
    @return Problem.
    """
    b = 30.0 - A
    p = Problem.new(30.0, 24.0, 2, h_side=10.0).add_full_copper()
    p.add_heater(1, 2.0, rect=(9, 10, 12, 14), name="U")
    p.set_outline([[0, 12], [A, 12], [A, 0], [b, 0], [b, 12], [30, 12], [30, 24], [0, 24]])
    return p


@pytest.mark.parametrize("model", [fvm, fdm, solid3d])
def test_cut_cells_match_the_grid_aligned_reference(model):
    # At 1/3 mm the stem edge x = 31/3 mm is on a grid line (no cell is cut); at 0.5 mm it cuts a column of cells under the part, leaving
    # 1/3 of each on the board. Measured: FVM +0.57, FDM -0.46, 3D +0.70 K. The old weight (part cover x whole cell) was 6 to 8 K too hot, and
    # the plain intersection without the board cover (cover 1/4, part weight 3/8 in the cut cells) left the FVM 1.5 K too hot.
    ref = model.solve_steady(small_t(), cell_mm=1.0 / 3.0).t_max
    cut = model.solve_steady(small_t(), cell_mm=0.5).t_max
    assert abs(cut - ref) < 0.8


def test_power_density_of_a_cut_cell_is_not_inflated():
    # Regression: the cell column cut by the stem edge has 2/3 of its area on the board and the part covers it all. The power per unit of
    # board area must be that of a whole cell (the old code gave the cut cell the power of a whole cell, 1/cover too much density).
    for net in (fvm.Network(small_t(), 30, 24), solid3d.Solid(small_t(), cell_mm=1.0)):
        q = net.Q.reshape(-1, 24, 30)
        q = q[np.argmax(q.reshape(q.shape[0], -1).sum(axis=1))]       # The layer (FVM) or slab (3D solid) that carries the part
        cover = net.cover
        i, j = 10, 10                            # Row y 10 to 11 mm, column x 10 to 11 mm: the edge x = 10.333 mm cuts it, the part covers it all
        assert 0.0 < cover[i, j] < 1.0
        full = q[i, j + 1]                       # The next column is whole board and whole part
        assert q[i, j] / cover[i, j] == pytest.approx(full, rel=1e-12)
        assert q[i, j] / full < 0.9


@pytest.mark.parametrize("model", [fvm, solid3d])
def test_density_is_uniform_on_the_board_part_of_a_round_board(model):
    # A part across the edge of a round board (outline of 64 sides, off the grid lines): every cell that lies wholly inside the part gets the
    # same power per unit of board area, whether the outline cuts it or not, and the cells off the board get nothing.
    p = Problem.new(40.0, 40.0, 2, h_side=10.0).add_full_copper()
    t = np.linspace(0.0, 2.0 * np.pi, 64, endpoint=False)
    p.set_outline(np.column_stack([20.0 + 18.3 * np.cos(t), 20.0 + 18.3 * np.sin(t)]).tolist())
    p.add_heater(1, 1.5, rect=(34.6, 14.2, 40.0, 25.8), name="U")
    net = fvm.Network(p, 40, 40) if model is fvm else solid3d.Solid(p, cell_mm=1.0)
    q = net.Q.reshape(-1, 40, 40)
    q = q[np.argmax(q.reshape(q.shape[0], -1).sum(axis=1))]
    assert q.sum() == pytest.approx(1.5, rel=1e-12)
    whole = coverage_fraction(p.heaters[0].polygon, 40, 40, 1e-3, 1e-3, 8) >= 1.0
    cut = whole & (net.cover > 0) & (net.cover < 1)
    assert cut.sum() >= 3
    density = q[whole & (net.cover > 0)] / net.cover[whole & (net.cover > 0)]
    assert np.ptp(density) <= 1e-12 * density.max()
    assert q[net.cover == 0].sum() == 0.0


@pytest.mark.parametrize("cell", [1.0, 0.5])
def test_total_power_is_exact_in_every_model(cell):
    p = small_t()
    nx, ny = int(round(30.0 / cell)), int(round(24.0 / cell))
    assert fvm.Network(p, nx, ny).Q.sum() == pytest.approx(2.0, rel=1e-12)
    assert fdm.Network(p, cell_mm=cell).Q.sum() == pytest.approx(2.0, rel=1e-12)
    assert solid3d.Solid(p, cell_mm=cell).Q.sum() == pytest.approx(2.0, rel=1e-12)


@pytest.mark.parametrize("model", [fvm, fdm, solid3d])
def test_board_without_outline_and_a_rectangle_outline_are_unchanged(model):
    # Values of the example board at a 2 mm cell: the helper falls back to the plain coverage without an outline. The FVM and FDM were re-baselined when
    # the point via became the mean-potential via (develop gave 85.3423 and 84.6643); the 3D solid is unchanged at this cell (the via is a fraction of a cell)
    # (fix/laminate-nodes: the example board has partial copper, so the laminate nodes and the vertical correction of the rule moved the FVM and FDM by +0.008 and +0.004 K)
    stored = {fvm: 85.07464607663806, fdm: 84.26568445977094, solid3d: 85.48327731195374}
    assert model.solve_steady(example_board(), cell_mm=2.0).t_max == pytest.approx(stored[model], abs=1e-9)
    p = example_board()
    p.board.outline = np.array([[0, 0], [p.board.width, 0], [p.board.width, p.board.height], [0, p.board.height]])
    assert model.solve_steady(p, cell_mm=2.0).t_max == pytest.approx(stored[model], abs=0.02)


def test_part_weights_without_outline_is_the_coverage():
    poly = np.array([[1.3e-3, 1.1e-3], [4.9e-3, 1.1e-3], [4.9e-3, 3.7e-3], [1.3e-3, 3.7e-3]])
    assert np.array_equal(part_weights(poly, None, 10, 10, 1e-3, 1e-3, 8), coverage_fraction(poly, 10, 10, 1e-3, 1e-3, 8))


def test_part_weights_is_the_intersection_not_the_product():
    # Board for x < 1.5 mm, part for x > 1.25 mm, both over the whole height. Cell x 1 to 2 mm: part cover 0.75, board cover 0.5, in both 0.25
    # (x 1.25 to 1.5); the product of the covers (0.375) would put 50 % too much weight there.
    outline = np.array([[0, 0], [1.5e-3, 0], [1.5e-3, 3e-3], [0, 3e-3]])
    part = np.array([[1.25e-3, 0.0], [2.9e-3, 0.0], [2.9e-3, 3e-3], [1.25e-3, 3e-3]])
    w = part_weights(part, outline, 3, 3, 1e-3, 1e-3, 8)
    assert w[1, 1] == pytest.approx(0.25, abs=1e-12)
    prod = coverage_fraction(part, 3, 3, 1e-3, 1e-3, 8) * coverage_fraction(outline, 3, 3, 1e-3, 1e-3, 8)
    assert prod[1, 1] == pytest.approx(0.375, abs=1e-12)
    assert w[1, 2] == 0.0                                    # Cell x 2 to 3 mm is off the board
    # The weight is exact (part clipped to the outline, cut by the cells) and needs no normalisation to the model's cover: the exact board cover
    # of that cell is 0.5 and the part covers half of the board part of it, so the weight is the same 0.25 whatever `cover` is passed
    cover = np.ones((3, 3))
    cover[:, 1] = 0.5
    wc = part_weights(part, outline, 3, 3, 1e-3, 1e-3, 8, cover=cover)
    assert wc[1, 1] == pytest.approx(0.25, abs=1e-15)
    assert wc[1, 0] == 0.0 and wc[1, 2] == 0.0


def test_part_weights_sampled_fallback_for_two_concave_polygons_keeps_the_cover_normalisation():
    # Two concave polygons cannot be clipped exactly (Sutherland-Hodgman needs one convex operand): the sampled rule stays, with the model's cover
    # (here 0.6 for the cut cell): the share of the board samples in the part (0.5) times that cover
    outline = np.array([[0, 0], [1.5e-3, 0], [1.5e-3, 3e-3], [0.9e-3, 1.5e-3], [0, 3e-3]])      # A notch on the left side makes it concave
    part = np.array([[1.25e-3, 0.0], [2.9e-3, 0.0], [2.9e-3, 3e-3], [1.25e-3, 3e-3], [1.5e-3, 1.5e-3]])
    from pcbthermal import geometry
    assert geometry._part_on_board(part, outline) is None
    cover = np.ones((3, 3))
    cover[:, 1] = 0.6
    wc = part_weights(part, outline, 3, 3, 1e-3, 1e-3, 8, cover=cover)
    plain = part_weights(part, outline, 3, 3, 1e-3, 1e-3, 8)
    assert wc[1, 2] == 0.0 and plain[1, 2] == 0.0
    assert 0.0 < wc[1, 1] <= 0.6 and wc[1, 1] > plain[1, 1]


def test_turned_small_part_keeps_its_area_in_the_3d_solid():
    # A 3 mm square turned 45 degrees at a 0.125 mm cell: the 4 x 4 sampling kept 98.9 % of its area, 8 x 8 keeps 99.6 %
    a, h, c = math.radians(45.0), 1.5e-3, 30e-3
    poly = np.array([[c + x * math.cos(a) - y * math.sin(a), c + x * math.sin(a) + y * math.cos(a)] for x, y in ((-h, -h), (h, -h), (h, h), (-h, h))])
    d, n = 0.125e-3, 480
    share8 = part_weights(poly, None, n, n, d, d, 8).sum() * d * d / polygon_area(poly)
    share4 = coverage_fraction(poly, n, n, d, d, 4).sum() * d * d / polygon_area(poly)
    assert abs(share8 - 1.0) < 0.005 < abs(share4 - 1.0)
    # And the solid uses the finer sampling: a turned part on a small board puts the exact power with weights of the 8 x 8 kind
    p = Problem.new(20.0, 20.0, 2, h_side=10.0).add_full_copper()
    p.add_heater(1, 1.0, polygon=[[10 + x * math.cos(a) - y * math.sin(a), 10 + x * math.sin(a) + y * math.cos(a)] for x, y in ((-1.5, -1.5), (1.5, -1.5), (1.5, 1.5), (-1.5, 1.5))])
    net = solid3d.Solid(p, cell_mm=0.5)
    assert net.Q.sum() == pytest.approx(1.0, rel=1e-12)
    q = net.Q.reshape(-1, 40, 40)[net.board_slab[p.heaters[0].layer]]
    cov8 = coverage_fraction(p.heaters[0].polygon, 40, 40, 0.5e-3, 0.5e-3, 8)
    assert np.allclose(q, cov8 / cov8.sum(), rtol=0, atol=1e-15)          # The 8 x 8 weights (the 4 x 4 ones differ on the slanted sides)


def test_lumped_and_analytic_on_the_equivalent_rectangle_are_unchanged():
    # They run on the rectangle of the same area and do not use the part weights: values of develop before the change (small T, 1 mm).
    # The Analytic value was 237.28294907393308 until the edge loss of the real outline (perimeter kept by equivalent_rectangle) entered the model;
    # with an insulated edge it is still that. With the edge in the eigenfunctions of the series (feature/analytic-robin-edge) the edge loss is where the edge is:
    # 215.944 degC (it was 215.233 with the edge moved to the faces, +0.33 % of the rise; the FVM reads 231.87 at 1 mm, the equivalent rectangle is the limit here).
    o = api.SolverOptions(cell_mm=1.0)
    assert api._run_model(small_t(), "lumped", o).t_max == pytest.approx(217.73005348656147, abs=1e-9)
    assert api._run_model(small_t(), "analytic", o).t_max == pytest.approx(215.94408257945503, abs=1e-6)
    insulated = small_t()
    insulated.board.h_side = None
    assert api._run_model(insulated, "analytic", o).t_max == pytest.approx(237.28294907393308, abs=1e-9)


@pytest.mark.parametrize("model", [fvm, fdm, solid3d])
def test_statistics_leave_out_the_cells_off_the_board(model):
    # The cells (nodes) off the board hold the ambient: the old statistics took them in, so the mean under a part across the outline was
    # about 32 K low here, its ring 41 K low, and every full-copper zone of a board with an outline read a minimum of 25 degC.
    p = small_t()
    r = model.solve_steady(p, cell_mm=0.5)
    h = analysis.heater_stats(r, p)[0]
    assert h["t_max"] == pytest.approx(r.t_max, abs=1e-9)
    assert h["t_max"] - 10.0 < h["t_mean"] < h["t_max"]         # Measured 7.3 / 6.2 / 7.5 K below the maximum (FVM / FDM / 3D)
    assert h["t_ring"] > 195.0                                   # Measured 203.7 / 201.1 / 204.2 degC (old 163 to 164)
    for z in analysis.zone_stats(r, p):
        assert z["t_min"] > 150.0                                # Measured 158 to 162 degC (old 25: the ambient off the board)
    # Without an outline the weights are the plain 4 x 4 coverage of the part, as before the change
    q = example_board()
    rq = model.solve_steady(q, cell_mm=2.0)
    for h in q.heaters:
        if rq.grid == "nodes":
            continue                                             # The node test of the FDM did not change either
        cov = coverage_fraction(h.polygon, rq.T.shape[2], rq.T.shape[1], rq.dx, rq.dy, 4)
        T = rq.T[h.layer]
        assert analysis._footprint_stats(rq, h.polygon, h.layer, q.board.outline)[0] == pytest.approx(float((T * cov).sum() / cov.sum()), rel=1e-15)


def test_board_cover_and_part_weights_have_no_sampling_lattice_any_more():
    # The board cover (FVM, 3D solid, FDM node cover) and the weights of a part are exact since fix/exact-board-cover; only the fallback for two
    # concave polygons keeps the lattice of geometry.BOARD_SAMPLES
    import inspect
    from pcbthermal import geometry, model
    assert geometry.BOARD_SAMPLES == 8
    assert "samples" not in inspect.signature(model.Board.cover).parameters
    assert inspect.signature(part_weights).parameters["samples"].default == geometry.BOARD_SAMPLES


def test_board_cover_resolves_an_eighth_of_a_cell():
    # A vertical edge at 3/8 of a cell cuts it into 3/8 and 5/8: exact on the 8 x 8 lattice (the 4 x 4 lattice read 1/4 or 1/2)
    p = Problem.new(8.0, 4.0, 1).add_full_copper()
    p.set_outline([[0, 0], [3.375, 0], [3.375, 4], [0, 4]])
    cover = p.board.cover(8, 4, 1e-3, 1e-3)
    assert np.allclose(cover[:, 3], 0.375, atol=1e-12)
    assert np.allclose(cover[:, :3], 1.0) and np.allclose(cover[:, 4:], 0.0)


def test_edge_shift_scatter_of_the_fvm_stays_small_at_1_mm():
    # The stem edge of the small T moves over one cell (1 mm) in twelfths; the error against a fine grid (1/6 mm) must not jump from edge to
    # edge. Measured: spread 3.0 K with the 4 x 4 board cover, 1.4 K with 8 x 8 (the part weights were already 8 x 8).
    shifts = [10.0 + k / 12.0 for k in range(13)]

    def tee(a):
        q = small_t()
        q.set_outline([[0, 12], [a, 12], [a, 0], [30.0 - a, 0], [30.0 - a, 12], [30, 12], [30, 24], [0, 24]])
        return q

    err = [fvm.solve_steady(tee(a), cell_mm=1.0).t_max - fvm.solve_steady(tee(a), cell_mm=1.0 / 6.0).t_max for a in shifts]
    assert np.ptp(err) < 1.6
