#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_block_exact_cover.py
@brief A metal block covers every cell by the exact area of the block polygon on the board (the rule of the board cover and of the parts), not by a 4 x 4 sampling times the board cover.
@details Closed-form references: the area of a rectangle (turned or not) cut by a straight outline side is a trapezoid area, computed here by a
         half-plane clip written for the test; the contact conductance of a block over full copper is its exact area over the interface resistance.
"""

import numpy as np
import pytest

from pcbthermal import Problem, SolverOptions, simulate
from pcbthermal import blocks, fdm, fvm


def turned_rect(cx, cy, w, h, deg):
    """!
    @brief Corners of a rectangle turned about its centre.
    @param cx Centre x in mm.
    @param cy Centre y in mm.
    @param w Width in mm.
    @param h Height in mm.
    @param deg Angle in degrees.
    @return List of four [x, y] corners in mm.
    """
    a = np.radians(deg)
    r = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
    c = np.array([[-w, -h], [w, -h], [w, h], [-w, h]]) / 2.0
    return ((c @ r.T) + [cx, cy]).tolist()


def area_right_of(poly, x0):
    """!
    @brief Area of a convex polygon to the right of the line x = x0 (Sutherland-Hodgman against one half-plane, shoelace).
    @param poly Vertices (n, 2) in any unit.
    @param x0 Limit in the same unit.
    @return Area in the squared unit.
    """
    pts, out = [tuple(v) for v in poly], []
    for i, cur in enumerate(pts):
        prev = pts[i - 1]
        if (cur[0] >= x0) != (prev[0] >= x0):
            t = (x0 - prev[0]) / (cur[0] - prev[0])
            out.append((x0, prev[1] + t * (cur[1] - prev[1])))
        if cur[0] >= x0:
            out.append(cur)
    q = np.array(out)
    x, y = q[:, 0], q[:, 1]
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def board(deg, outline):
    """!
    @brief A 60 x 40 mm two-layer board of full copper, a 3 W part and a 3 mm aluminium block turned by deg degrees, on the bottom face.
    @param deg Angle of the block in degrees.
    @param outline True to cut the board at x = 20.4 mm.
    @return Problem.
    """
    p = Problem.new(60, 40, 2).add_full_copper()
    if outline:
        p.set_outline([[20.4, 0], [60, 0], [60, 40], [20.4, 40]])
    p.add_heater(1, 3.0, rect=(35, 15, 45, 25), name="U")
    p.add_heatsink(2, 15.0, polygon=turned_rect(25.0, 19.6, 29.8, 23.7, deg), thickness_mm=3.0, k=205.0, name="Al")
    return p


@pytest.mark.parametrize("deg", [0.0, 20.0, 37.0])
@pytest.mark.parametrize("cell", [2.0, 1.0, 0.7])
def test_the_block_area_on_the_grid_is_the_exact_area_across_an_outline(deg, cell):
    p = board(deg, True)
    nx, ny = int(round(60 / cell)), int(round(40 / cell))
    poly_mm = p.heatsinks[0].polygon * 1e3
    exact = area_right_of(poly_mm, 20.4) * 1e-6
    for build in (lambda: fvm.Network(p, nx, ny), lambda: fvm.Network(p, nx, ny, cut_cells=False)):
        net = build()
        got = sum(i["cov"].sum() for i in net.block_info) * net.dx * net.dy
        assert got == pytest.approx(exact, rel=1e-12)


def test_contact_conductance_over_full_copper_is_the_exact_area_over_the_interface_resistance():
    # Closed form: with the copper fill 1 under the whole block the contact is area / R'' (the 4 x 4 sampling read 0.3 to 0.8 % of the area wrong here)
    p = board(20.0, False)
    net = fvm.Network(p, 43, 29)
    a = p.heatsinks[0]
    exact = area_right_of(a.polygon * 1e3, -1e9) * 1e-6
    g = sum(i["g_link"].sum() for i in net.block_info)
    assert g == pytest.approx(exact / max(a.interface_resistance(), 1e-7), rel=1e-9)


def test_a_rectangle_on_the_grid_lines_is_unchanged():
    poly = np.array([[0.004, 0.006], [0.020, 0.006], [0.020, 0.018], [0.004, 0.018]])
    from pcbthermal.geometry import coverage_fraction
    old = coverage_fraction(poly, 30, 20, 0.002, 0.002, samples=4)
    assert np.array_equal(blocks.block_cover(poly, None, 30, 20, 0.002, 0.002), old)


def test_a_polygon_that_crosses_itself_keeps_the_sampled_rule():
    bow = np.array([[0.004, 0.004], [0.020, 0.016], [0.020, 0.004], [0.004, 0.016]])
    from pcbthermal.geometry import coverage_fraction
    assert np.array_equal(blocks.block_cover(bow, None, 30, 20, 0.001, 0.001), coverage_fraction(bow, 30, 20, 0.001, 0.001, samples=4))


@pytest.mark.parametrize("model", ["fvm", "fdm", "solid3d"])
def test_energy_balance_closes_with_a_turned_block_across_the_outline(model):
    for deg in (0.0, 20.0, 35.0):
        r = simulate(board(deg, True), SolverOptions(models=(model,), cell_mm=2.0)).results[model]
        assert abs(r.balance_error) < 1e-6
        assert np.isfinite(r.t_max)


@pytest.mark.parametrize("model", ["fvm", "fdm"])
def test_the_coarse_cell_follows_the_fine_cell_more_closely_than_the_sampled_cover_did(model):
    # Turned 20 degrees across the cut: against the 0.5 mm cell the 2 mm cell was 0.70 K (FVM) and 0.62 K (FDM) off with the sampled cover and is 0.70 and
    # 0.61 K with the exact area (the cell error is not the block's): a bound of 0.8 K keeps it from growing back (the rest of it is the cut-cell treatment of the board, not the block)
    hot = {c: simulate(board(20.0, True), SolverOptions(models=(model,), cell_mm=c)).results[model].t_max for c in (2.0, 0.5)}
    assert abs(hot[2.0] - hot[0.5]) < 0.8
