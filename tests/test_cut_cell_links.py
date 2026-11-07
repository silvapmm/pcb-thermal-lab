#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_cut_cell_links.py
@brief The cut-cell treatment of the layered FVM (open-fraction links and the edge film in series with the conduction to the edge): geometry, matrix properties, the sliver
       defect, the spread over the position of the outline against an independent reference, the solvers, vias, laminate nodes, metal blocks and imported copper.
@details Evidence: research/cut-cell-links (README, its review) and docs/validation.md 32. The independent reference is tests/helpers/two_sheet.py (the aligned board in its own frame,
         its own assembly, nothing of the program).
"""

import functools
import logging
import math
import os
import sys
import time

import numpy as np
import pytest
import scipy.sparse as sp

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "helpers"))
import cut_cell_boards as bd                                    # noqa: E402
import cut_cell_study as study                                  # noqa: E402
import two_sheet as ind                                         # noqa: E402

from pcbthermal import Problem, copper, fvm                     # noqa: E402
from pcbthermal.geometry import exact_coverage, face_apertures, signed_distance_to_outline   # noqa: E402


def turned(pts, angle_deg, c):
    """!
    @brief Points turned about (c, c).
    @param pts List of (x, y).
    @param angle_deg Angle in degrees.
    @param c Centre of the turn (both coordinates, same unit as the points).
    @return Array (n, 2).
    """
    a = math.radians(angle_deg)
    R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    return (np.asarray(pts, float) - c) @ R.T + c


def brute_aperture(poly, nx, ny, dx, dy, m=2000):
    """!
    @brief Reference apertures by point sampling every face (the share of its sample points that lie inside the polygon, with the board required on both sides).
    @param poly Polygon (n, 2) in metres.
    @param nx Cells along x.
    @param ny Cells along y.
    @param dx Cell width in metres.
    @param dy Cell height in metres.
    @param m Samples per face.
    @return Tuple (ax, ay).
    """
    from pcbthermal.geometry import points_in_polygon
    t = (np.arange(m) + 0.5) / m
    ax = np.zeros((ny, nx - 1))
    ay = np.zeros((ny - 1, nx))
    e = 1e-7 * dx
    for i in range(ny):
        for j in range(1, nx):
            y, x = (i + t) * dy, np.full(m, j * dx)
            ax[i, j - 1] = (points_in_polygon(x - e, y, poly) & points_in_polygon(x + e, y, poly)).mean()
    for i in range(1, ny):
        for j in range(nx):
            x, y = (j + t) * dx, np.full(m, i * dy)
            ay[i - 1, j] = (points_in_polygon(x, y - e, poly) & points_in_polygon(x, y + e, poly)).mean()
    return ax, ay


L_SHAPE = np.array([[0, 0], [20, 0], [20, 8], [9, 8], [9, 20], [0, 20]]) * 1e-3
T_SHAPE = np.array([[0, 12], [10, 12], [10, 0], [20, 0], [20, 12], [30, 12], [30, 24], [0, 24]]) * 1e-3
NOTCH = np.array([[0, 0], [20, 0], [20, 20], [11, 20], [10.3, 5], [9.7, 20], [0, 20]]) * 1e-3


@pytest.mark.parametrize("shape", [L_SHAPE, T_SHAPE, NOTCH], ids=["L", "T", "notch"])
@pytest.mark.parametrize("angle", [0.0, 7.0, 23.0, 45.0])
def test_apertures_equal_point_sampling_on_reentrant_shapes(shape, angle):
    # The aperture of a face is the length of it that has board on BOTH sides: exact at a re-entrant corner and on a face the outline crosses twice (the notch)
    poly = turned(shape, angle, 10e-3) + 8e-3
    nx = ny = 36
    d = 1e-3
    ax, ay = face_apertures(poly, nx, ny, d, d)
    bx, by = brute_aperture(poly, nx, ny, d, d)
    assert abs(ax - bx).max() < 1e-3
    assert abs(ay - by).max() < 1e-3


def test_apertures_of_a_rectangle_on_the_grid_are_one_and_a_face_on_the_outline_is_zero():
    # Board 5 x 4 cells in a 8 x 6 grid: faces inside are 1, the faces ON the outline (board on one side only) are 0, outside are 0
    poly = np.array([[1, 1], [6, 1], [6, 5], [1, 5]]) * 1e-3
    c = exact_coverage(poly, 8, 6, 1e-3, 1e-3)
    ax, ay = face_apertures(poly, 8, 6, 1e-3, 1e-3, cover=c)
    assert np.all(ax[1:5, 1:5] == 1.0)
    assert np.all(ay[1:4, 1:6] == 1.0)
    assert np.all(ax[:, 0] == 0.0) and np.all(ax[:, 6] == 0.0)
    assert np.all(ay[0] == 0.0) and np.all(ay[4:] == 0.0)
    # the faces on the outline: x = 1 mm (ax[:, 0]) and x = 6 mm (ax[:, 5]) between rows 1..4
    assert np.all(ax[1:5, 0] == 0.0) and np.all(ax[1:5, 5] == 0.0)


def test_apertures_cost_on_a_big_outline():
    # 20 000 vertices on a 0.25 mm grid (400 x 400): the vectorised aperture takes about 0.1 s; and the distance of the cut cells (about 2000) well under a second
    n = 20000
    th = np.linspace(0, 2 * np.pi, n, endpoint=False)
    r = 0.05 + 0.002 * np.sin(40 * th)
    poly = np.column_stack([0.05 + r * np.cos(th), 0.05 + r * np.sin(th)])
    t0 = time.perf_counter()
    face_apertures(poly, 400, 400, 0.25e-3, 0.25e-3)
    t_ap = time.perf_counter() - t0
    c = exact_coverage(poly, 400, 400, 0.25e-3, 0.25e-3)
    cut = np.argwhere((c > 0) & (c < 1))
    t0 = time.perf_counter()
    signed_distance_to_outline(poly, (cut[:, 1] + 0.5) * 0.25e-3, (cut[:, 0] + 0.5) * 0.25e-3)
    t_d = time.perf_counter() - t0
    assert t_ap < 1.0, f"aperture build {t_ap:.2f} s"
    assert t_d < 2.0, f"distance of {len(cut)} cut cells {t_d:.2f} s"


def test_signed_distance_of_a_square_a_disc_and_a_reflex_corner():
    sq = np.array([[0, 0], [10, 0], [10, 10], [0, 10]]) * 1e-3
    pts = np.array([[5, 5], [1, 5], [5, 9.5], [-1, 5], [12, 12], [9.9, 0.2]]) * 1e-3
    d = signed_distance_to_outline(sq, pts[:, 0], pts[:, 1])
    assert d == pytest.approx(np.array([5, 1, 0.5, -1, -math.hypot(2, 2), 0.1]) * 1e-3, abs=1e-12)
    th = np.linspace(0, 2 * np.pi, 720, endpoint=False)
    disc = np.column_stack([5e-3 + 4e-3 * np.cos(th), 5e-3 + 4e-3 * np.sin(th)])
    pts = np.array([[5, 5], [8.5, 5], [9.5, 5], [5, 0.2]]) * 1e-3
    d = signed_distance_to_outline(disc, pts[:, 0], pts[:, 1])
    assert d == pytest.approx(np.array([4, 0.5, -0.5, -0.8]) * 1e-3, abs=2e-7)       # (the polygon of 720 sides is inside the circle by R (1 - cos(pi/720)) = 4 nm)
    # Reflex corner (9, 8) of the L: a point in the notch is OUTSIDE, a point on the other side of the corner is inside, though the nearest point of both is the VERTEX
    # (the side of one segment does not tell them apart: the even-odd test does)
    pts = np.array([[14, 14], [8, 14], [10, 6], [8.5, 7.5], [9.5, 8.5]]) * 1e-3
    d = signed_distance_to_outline(L_SHAPE, pts[:, 0], pts[:, 1])
    assert d == pytest.approx(np.array([-5, 1, 2, math.sqrt(0.5), -0.5]) * 1e-3, abs=1e-12)


def rectangle_problem(h_side, with_outline, cell=1.0):
    """!
    @brief A 20 x 16 mm two-layer board with a 2 W part, as a rectangle or as the same rectangle drawn as an outline.
    @param h_side Edge coefficient in W/m2K.
    @param with_outline True: the rectangle is given as an outline too.
    @param cell Unused (kept for symmetry with the other builders).
    @return Problem.
    """
    p = Problem.new(20, 16, 2, h_side=h_side).add_full_copper()
    p.add_heater(1, 2.0, rect=(7, 5, 10, 8), name="U")
    if with_outline:
        p.set_outline([[0, 0], [20, 0], [20, 16], [0, 16]])
    return p


@pytest.mark.parametrize("h_side", [0.0, 10.0, 2000.0])
def test_a_rectangle_drawn_as_an_outline_is_the_rectangle(h_side):
    # Square cells: the outline on the grid lines must give the links of the rectangle (aperture 1 where both cells are whole) and the same film (distance half a cell)
    a = fvm.Network(rectangle_problem(h_side, False), 20, 16)
    b = fvm.Network(rectangle_problem(h_side, True), 20, 16)
    assert abs(a.K - b.K).max() <= 1e-9 * abs(a.K).max()
    assert a.g_side == pytest.approx(b.g_side, rel=1e-9, abs=1e-12)
    ta = fvm.solve_steady(rectangle_problem(h_side, False), cell_mm=1.0).t_max
    tb = fvm.solve_steady(rectangle_problem(h_side, True), cell_mm=1.0).t_max
    assert ta == pytest.approx(tb, abs=1e-6)


def test_without_h_side_and_without_an_outline_the_matrix_is_the_earlier_one_bit_for_bit():
    p = rectangle_problem(0.0, False)
    a = fvm.Network(p, 20, 16)
    b = fvm.Network(p, 20, 16, cut_cells=False)
    assert a.aperture is None
    assert (a.K != b.K).nnz == 0


def test_the_film_of_a_whole_edge_cell_is_in_series_with_half_a_cell():
    # g = H L / (1 + H d / S) with d = dx / 2 on a rectangle (the corner has two edges, each with its own d)
    p = rectangle_problem(200.0, False)
    old = fvm.Network(p, 20, 16, cut_cells=False)
    new = fvm.Network(p, 20, 16)
    sp_ = new._physical_sheet()
    H = 200.0 * 0.8e-3
    for layer in range(2):
        i, j = 8, 0                                          # a left edge cell, away from the corners
        g0 = H * new.dy
        assert old.g_side[layer, i, j] == pytest.approx(g0, rel=1e-12)
        assert new.g_side[layer, i, j] == pytest.approx(g0 / (1.0 + H * 0.5 * new.dx / sp_[layer, i, j]), rel=1e-12)
        i, j = 0, 0                                          # the corner: two edges
        expect = H * new.dy / (1.0 + H * 0.5 * new.dx / sp_[layer, i, j]) + H * new.dx / (1.0 + H * 0.5 * new.dy / sp_[layer, i, j])
        assert new.g_side[layer, i, j] == pytest.approx(expect, rel=1e-12)
    assert (new.g_side <= old.g_side).all()


def turned_square(angle, h_side=200.0, **kw):
    """!
    @brief The 20 mm square board turned by `angle` (part on the grid).
    @param angle Turn in degrees.
    @param h_side Edge coefficient in W/m2K.
    @param kw Other options of `cut_cell_boards.edge_board`.
    @return Problem.
    """
    return bd.edge_board(angle=angle, h_side=h_side, pc=0.5, box=32.0, **kw)


@pytest.mark.parametrize("kw", [dict(angle=0.0), dict(angle=17.0), dict(angle=45.0), dict(angle=17.0, pattern=True), dict(angle=17.0, vias=True)],
                         ids=["aligned", "17deg", "45deg", "pattern", "vias"])
def test_energy_balance_steady_and_transient(kw):
    p = bd.edge_board(h_side=200.0, pc=0.5, box=32.0, **kw)
    r = fvm.solve_steady(p, cell_mm=1.0)
    assert abs(r.balance_error) < 1e-9
    net = fvm.Network(p, 32, 32)
    theta, res = net.solve_steady()
    out = net.power_out(theta)
    assert sum(out.values()) == pytest.approx(2.0, rel=1e-9)
    # Transient: the late-time temperature approaches the steady one and the heat leaving it approaches the power
    tr = fvm.solve_transient(p, t_end=400.0, n_out=4, cell_mm=2.0)
    steady = fvm.solve_steady(p, cell_mm=2.0)
    assert tr.t_max[-1] == pytest.approx(steady.t_max, rel=2e-2)


@pytest.mark.parametrize("c", [0.002, 0.01, 0.02, 0.1, 0.5, 1.0])
def test_matrix_is_symmetric_with_no_positive_off_diagonal_and_the_symmetric_lu_is_accepted(c, caplog):
    # A sliver of any cover: K stays symmetric, an M-matrix (no vias) and the symmetric LU of fvm.lu_factor passes its probe (no fallback warning)
    p = study.sliver_board(max(c, 0.011), 200.0)         # (below 0.01 the cell is dropped as in the program: the next case checks that)
    net = fvm.Network(p, 30, 30)
    K = net.K.tocsr()
    keep = np.flatnonzero(np.repeat(net.active.ravel()[None, :], net.nl, axis=0).ravel())
    K = K[keep][:, keep].tocsr()
    assert abs(K - K.T).max() <= 1e-12 * abs(K).max()
    off = K - sp.diags(K.diagonal())
    assert (off.data > 1e-14 * abs(K).max()).sum() == 0
    with caplog.at_level(logging.WARNING, logger="pcbthermal.fvm"):
        theta, _ = net.solve_steady()
    assert "non-symmetric" not in caplog.text and "default mode" not in caplog.text
    assert np.isfinite(theta).all()


def test_sliver_below_the_minimum_cover_is_dropped_and_the_curve_is_continuous():
    # The program jumped by +3.6 K at 200 W/m2K (and +9.8 K at 2000) between the cover 0.01 and 0.02 (the film of the sliver sat behind a link of 2c/(1+c))
    for hs, bound in ((200.0, 0.3), (2000.0, 0.3), (10.0, 0.4)):
        t = {c: fvm.solve_steady(study.sliver_board(c, hs), cell_mm=1.0).t_max for c in (0.01, 0.02, 0.05, 0.1, 0.25, 0.5, 1.0)}
        assert abs(t[0.02] - t[0.01]) < bound, (hs, t)
    # the error against the independent reference (the same board as an aligned rectangle) is smooth in the cover: its range over 0.01, 0.02 and 0.1 is under 0.3 K
    err = [fvm.solve_steady(study.sliver_board(c, 200.0), cell_mm=1.0).t_max - study.sliver_reference(c, 200.0) for c in (0.01, 0.02, 0.1)]
    assert np.ptp(err) < 0.3, err


def old_treatment(monkeypatch):
    """!
    @brief Make fvm.solve_steady build its network with the earlier cover-weighted links and the film on the node.
    @param monkeypatch pytest fixture.
    @return None.
    """
    monkeypatch.setattr(fvm, "Network", functools.partial(fvm.Network, cut_cells=False))


def test_the_old_treatment_has_the_sliver_jump_and_the_new_one_does_not(monkeypatch):
    new = {c: fvm.solve_steady(study.sliver_board(c, 200.0), cell_mm=1.0).t_max for c in (0.01, 0.02)}
    old_treatment(monkeypatch)
    old = {c: fvm.solve_steady(study.sliver_board(c, 200.0), cell_mm=1.0).t_max for c in (0.01, 0.02)}
    assert old[0.02] - old[0.01] > 3.0
    assert abs(new[0.02] - new[0.01]) < 0.3


def test_the_two_sheet_solver_agrees_with_the_program_on_a_rectangle():
    # The independent solver (its own assembly, film in series with half a cell) and the program's FVM on a 30 mm rectangle: 0.03 to 0.11 K at 1 to 0.25 mm
    p_args = (30, 30)
    for hs in (10.0, 200.0):
        for cell, bound in ((1.0, 0.15), (0.5, 0.15), (0.25, 0.15)):
            p = Problem.new(*p_args, 2, h_side=hs).add_full_copper()
            p.add_heater(1, 2.0, rect=(10.0, 13.5, 13.0, 16.5), name="U")
            mine = fvm.solve_steady(p, cell_mm=cell).t_max
            ref = ind.solve(30e-3, 30e-3, cell * 1e-3, hs, (10e-3, 13.5e-3, 13e-3, 16.5e-3))[0] + 25.0
            assert abs(mine - ref) < bound, (hs, cell, mine, ref)


FRAME_POS = [("turn 0", dict(angle=0.0)), ("turn 15", dict(angle=15.0)), ("turn 30", dict(angle=30.0)), ("turn 45", dict(angle=45.0)),
             ("shift 3/8", dict(sx=0.375, sy=0.375)), ("turn 20 shift", dict(angle=20.0, sx=0.2, sy=0.6))]


@pytest.fixture(scope="module")
def frame_refs():
    """!
    @brief Frame references of the positions, per (h_side): computed once per module.
    @return dict.
    """
    return {}


@pytest.mark.parametrize("h_side", [10.0, 200.0, 2000.0])
def test_spread_over_the_position_of_the_outline_against_the_frame_reference(h_side, frame_refs, monkeypatch):
    # The square, the part 3.5 mm off centre, 1 mm: the spread of the error over the positions is at most 0.15 K for h_side 10 to 2000 (the earlier links: 0.06, 1.2, 3.0 K)
    refs = frame_refs.setdefault(h_side, {})
    new = np.array(list(study.errors("square", 3.5, h_side, 1.0, FRAME_POS, refs).values()))
    assert np.ptp(new) <= 0.15, new
    old_treatment(monkeypatch)
    old = np.array(list(study.errors("square", 3.5, h_side, 1.0, FRAME_POS, refs).values()))
    if h_side >= 200.0:
        assert np.ptp(old) > 3.0 * np.ptp(new)               # the gain at a cooled edge
    assert np.ptp(new) <= np.ptp(old) + 0.02                 # and never worse at the default coefficient


def test_the_strip_spread_at_half_a_millimetre():
    refs = {}
    e = np.array(list(study.errors("strip", 0.0, 200.0, 0.5, FRAME_POS, refs).values()))
    assert np.ptp(e) <= 0.15


@pytest.mark.parametrize("angle", [0.0, 11.0, 22.5, 33.0, 45.0])
def test_rotated_square_peak_is_nearly_independent_of_the_angle(angle):
    # The same square turned: the peak moves by at most 0.2 K over five angles at 200 W/m2K, 1 mm (the earlier treatment: more than 1 K)
    peaks = [fvm.solve_steady(turned_square(a), cell_mm=1.0).t_max for a in (0.0, 11.0, 22.5, 33.0, 45.0)]
    assert max(peaks) - min(peaks) < 0.25


def mirror(poly, width):
    """!
    @brief The polygon mirrored in x about the middle of the box.
    @param poly Polygon (n, 2) in mm.
    @param width Box width in mm.
    @return list of points.
    """
    return [[width - x, y] for x, y in np.asarray(poly)]


@pytest.mark.parametrize("name,pts,w,h", [("L", [[0, 0], [20, 0], [20, 8], [9, 8], [9, 20], [0, 20]], 20.0, 20.0),
                                           ("T", [[0, 12], [10.3, 12], [10.3, 0], [19.7, 0], [19.7, 12], [30, 12], [30, 24], [0, 24]], 30.0, 24.0)])
def test_a_shape_and_its_mirror_image_give_the_same_peak(name, pts, w, h):
    # Any sign mistake in the distance or the aperture at a re-entrant corner breaks the mirror symmetry
    def run(points, part):
        p = Problem.new(w, h, 2, h_side=200.0).add_full_copper()
        p.add_heater(1, 2.0, rect=part, name="U")
        p.set_outline(points)
        return fvm.solve_steady(p, cell_mm=1.0).t_max, abs(fvm.solve_steady(p, cell_mm=1.0).balance_error)
    part = (3.0, 3.0, 6.0, 6.0)
    mpart = (w - 6.0, 3.0, w - 3.0, 6.0)
    a, ea = run(pts, part)
    b, eb = run(mirror(pts, w), mpart)
    assert a == pytest.approx(b, abs=1e-6)
    assert ea < 1e-9 and eb < 1e-9


def test_disc_energy_balance_and_peak_converges():
    th = np.linspace(0, 2 * np.pi, 128, endpoint=False)
    ring = np.column_stack([16 + 10 * np.cos(th), 16 + 10 * np.sin(th)])
    p = Problem.new(32, 32, 2, h_side=200.0).add_full_copper()
    p.add_heater(1, 2.0, polygon=[[16 + 1.5 * math.cos(a), 16 + 1.5 * math.sin(a)] for a in th[::8]], name="U")
    p.set_outline(ring)
    peaks = []
    for cell in (1.0, 0.5, 0.25):
        r = fvm.solve_steady(p, cell_mm=cell)
        assert abs(r.balance_error) < 1e-9
        peaks.append(r.t_max)
    assert abs(peaks[2] - peaks[1]) < abs(peaks[1] - peaks[0])


@pytest.mark.parametrize("solver", ["cg", "sor"])
def test_cg_and_sor_agree_with_the_direct_solver(solver):
    # Turned square with vias and a copper pattern (laminate nodes in the cut cells): the same links in the matrix and in the SOR
    p = bd.edge_board(angle=17.0, h_side=200.0, pc=0.5, box=32.0, vias=True, pattern=True)
    net = fvm.Network(p, 32, 32)
    ref, _ = net.solve_steady("direct")
    if solver == "cg":
        theta, _ = net.solve_steady("cg", rtol=1e-12)
        assert abs(theta - ref).max() < 1e-6
    else:
        theta, res, info = net.solve_sor(tol=1e-10)
        assert info["converged"]
        assert abs(theta - ref).max() < 1e-4


def test_sor_on_a_plain_turned_square():
    p = turned_square(17.0)
    net = fvm.Network(p, 32, 32)
    ref, _ = net.solve_steady("direct")
    theta, res, info = net.solve_sor(tol=1e-10)
    assert info["converged"] and abs(theta - ref).max() < 1e-4
    th2, _ = net.solve_steady("cg", rtol=1e-12)
    assert abs(th2 - ref).max() < 1e-6


def test_the_film_floor_is_kept_and_the_matrix_stays_positive_at_the_limit_coefficient():
    # h_side 1e5 W/m2K (the limit of Board.validate): no film factor below 0.25, positive diagonal, finite solution
    p = turned_square(20.0, h_side=1e5)
    net = fvm.Network(p, 32, 32)
    old = fvm.Network(p, 32, 32, cut_cells=False)
    ratio = np.where(old.g_side > 0, net.g_side / np.where(old.g_side > 0, old.g_side, 1.0), 1.0)
    assert ratio.max() <= 1.0 / fvm.EDGE_FILM_FLOOR + 1e-9
    assert ratio.min() > 0.0
    assert (net.K.diagonal() > 0).all()
    assert np.isfinite(fvm.solve_steady(p, cell_mm=1.0).t_max)


def test_copper_held_off_the_edge_at_a_stiff_edge_the_floor_binds_and_its_value_hardly_matters():
    # Bare-laminate nodes in the cut cells have a small sheet, so the factor 1 - h_side |d| / k_lam reaches the floor from about 1000 W/m2K at 1 mm. At 2000 W/m2K
    # (80 nodes at the floor) the peak changes by 0.06 K between the floor 0.25 and 0.05, and by 0.15 K between 0.25 and 0.5 (0.2 % of the 71 K rise)
    p = study.recessed_board(2000.0)
    assert study.count_at_floor(p, 1.0) > 40
    keep = fvm.EDGE_FILM_FLOOR
    try:
        t = {}
        for fl in (0.5, 0.25, 0.1, 0.05):
            fvm.EDGE_FILM_FLOOR = fl
            t[fl] = fvm.solve_steady(study.recessed_board(2000.0), cell_mm=1.0).t_max
    finally:
        fvm.EDGE_FILM_FLOOR = keep
    assert abs(t[0.25] - t[0.05]) < 0.15
    assert abs(t[0.25] - t[0.5]) < 0.3
    assert abs(t[0.1] - t[0.05]) < 0.05


def test_vias_in_a_cut_cell_near_a_turned_edge_run_and_balance():
    # The via footprint cells keep the cover-scaled sheet (viawell), the links to the sliver cells carry the aperture: the system is solved and conserves the heat
    p = bd.edge_board(angle=30.0, h_side=200.0, pc=0.5, box=32.0, vias=True)
    r = fvm.solve_steady(p, cell_mm=1.0)
    assert abs(r.balance_error) < 1e-9
    refs = {}
    e = np.array(list(study.errors("square", 0.0, 200.0, 1.0, FRAME_POS[:4], refs).values()))
    assert np.isfinite(e).all()


def test_a_metal_block_on_a_turned_board_keeps_the_block_links_and_balances():
    p = turned_square(25.0)
    p.add_heatsink(2, 15.0, rect=(12.0, 12.0, 20.0, 20.0), thickness_mm=3.0, k=205.0, name="Al")
    r = fvm.solve_steady(p, cell_mm=1.0)
    assert abs(r.balance_error) < 1e-9
    net = fvm.Network(p, 32, 32)
    assert net.block_info
    gx, gy = net._lateral_links()
    for info in net.block_info:
        ref = net._harmonic(net.S[info["layer"], :, :-1], net.S[info["layer"], :, 1:]) * net.dy / net.dx
        assert np.array_equal(gx[info["layer"]], ref)             # the block layer keeps the cover-scaled links
    # and the copper layers have the aperture: some link differs from the cover-scaled one
    ref0 = net._harmonic(net.S[0, :, :-1], net.S[0, :, 1:]) * net.dy / net.dx
    assert not np.array_equal(gx[0], ref0)


def test_imported_copper_on_a_board_with_an_outline_keeps_the_earlier_treatment_and_says_so():
    n = 40
    stripes = np.zeros((n, n), np.uint8)
    stripes[::6] = 1
    full = np.ones((n, n), np.uint8)
    p = Problem.new(10, 10, 2, h_side=200.0)
    p.add_heater(1, 1.0, rect=(4, 4, 6, 6), name="U")
    p.set_outline([[0.4, 0.2], [9.8, 0.6], [9.6, 9.7], [0.3, 9.5]])
    p.imported = copper.imported_from_rasters([stripes, full], 0.25, "faces")
    net = fvm.Network(p, 20, 20)
    assert net.aperture is None and net.cut_cells_note
    assert net.cut_cells_note in copper.model_warnings(p, "fvm")
    old = fvm.Network(p, 20, 20, cut_cells=False)
    assert (net.K != old.K).nnz == 0                              # one consistent treatment: exactly the earlier network
    assert abs(fvm.solve_steady(p, cell_mm=0.5).balance_error) < 1e-9
    # A rectangle with imported copper has no cut cell: no note; and the other models have none
    q = Problem.new(10, 10, 2, h_side=200.0)
    q.add_heater(1, 1.0, rect=(4, 4, 6, 6), name="U")
    q.imported = copper.imported_from_rasters([stripes, full], 0.25, "faces")
    assert fvm.Network(q, 20, 20).cut_cells_note is None
    assert copper.CUT_CELLS_IMPORTED_NOTE not in copper.model_warnings(q, "fvm")
    assert copper.CUT_CELLS_IMPORTED_NOTE not in copper.model_warnings(p, "fdm")


def test_the_lumped_model_builds_its_network_without_the_series_term(monkeypatch):
    # The Lumped never sees the links: its networks are built with cut_cells=False, so its numbers do not move with this change
    from pcbthermal import SolverOptions, lumped, simulate
    seen = []
    real = lumped.Network

    def spy(*a, **k):
        seen.append(k.get("cut_cells", True))
        return real(*a, **k)

    monkeypatch.setattr(lumped, "Network", spy)
    simulate(turned_square(20.0), SolverOptions(models=("lumped",), cell_mm=1.0))
    assert seen and not any(seen)


@pytest.mark.parametrize("h_side", [10.0, 200.0, 2000.0, 1e4, 1e5])
def test_a_constant_temperature_field_is_reproduced_to_round_off(h_side):
    # The series term changes the conductance AND the ambient term together (g_amb), so a board at rest in a warm ambient stays at that temperature, and the rows of K sum to the
    # ambient conductances (the data side scales with the same factor as the conductance; a right-hand side with a floored denominator would not)
    p = turned_square(20.0, h_side=h_side, pattern=True)
    p.board.ambient = 63.0
    p.heaters.clear()
    net = fvm.Network(p, 32, 32)
    rows = np.asarray(net.K.sum(axis=1)).ravel()
    assert rows == pytest.approx(net.g_amb.ravel(), rel=1e-9, abs=1e-9 * net.g_amb.max())
    r = fvm.solve_steady(p, cell_mm=1.0)
    assert r.t_max == pytest.approx(63.0, abs=1e-9)


def test_a_dropped_sliver_keeps_the_heat_balance():
    # A cell under the minimum cover is off the board (the program's rule); the face apertures next to it are not used (its sheet is zero), its edge length goes to the nearest board cell,
    # and the node of a sliver above the minimum stays a node, joined by its open face
    p = study.sliver_board(0.0099, 200.0)                            # (cover 0.0099: dropped)
    net = fvm.Network(p, 30, 30)
    assert not net.active[:, 5].any()
    assert abs(fvm.solve_steady(p, cell_mm=1.0).balance_error) < 1e-9
    q = study.sliver_board(0.02, 200.0)
    netq = fvm.Network(q, 30, 30)
    col = netq.active[:, 5]
    assert col.sum() == 20 and (netq.cover[col, 5] == pytest.approx(0.02, abs=1e-9))
    assert (netq.aperture[0][col, 5] > 0.99).all()                    # the face to the neighbour is open over its whole length
