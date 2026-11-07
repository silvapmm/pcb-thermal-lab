#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_solid3d_sliver_cells.py
@brief The 3D solid on a board with an outline: the cut-cell links (aperture of the shared face) and the edge film at the closest outline point.
@details Before the change the 3D solid scaled the in-plane conductivity of every slab by the cover of the cell and joined cells by the harmonic mean, so the link into a sliver
         of a cell (cover 0.01 to 0.1) was 2c / (1 + c) of a full link and the edge film sat on the sliver node behind a cover-scaled conduction: the heat of the edge column could
         not reach the sliver and the hottest point jumped by 16 K (13 % of the rise) between covers 0.01 and 0.02 at an edge coefficient of 200 W/m2K and 1 mm, and by 1.6 K at the
         default 10 (research/cut-cell-links README 10.1). The tests compare the solid with an independent two-sheet solver (tests/helpers/indep_sheet.py, which imports nothing from
         the program), with the same board drawn as an aligned rectangle in the solid itself, and check the structure of the matrix and the heat balance.
         The covers of the sliver board are made exact here (the program's cover is sampled 8 x 8 on this branch, so a sliver of 0.02 would be 0 or 0.125): `Board.cover` is replaced by
         the exact overlap of the cell with the bounding box of the outline for the duration of a test.
"""

import math
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "helpers"))

import indep_sheet as ind                                    # noqa: E402
from pcbthermal import Problem, geometry, model, solid3d     # noqa: E402

AMB = 25.0
FINE = (0.5e-3, 0.25e-3, 0.125e-3)                           # Cells of the independent reference (extrapolated)


def sliver_board(c, h_side):
    """!
    @brief The board of the cut-cell study: the left edge column [5, 6] mm is covered by the fraction c.
    @param c Cover of the edge column (0 to 1).
    @param h_side Edge coefficient in W/m2K.
    @return Problem (30 x 30 mm box, 2 layers, full copper, a 2 W part, outline from x = 6 - c).
    """
    e = 6.0 - c
    p = Problem.new(30, 30, 2, h_side=h_side).add_full_copper()
    p.add_heater(1, 2.0, rect=(8.0, 13.5, 11.0, 16.5), name="U")
    p.set_outline([[e, 5], [25, 5], [25, 25], [e, 25]])
    return p


def sliver_rect(c, h_side):
    """!
    @brief The same board drawn as an aligned rectangle (no outline, so no cut cell).
    @param c Cover of the edge column of `sliver_board`.
    @param h_side Edge coefficient in W/m2K.
    @return Problem.
    """
    e = 6.0 - c
    p = Problem.new(25 - e, 20, 2, h_side=h_side).add_full_copper()
    p.add_heater(1, 2.0, rect=(8.0 - e, 8.5, 11.0 - e, 11.5), name="U")
    return p


def reference(c, h_side):
    """!
    @brief Peak temperature of the sliver board from the independent two-sheet solver (three cells, extrapolated).
    @param c Cover of the edge column.
    @param h_side Edge coefficient in W/m2K.
    @return degC.
    """
    e = 6.0 - c
    src = ((8 - e) * 1e-3, 8.5e-3, (11 - e) * 1e-3, 11.5e-3)
    return ind.richardson(lambda h: ind.solve((25 - e) * 1e-3, 20e-3, h, h_side, src)[0] + AMB, FINE)[0]


def exact_box_cover(self, nx, ny, dx, dy, samples=8, minimum=0.01):
    """!
    @brief Replacement of `Board.cover`: the exact overlap of every cell with the bounding box of the outline (the sliver board is an axis-aligned rectangle).
    @param self Board.
    @param nx Cells along x.
    @param ny Cells along y.
    @param dx Cell width in metres.
    @param dy Cell height in metres.
    @param samples Ignored (the cover is exact).
    @param minimum Smallest cover kept.
    @return Array (ny, nx).
    """
    if not self.has_outline():
        return np.ones((ny, nx))                                     # A rectangle: every cell is on the board
    o = np.asarray(self.outline, dtype=float)                       # The outline is stored in metres
    x0, x1, y0, y1 = o[:, 0].min(), o[:, 0].max(), o[:, 1].min(), o[:, 1].max()
    ox = np.clip(np.minimum((np.arange(nx) + 1) * dx, x1) - np.maximum(np.arange(nx) * dx, x0), 0, None) / dx
    oy = np.clip(np.minimum((np.arange(ny) + 1) * dy, y1) - np.maximum(np.arange(ny) * dy, y0), 0, None) / dy
    out = oy[:, None] * ox[None, :]
    return np.where(out >= minimum, out, 0.0)


@pytest.fixture
def exact_cover(monkeypatch):
    """!
    @brief Make the cover of the sliver boards exact for the length of a test.
    @param monkeypatch pytest fixture.
    @return None.
    """
    monkeypatch.setattr(model.Board, "cover", exact_box_cover)


def peak(p, cell=1.0):
    """!
    @brief Hottest temperature of the 3D solid.
    @param p Problem.
    @param cell Cell in mm.
    @return degC.
    """
    return solid3d.solve_steady(p, cell_mm=cell).t_max


def test_cover_replacement_is_exact(exact_cover):
    """!
    @brief The test helper gives the edge column the cover c (and 1 elsewhere on the board).
    @param exact_cover Fixture.
    """
    p = sliver_board(0.02, 10.0)
    cov = p.board.cover(30, 30, 1e-3, 1e-3)
    assert cov[10, 5] == pytest.approx(0.02) and cov[10, 6] == pytest.approx(1.0) and cov[10, 4] == 0.0 and cov[3, 10] == 0.0


def test_sliver_hottest_point_does_not_jump_at_the_default_edge_coefficient(exact_cover):
    """!
    @brief h_side 10 (the default): the error against the independent solver changes by little over the covers 0.01 to 1 (before the change +1.78 K at c = 0.02, +0.15 at 0.01).
    @param exact_cover Fixture.
    """
    err = {c: peak(sliver_board(c, 10.0)) - reference(c, 10.0) for c in (0.01, 0.02, 0.05, 0.1, 0.5, 1.0)}
    assert max(err.values()) - min(err.values()) < 0.45, err
    assert all(abs(e) < 0.5 for e in err.values()), err


def test_sliver_hottest_point_does_not_jump_at_a_stiff_edge(exact_cover):
    """!
    @brief h_side 200: the error against the independent solver, minus its value at c = 1 (the known offset of the 3D solid at a stiff edge), stays within 1 K for every cover
           (before the change +16 K between c = 0.01 and 0.02).
    @param exact_cover Fixture.
    """
    base = peak(sliver_board(1.0, 200.0)) - reference(1.0, 200.0)
    for c in (0.01, 0.02, 0.05, 0.1, 0.25):
        e = peak(sliver_board(c, 200.0)) - reference(c, 200.0)
        assert abs(e - base) < 1.0, (c, e, base)


def test_sliver_board_agrees_with_the_same_board_drawn_as_a_rectangle(exact_cover):
    """!
    @brief The outline and the aligned rectangle of the same board give the hottest point within 0.5 K at h_side 10 and within 1 K at 200, at covers 0.02 and 0.1
           (before the change +1.7 K and +16 K at c = 0.02, 1 mm).
    @param exact_cover Fixture.
    """
    for hs, tol in ((10.0, 0.5), (200.0, 1.0)):
        for c in (0.02, 0.1):
            assert abs(peak(sliver_board(c, hs)) - peak(sliver_rect(c, hs))) < tol, (hs, c)


def test_energy_balance_and_matrix_structure_on_slivers(exact_cover):
    """!
    @brief Heat to the air equals the power to 1e-9, the matrix is symmetric, has no positive off-diagonal entry and is diagonally dominant (an M-matrix) on a sliver board.
    @param exact_cover Fixture.
    """
    for hs in (10.0, 200.0, 2000.0):
        p = sliver_board(0.02, hs)
        r = solid3d.solve_steady(p, cell_mm=1.0)
        assert abs(r.balance_error) < 1e-9
        K = solid3d.Solid(p, 1.0).K.tocsr()
        assert abs(K - K.T).max() <= 1e-12 * abs(K).max()
        off = K - __import__("scipy.sparse", fromlist=["diags"]).diags(K.diagonal())
        assert off.max() <= 1e-15 * abs(K).max()                      # No positive off-diagonal entry
        assert (K.diagonal() + off.sum(axis=1).A1).min() >= -1e-12 * abs(K).max()    # Row sums are the (non-negative) conductances to the ambient


def turned_pair(angle, h_side):
    """!
    @brief A 20 mm square board turned by `angle` degrees about its centre in a 32 mm box (the part stays on the grid), and the same continuum problem in its own frame.
    @param angle Turn of the board in degrees.
    @param h_side Edge coefficient in W/m2K.
    @return Tuple (board with an outline, frame board, part polygon of the frame in metres).
    """
    c, hw = 16.0, 10.0
    a = math.radians(angle)

    def rot(x, y):
        return [c + (x - c) * math.cos(a) - (y - c) * math.sin(a), c + (x - c) * math.sin(a) + (y - c) * math.cos(a)]

    p = Problem.new(32, 32, 2, h_side=h_side).add_full_copper()
    px, py = c + 3.5 + 0.5, c + 0.5                                  # The part centre of the study: 3.5 mm off the centre, on a cell centre
    p.add_heater(1, 2.0, rect=(px - 1.5, py - 1.5, px + 1.5, py + 1.5), name="U")
    p.set_outline([rot(c + x, c + y) for x, y in ((-hw, -hw), (hw, -hw), (hw, hw), (-hw, hw))])
    # Frame: the board axes are the rotated ones; the part (a square on the grid) is turned by -angle about the board centre
    cb, ca, sa = hw, math.cos(-a), math.sin(-a)
    fx, fy = cb + (px - c) * ca - (py - c) * sa, cb + (px - c) * sa + (py - c) * ca
    pts = [[fx + x * ca - y * sa, fy + x * sa + y * ca] for x, y in ((-1.5, -1.5), (1.5, -1.5), (1.5, 1.5), (-1.5, 1.5))]
    f = Problem.new(20, 20, 2, h_side=h_side).add_full_copper()
    f.add_heater(1, 2.0, polygon=pts, name="U")
    return p, f, np.array(pts) * 1e-3


@pytest.mark.parametrize("angle", [10.0, 20.0, 30.0])
def test_turned_square_against_its_own_frame_and_the_independent_solver(angle):
    """!
    @brief A turned square board: the 3D solid on the outline agrees with the solid on the same board in its own frame (an aligned rectangle with a turned part) within 0.4 K at the
           default edge coefficient and within 3 K at 200 W/m2K (before the change 11 K), and with the independent two-sheet solver within 1 K at 10.
    @param angle Turn of the board in degrees.
    """
    for hs, tol in ((10.0, 0.4), (200.0, 3.0)):
        p, f, poly = turned_pair(angle, hs)
        turned, frame = peak(p), peak(f, 0.5)
        assert abs(turned - frame) < tol, (angle, hs, turned, frame)
    p, f, poly = turned_pair(angle, 10.0)
    ref = ind.richardson(lambda h: ind.solve(20e-3, 20e-3, h, 10.0, poly, poly=True)[0] + AMB, FINE)[0]
    assert abs(peak(p) - ref) < 1.0              # 0.8 K observed: the offset of the 3D solid from a two-sheet model, not a cut-cell effect


def test_rectangle_drawn_as_an_outline_equals_the_rectangle():
    """!
    @brief The outline that follows the edge of the box exactly and the rectangle without an outline give the same hottest point (the edge film of a whole cell is the same expression).
    """
    for hs in (10.0, 200.0):
        o = Problem.new(20, 20, 2, h_side=hs).add_full_copper()
        o.add_heater(1, 2.0, rect=(8, 8, 11, 11), name="U")
        r = Problem.new(20, 20, 2, h_side=hs).add_full_copper()
        r.add_heater(1, 2.0, rect=(8, 8, 11, 11), name="U")
        o.set_outline([[0, 0], [20, 0], [20, 20], [0, 20]])
        assert abs(peak(o) - peak(r)) < 0.05, hs


def test_outline_edge_conductance_adds_up_to_the_film_on_the_perimeter():
    """!
    @brief With a very good conductor (the copper slabs) the edge conductance of a turned square tends to h_side times the perimeter times the slab thickness: at most 1 % short in the
           copper slabs, which the signed distance (positive and negative) keeps.
    """
    p, f, poly = turned_pair(20.0, 200.0)
    s = solid3d.Solid(p, 1.0)
    per = 4 * 20e-3
    for slab in (s.board_slab[0], s.board_slab[1]):
        g = s.g["sides"].reshape(s.ns, s.ny, s.nx)[slab].sum()
        dz = s.slabs[slab]["dz"].flat[0]
        assert g == pytest.approx(200.0 * per * dz, rel=0.01)


def test_floor_of_the_film_denominator_keeps_the_matrix_positive():
    """!
    @brief A very stiff edge (1e5 W/m2K, the limit of Board.validate) on a sliver keeps the conductances to the ambient positive and the solution finite.
    """
    p = sliver_board(0.05, 1.0e5)
    s = solid3d.Solid(p, 1.0)
    assert (s.g["sides"] >= 0).all() and np.isfinite(s.g["sides"]).all()
    assert np.isfinite(peak(p))


def test_face_apertures_of_a_rectangle_and_an_outline_on_grid_lines():
    """!
    @brief A rectangle larger than the grid has all apertures 1; a rectangle whose sides lie on grid lines has aperture 0 on the faces along its sides and 1 inside.
    """
    nx = ny = 6
    ax, ay = geometry.face_apertures([[-1, -1], [7, -1], [7, 7], [-1, 7]], nx, ny, 1.0, 1.0)
    assert np.allclose(ax, 1.0) and np.allclose(ay, 1.0)
    ax, ay = geometry.face_apertures([[1, 1], [5, 1], [5, 5], [1, 5]], nx, ny, 1.0, 1.0)     # Sides on the grid lines x, y = 1 and 5
    assert ax[2, 0] == 0.0 and ax[2, 4] == 0.0 and np.allclose(ax[1:5, 1:4], 1.0)
    assert ay[0, 2] == 0.0 and ay[4, 2] == 0.0 and np.allclose(ay[1:4, 1:5], 1.0)


def brute_apertures(poly, nx, ny, dx, dy, m=2000):
    """!
    @brief Apertures by m point samples on every face (resolution 1/m).
    @param poly Closed polygon (n, 2) in metres.
    @param nx Cells along x.
    @param ny Cells along y.
    @param dx Cell width in metres.
    @param dy Cell height in metres.
    @param m Samples per face.
    @return Tuple (ax, ay).
    """
    t = (np.arange(m) + 0.5) / m
    ax, ay = np.zeros((ny, nx - 1)), np.zeros((ny - 1, nx))
    for j in range(nx - 1):
        yy = ((np.arange(ny)[:, None] + t[None]) * dy).ravel()
        ax[:, j] = geometry.points_in_polygon(np.full(yy.size, (j + 1) * dx), yy, poly).reshape(ny, m).mean(1)
    for i in range(ny - 1):
        xx = ((np.arange(nx)[:, None] + t[None]) * dx).ravel()
        ay[i, :] = geometry.points_in_polygon(xx, np.full(xx.size, (i + 1) * dy), poly).reshape(nx, m).mean(1)
    return ax, ay


@pytest.mark.parametrize("angle", [7.0, 23.0, 45.0])
def test_face_apertures_against_point_sampling_at_a_reentrant_corner(angle):
    """!
    @brief A turned notched polygon whose spike crosses some faces twice: the apertures equal the point-sampled ones within the sampling resolution (at these angles no side lies on a grid line).
    @param angle Turn in degrees about (6, 6) (mm, in metres here).
    """
    pts = [(1, 1), (11, 1), (11, 11), (7, 11), (7, 5), (5, 5), (5, 11), (1, 11)]               # A U-shaped notch: faces cross the polygon twice
    a = math.radians(angle)
    poly = np.array([[6 + (x - 6) * math.cos(a) - (y - 6) * math.sin(a), 6 + (x - 6) * math.sin(a) + (y - 6) * math.cos(a)] for x, y in pts]) * 1e-3
    ax, ay = geometry.face_apertures(poly, 12, 12, 1e-3, 1e-3)
    bx, by = brute_apertures(poly, 12, 12, 1e-3, 1e-3)
    assert np.abs(ax - bx).max() < 2e-3
    assert np.abs(ay - by).max() < 2e-3


def test_signed_distance_to_outline_of_a_square():
    """!
    @brief Distances to a square: positive inside, negative outside, the nearest side or corner.
    """
    sq = [[0, 0], [10, 0], [10, 10], [0, 10]]
    d = geometry.signed_distance_to_outline(sq, np.array([5.0, 1.0, -3.0, 13.0]), np.array([5.0, 5.0, 5.0, 14.0]))
    assert d == pytest.approx([5.0, 1.0, -3.0, -math.hypot(3.0, 4.0)])
