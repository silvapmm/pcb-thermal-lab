#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_exact_cover.py
@brief The exact board cover and part weights (`geometry.exact_coverage`, `Board.cover`, `geometry.part_weights` with an outline): areas against analytic
       values and against clipping every cell, invariance to orientation, turn and shift, the FDM node cover, and the speed on a big outline.
"""

import math
import time

import numpy as np
import pytest

from pcbthermal import Problem, fdm, fvm, geometry, solid3d
from pcbthermal.geometry import clip_polygon, exact_coverage, part_weights, polygon_area, polygon_area_signed, polygon_overlap_area


def turned_square(side, angle, cx, cy):
    """!
    @brief A square turned by an angle.
    @param side Side in metres.
    @param angle Turn in radians.
    @param cx Centre x in metres.
    @param cy Centre y in metres.
    @return Vertices (4, 2) in metres, counter-clockwise.
    """
    h = side / 2
    p = np.array([[-h, -h], [h, -h], [h, h], [-h, h]])
    c, s = math.cos(angle), math.sin(angle)
    return p @ np.array([[c, s], [-s, c]]) + [cx, cy]


def clip_every_cell(poly, nx, ny, dx, dy):
    """!
    @brief Reference: the area of the polygon in every cell by clipping the polygon with the cell box (Sutherland-Hodgman).
    @param poly Polygon vertices in metres.
    @param nx Cells along x.
    @param ny Cells along y.
    @param dx Cell width in metres.
    @param dy Cell height in metres.
    @return Array (ny, nx) of fractions.
    """
    out = np.zeros((ny, nx))
    for i in range(ny):
        for j in range(nx):
            box = np.array([[j * dx, i * dy], [(j + 1) * dx, i * dy], [(j + 1) * dx, (i + 1) * dy], [j * dx, (i + 1) * dy]])
            c = clip_polygon(poly, box)
            out[i, j] = abs(polygon_area_signed(c)) / (dx * dy) if len(c) >= 3 else 0.0
    return out


@pytest.mark.parametrize("angle_deg", [0.0, 3.0, 17.0, 26.565, 45.0, 71.0, 90.0, 133.0])
def test_cover_area_of_a_turned_square_is_the_polygon_area_to_rounding(angle_deg):
    # Any turn, either orientation, a grid that does not divide the square: the area of the cover is the polygon area (the old 8 x 8 cover was off by
    # 0.64 % at 45 degrees and 1 mm, 0.38 % along a slope of 1/3)
    sq = turned_square(0.0137, math.radians(angle_deg), 0.0151, 0.0149)
    for poly in (sq, sq[::-1]):
        c = exact_coverage(poly, 30, 30, 1e-3, 1e-3)
        assert c.sum() * 1e-6 == pytest.approx(polygon_area(poly), rel=1e-12)
        assert c.min() >= 0.0 and c.max() <= 1.0


def test_cover_of_a_triangle_and_a_disc_match_the_closed_forms():
    tri = np.array([[1.3e-3, 1.1e-3], [11.7e-3, 2.9e-3], [4.1e-3, 9.3e-3]])
    area = 0.5 * abs((tri[1, 0] - tri[0, 0]) * (tri[2, 1] - tri[0, 1]) - (tri[2, 0] - tri[0, 0]) * (tri[1, 1] - tri[0, 1]))
    assert exact_coverage(tri, 14, 12, 0.9e-3, 0.95e-3).sum() * 0.9e-3 * 0.95e-3 == pytest.approx(area, rel=1e-12)
    # A regular 720-gon of radius 8.7 mm: its area is n/2 r^2 sin(2 pi / n), a slice of the disc in every cell it cuts
    t = np.linspace(0, 2 * np.pi, 720, endpoint=False)
    disc = np.c_[11.3e-3 + 8.7e-3 * np.cos(t), 12.1e-3 + 8.7e-3 * np.sin(t)]
    exact = 0.5 * 720 * 8.7e-3 ** 2 * math.sin(2 * math.pi / 720)
    assert exact_coverage(disc, 25, 25, 1e-3, 1e-3).sum() * 1e-6 == pytest.approx(exact, rel=1e-12)


def test_cover_equals_the_clip_of_every_cell_on_a_concave_polygon():
    l_shape = np.array([[2e-3, 2e-3], [20e-3, 2e-3], [20e-3, 10.3e-3], [10.2e-3, 10.3e-3], [10.2e-3, 19.7e-3], [2e-3, 19.7e-3]])
    got = exact_coverage(l_shape, 22, 22, 1e-3, 1e-3)
    assert np.abs(got - clip_every_cell(l_shape, 22, 22, 1e-3, 1e-3)).max() < 1e-12
    # A non-square cell and a polygon that leaves the grid: only the part inside is counted
    big = turned_square(0.03, math.radians(20.0), 0.01, 0.01)
    got = exact_coverage(big, 20, 16, 1.1e-3, 0.8e-3)
    assert np.abs(got - clip_every_cell(big, 20, 16, 1.1e-3, 0.8e-3)).max() < 1e-12


def test_cells_wholly_inside_are_exactly_one_and_those_outside_exactly_zero():
    # The snap: no rounding noise in cells nothing cuts, so "cover > 0" is the board mask
    rect = np.array([[0, 0], [25e-3, 0], [25e-3, 25e-3], [0, 25e-3]])
    assert np.array_equal(exact_coverage(rect, 25, 25, 1e-3, 1e-3), np.ones((25, 25)))
    sq = turned_square(0.016, math.radians(45.0), 0.0125, 0.0125)
    c = exact_coverage(sq, 25, 25, 1e-3, 1e-3)
    assert set(np.unique(c[(c < 1e-6) | (c > 1 - 1e-6)])) <= {0.0, 1.0}
    assert c[12, 12] == 1.0 and c[0, 0] == 0.0 and c[24, 24] == 0.0


def test_board_cover_is_exact_and_a_rectangle_is_all_ones():
    p = Problem.new(30.0, 30.0, 2).add_full_copper()
    assert np.array_equal(p.board.cover(30, 30, 1e-3, 1e-3), np.ones((30, 30)))
    p.set_outline([[15, 5.858], [24.142, 15], [15, 24.142], [5.858, 15]])             # A diamond (the case that the 8 x 8 lattice read 0.64 % high)
    cov = p.board.cover(30, 30, 1e-3, 1e-3, minimum=0.0)
    assert cov.sum() * 1e-6 == pytest.approx(polygon_area(p.board.outline), rel=1e-12)
    # Cells under the minimum are off the board
    assert (p.board.cover(30, 30, 1e-3, 1e-3)[cov < 0.01] == 0.0).all()


def test_part_weights_are_the_exact_overlap_of_part_and_outline_whatever_the_cut():
    # Part and outline both turned and cutting the same cells: the weights add up to the exact overlap area (the product of the covers does not)
    outline = turned_square(0.016, math.radians(30.0), 0.0125, 0.0125)
    for angle in (0.0, 11.0, 45.0, 80.0):
        part = turned_square(0.006, math.radians(angle), 0.0125 + 0.0055 * math.cos(math.radians(30)), 0.0125 + 0.0055 * math.sin(math.radians(30)))
        w = part_weights(part, outline, 25, 25, 1e-3, 1e-3)
        assert w.sum() * 1e-6 == pytest.approx(polygon_overlap_area(part, outline), rel=1e-12)
        # And in every cell: part x board, clipped by the cell box
        ref = np.zeros((25, 25))
        for i, j in zip(*np.nonzero(w > 0)):
            box = np.array([[j * 1e-3, i * 1e-3], [(j + 1) * 1e-3, i * 1e-3], [(j + 1) * 1e-3, (i + 1) * 1e-3], [j * 1e-3, (i + 1) * 1e-3]])
            ref[i, j] = polygon_overlap_area(clip_polygon(part, box), outline) / 1e-6 if len(clip_polygon(part, box)) >= 3 else 0.0
        assert np.abs(w - ref).max() < 1e-9


def test_part_weight_over_a_concave_outline_counts_each_piece_once():
    # A part across the notch of a U board: two pieces on the board, the bridge between them has no area
    u = np.array([[0, 0], [20e-3, 0], [20e-3, 20e-3], [14e-3, 20e-3], [14e-3, 8e-3], [6e-3, 8e-3], [6e-3, 20e-3], [0, 20e-3]])
    part = np.array([[3e-3, 5.5e-3], [17e-3, 5.5e-3], [17e-3, 12.5e-3], [3e-3, 12.5e-3]])
    w = part_weights(part, u, 20, 20, 1e-3, 1e-3)
    expect = 14e-3 * 2.5e-3 + 2 * 3e-3 * 4.5e-3                  # The strip below the notch plus the two arms (3 mm wide each, 4.5 mm up)
    assert w.sum() * 1e-6 == pytest.approx(expect, rel=1e-12)


def shifted_part_problem(shift_mm, angle_deg):
    """!
    @brief A round-ish board (a 24-gon) with a 3 mm, 2 W part across its edge, shifted and turned.
    @param shift_mm Shift of the part along x in mm.
    @param angle_deg Turn of the part in degrees.
    @return Problem.
    """
    t = np.linspace(0, 2 * np.pi, 24, endpoint=False)
    p = Problem.new(30.0, 30.0, 2, h_side=10.0).add_full_copper()
    p.set_outline(np.c_[15 + 10 * np.cos(t), 15 + 10 * np.sin(t)])
    a = math.radians(angle_deg)
    pts = turned_square(3.0, a, 24.6 + shift_mm, 15.0)
    p.add_heater(1, 2.0, polygon=pts.tolist(), name="U")
    return p


@pytest.mark.parametrize("model", [fvm, fdm, solid3d])
def test_total_power_and_heat_balance_do_not_depend_on_the_position_or_turn_of_a_part_across_the_edge(model):
    for shift, angle in ((0.0, 0.0), (0.37, 23.0), (0.8, 45.0)):
        r = model.solve_steady(shifted_part_problem(shift, angle), cell_mm=1.0)
        assert abs(r.balance_error) < 1e-8
        assert r.power_in == pytest.approx(2.0, rel=1e-12)


def test_hottest_point_of_the_turned_square_does_not_jump_at_45_degrees():
    # With the 8 x 8 cover the 20 mm square at 45 degrees read 0.97 K colder than at 40 degrees at 1 mm (the area was 0.64 % too large, the edge
    # losses and the volume with it); the exact cover removes it (0.025 K measured). The part is 3 mm, 2 W, h_side 10, two copper planes.
    def square(angle):
        h, a = 10.0, math.radians(angle)
        pts = [[15.0 + x * math.cos(a) - y * math.sin(a), 15.0 + x * math.sin(a) + y * math.cos(a)] for x, y in ((-h, -h), (h, -h), (h, h), (-h, h))]
        p = Problem.new(30.0, 30.0, 2, h_side=10.0).add_full_copper()
        p.set_outline(pts)
        p.add_heater(1, 2.0, rect=(14.0, 14.0, 17.0, 17.0), name="U")
        return p
    t40 = fvm.solve_steady(square(40.0), cell_mm=1.0).t_max
    t45 = fvm.solve_steady(square(45.0), cell_mm=1.0).t_max
    assert abs(t45 - t40) < 0.15


def test_fdm_node_cover_is_the_average_of_the_exact_cell_cover():
    p = shifted_part_problem(0.0, 0.0)
    net = fdm.Network(p, cell_mm=0.75)
    cells = exact_coverage(p.board.outline, 40, 40, p.board.width / 40, p.board.height / 40)
    expect = np.zeros((41, 41))
    count = np.zeros((41, 41))
    for di in (0, 1):
        for dj in (0, 1):
            expect[di:di + 40, dj:dj + 40] += cells
            count[di:di + 40, dj:dj + 40] += 1.0
    expect = expect / count
    expect = np.where(expect >= 0.01, expect, 0.0)
    assert np.allclose(net.cover, expect, atol=1e-12)


def test_exact_cover_of_a_big_outline_on_a_fine_grid_is_fast():
    # 200 mm round board of 1000 vertices at 0.25 mm: the sampled cover took about 1.4 s (edge walk in Python), the exact one milliseconds
    t = np.linspace(0, 2 * np.pi, 1000, endpoint=False)
    disc = np.c_[0.1 + 0.1 * np.cos(t), 0.1 + 0.1 * np.sin(t)]
    t0 = time.perf_counter()
    c = exact_coverage(disc, 800, 800, 0.25e-3, 0.25e-3)
    assert time.perf_counter() - t0 < 0.5
    assert c.sum() * (0.25e-3) ** 2 == pytest.approx(polygon_area(disc), rel=1e-12)


def test_sampled_fallback_remains_for_two_concave_polygons():
    a = np.array([[0, 0], [10e-3, 0], [10e-3, 10e-3], [5e-3, 4e-3], [0, 10e-3]])
    b = np.array([[2e-3, 1e-3], [12e-3, 1e-3], [8e-3, 6e-3], [12e-3, 11e-3], [2e-3, 11e-3]])
    assert geometry._part_on_board(b, a) is None
    w = part_weights(b, a, 12, 12, 1e-3, 1e-3)
    assert w.sum() * 1e-6 == pytest.approx(polygon_overlap_area(a, b), rel=0.02)
