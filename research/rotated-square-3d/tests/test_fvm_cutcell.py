#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_fvm_cutcell.py
@brief Tests of the cut-cell prototype for the layered FVM (`lib/fvm_cutcell.py`), its geometry (`lib/cutcell.py`) and its references (`lib/sheetmodes.py`, `lib/layered_disc.py`).
@details Light cases only (a few seconds, well below 1 GB). Run: .venv/bin/python -m pytest -q research/rotated-square-3d/tests/test_fvm_cutcell.py
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import cutcell            # noqa: E402
import fvm_cutcell as fc  # noqa: E402
import layered_disc       # noqa: E402
import rotsq              # noqa: E402
import sheetmodes         # noqa: E402
from pcbthermal import Problem, fvm   # noqa: E402


def _square(angle=20.0, h_side=100.0, **kw):
    """!
    @brief The 20 mm square in a 30 mm box with a 3 mm part.
    @param angle Turn in degrees.
    @param h_side Edge coefficient.
    @param kw More options of `rotsq.board`.
    @return Problem.
    """
    return rotsq.board(angle, h_side, side_mm=20.0, box_mm=30.0, part_mm=3.0, **kw)


def test_fast_geometry_equals_the_full_sampling():
    """!
    @brief The geometry sampled only at the cut cells is the one sampled everywhere.
    @return None.
    """
    for poly in (np.array(rotsq.turned_square(20.0, 27.0, (15.0, 15.0))) * 1e-3, np.array(rotsq.equal_area_polygon(9.0, (15.0, 15.0), 96)) * 1e-3):
        a = cutcell.cut_geometry(poly, 30, 30, 1e-3, 1e-3)
        b = cutcell.cut_geometry_fast(poly, 30, 30, 1e-3, 1e-3)
        for k in ("cover", "xc", "yc", "ax", "ay"):
            assert np.allclose(a[k], b[k], atol=1e-12), k


def test_half_cell_edge_has_unit_aperture_and_quarter_cell_centroid():
    """!
    @brief A straight edge half way through a column: the cut cell is half board, its centroid is a quarter cell inside, the face along the cut is whole.
    @return None.
    """
    dx = 1e-3
    poly = np.array([[0.0, 0.0], [5.5 * dx, 0.0], [5.5 * dx, 8 * dx], [0.0, 8 * dx]])
    g = cutcell.cut_geometry_fast(poly, 10, 8, dx, dx)
    assert np.allclose(g["cover"][:, 5], 0.5) and np.allclose(g["cover"][:, :5], 1.0) and np.allclose(g["cover"][:, 6:], 0.0)
    assert np.allclose(g["xc"][:, 5], 5.25 * dx)
    assert np.allclose(g["ax"][:, 4], 1.0) and np.allclose(g["ax"][:, 5], 0.0)       # the face 5|6 is outside the board
    assert np.allclose(g["ay"][:, 5], 0.5)                                         # the face along the edge carries half the width


def test_rectangle_matrix_is_the_programs():
    """!
    @brief A board without an outline gives exactly the program's matrix in every mode (no cut cell, nothing replaced).
    @return None.
    """
    p = Problem.new(20.0, 16.0, 2, h_side=10.0).add_full_copper()
    p.add_heater(1, 1.0, rect=(5, 5, 9, 9), name="U")
    k0 = fvm.Network(p, 20, 16).K
    for mode in fc.MODES:
        fc.CutCellNetwork.mode = mode
        k1 = fc.CutCellNetwork(p, 20, 16).K
        assert abs(k0 - k1).max() <= 1e-9 * abs(k0).max()


def test_outline_on_the_grid_lines_gives_the_programs_temperatures():
    """!
    @brief An outline that lies on grid lines cuts no cell: links and aperture reproduce the program (the strip variant adds the half-cell conduction and may differ).
    @return None.
    """
    p = Problem.new(30.0, 30.0, 2, h_side=100.0).add_full_copper()
    p.add_heater(1, 2.0, rect=(13, 13, 17, 17), name="U")
    p.set_outline([[5, 5], [25, 5], [25, 25], [5, 25]])
    t0 = fc.tmax(p, 1.0, "program")
    for s in ("links", "aperture"):
        assert abs(fc.tmax(p, 1.0, s) - t0) < 1e-8


def test_energy_balance_of_every_scheme_on_a_turned_square():
    """!
    @brief The heat leaving by the four paths adds up to the power for every variant (the prototype loses nothing at the cut cells).
    @return None.
    """
    p = _square(20.0, 500.0)
    for s in fc.MODES:
        r = fc.solve(p, 0.5, s)
        assert abs(sum(r.power_out.values()) - 2.0) < 1e-6, s


def test_cut_cells_remove_the_shift_dependence_at_high_edge_coefficient():
    """!
    @brief A square shifted by half a cell reads closer to the aligned one with the cut-cell links than with the program's cover scaling, at a high edge coefficient.
    @return None.
    """
    c = 0.5
    base = {s: fc.tmax(_square(0.0, 2000.0), c, s) for s in ("program", "links")}
    shifted = {s: fc.tmax(_square(0.0, 2000.0, shift_mm=(c / 2, c / 2)), c, s) for s in ("program", "links")}
    assert abs(shifted["links"] - base["links"]) < 0.5 * abs(shifted["program"] - base["program"]) + 0.02


def test_closed_form_reference_matches_the_fvm_without_cut_cells():
    """!
    @brief The cosine-series reference of an insulated rectangle and the program's FVM agree to the discretisation error, which falls as the cell squared.
    @return None.
    """
    p = Problem.new(20.0, 20.0, 2, h_side=0.0).add_full_copper()
    p.add_heater(1, 2.0, rect=(8, 8, 12, 12), name="U")
    const = sheetmodes.layer_constants(p)
    errs = []
    for cell in (1.0, 0.5):
        r = fvm.solve_steady(p, cell_mm=cell)
        c = cell / 2000.0
        ex = sheetmodes.rectangle_mean(const, (0.02, 0.02), 0, 2.0, (0.008, 0.008, 0.012, 0.012), (0.01 - c - 1e-6, 0.01 - c - 1e-6, 0.01 - c + 1e-6, 0.01 - c + 1e-6), 0, 400)
        errs.append(abs(r.t_max - p.board.ambient - ex) / ex)
    assert errs[0] < 0.01 and errs[1] < 0.3 * errs[0]


def test_series_total_power_is_conserved():
    """!
    @brief Check of the series itself: with a read rectangle equal to the whole board and a layer pair, the mean rise times the film conductance gives the power.
    @return None.
    """
    p = Problem.new(20.0, 20.0, 2, h_side=0.0).add_full_copper()
    const = sheetmodes.layer_constants(p)
    area = 0.02 * 0.02
    m_top = sheetmodes.rectangle_mean(const, (0.02, 0.02), 0, 2.0, (0.008, 0.008, 0.012, 0.012), (0.0, 0.0, 0.02, 0.02), 0, 10)
    m_bot = sheetmodes.rectangle_mean(const, (0.02, 0.02), 0, 2.0, (0.008, 0.008, 0.012, 0.012), (0.0, 0.0, 0.02, 0.02), 1, 10)
    assert abs(area * (const["h_top"] * m_top + const["h_bottom"] * m_bot) - 2.0) < 1e-9


def test_links_are_closer_to_the_axisymmetric_reference_on_a_round_board():
    """!
    @brief Round board at a high edge coefficient and 1 mm cells: the peak of the cut-cell links is nearer to the axisymmetric reduction than the program's, and the rim loss within 0.5 per cent.
    @return None.
    """
    d, a, hs, cell = 40.0, 3.0, 1000.0, 1.0
    p = rotsq.disc_board(d, a, hs)
    sol = layered_disc.solve(p, d / 2000.0, a / 1000.0, 2000)
    ref = float(np.interp(cell / 1000.0 * 0.5 * np.sqrt(2.0), sol["r"], sol["top"]))
    amb = p.board.ambient
    r0, r1 = fc.solve(p, cell, "program"), fc.solve(p, cell, "links")
    e0, e1 = abs(r0.t_max - amb - ref) / ref, abs(r1.t_max - amb - ref) / ref
    assert e1 < e0
    assert abs(r1.power_out["sides"] / sol["heat_rim"] - 1.0) < 0.005
    assert abs(sol["heat_rim"] + sol["heat_top"] + sol["heat_bottom"] - sol["power"]) < 1e-6 * sol["power"]


def test_blocks_are_refused():
    """!
    @brief A board with a metal block is not handled by the prototype and says so.
    @return None.
    """
    p = Problem.new(20.0, 20.0, 2, h_side=10.0).add_full_copper()
    p.add_heater(1, 1.0, rect=(8, 8, 12, 12), name="U")
    p.add_heatsink(1, 20.0, rect=(5, 5, 15, 15), thickness_mm=2.0, name="B")
    assert any(s.is_block() for s in p.heatsinks)
    try:
        fc.CutCellNetwork(p, 20, 20)
    except ValueError:
        return
    raise AssertionError("a metal block should be refused")


def test_transient_runs_with_the_cut_cell_network():
    """!
    @brief The implicit transient on the cut-cell network is finite, never below the ambient, and its time to 63 per cent is within 1 per cent of the program's.
    @return None.
    """
    p = _square(20.0, 100.0)
    t0 = fvm.solve_transient(p, 120.0, n_out=20, cell_mm=1.0)
    with fc.using_cutcell("links"):
        t1 = fvm.solve_transient(p, 120.0, n_out=20, cell_mm=1.0)
    assert np.isfinite(t1.frames).all() and t1.frames.min() >= p.board.ambient - 1e-9
    assert abs(t1.time_constant() / t0.time_constant() - 1.0) < 0.01


def test_exact_geometry_has_the_polygon_area_and_agrees_with_the_sampled_one():
    """!
    @brief The clipped cover sums to the polygon area to rounding, the sampled one to a few parts in 10^4, and apertures and centroids agree with the 16 x 16 sampling to its resolution.
    @return None.
    """
    import cutcell_exact
    for poly in (np.array(rotsq.turned_square(20.0, 27.0, (15.0, 15.0))) * 1e-3, np.array(rotsq.equal_area_polygon(9.0, (15.0, 15.0), 96)) * 1e-3):
        a = cutcell.cut_geometry_fast(poly, 30, 30, 1e-3, 1e-3)
        b = cutcell_exact.cut_geometry_exact(poly, 30, 30, 1e-3, 1e-3)
        area = abs(0.5 * np.sum(poly[:, 0] * np.roll(poly[:, 1], -1) - np.roll(poly[:, 0], -1) * poly[:, 1]))
        assert abs(b["cover"].sum() * 1e-6 / area - 1.0) < 1e-12
        assert abs(a["cover"].sum() * 1e-6 / area - 1.0) < 1e-3
        assert np.abs(a["cover"] - b["cover"]).max() < 0.02
        assert np.abs(a["ax"] - b["ax"]).max() < 0.07 and np.abs(a["ay"] - b["ay"]).max() < 0.07
        big = b["cover"] > 0.05      # a sliver below that is empty for one sampling and a corner for the other: no matter, the program takes it as off the board
        assert np.abs((a["xc"] - b["xc"])[big]).max() < 0.05e-3 and np.abs((a["yc"] - b["yc"])[big]).max() < 0.05e-3


def test_sor_with_cut_cell_links_equals_the_direct_solve():
    """!
    @brief The point SOR of the prototype uses the cut-cell links (the patched `solve_sor`) and converges to the direct solution of the same matrix, with vias and a copper edge inside a cut cell.
    @return None.
    """
    p = _square(20.0, 500.0)
    p.add_via(15.2, 15.3, diameter=0.3)
    with fc.using_cutcell("links"):
        net = fvm.Network(p, 30, 30)
        th_d, _ = net.solve_steady("direct")
        th_s, res, info = net.solve_sor(tol=1e-11)
    assert info["converged"] and np.abs(th_s - th_d).max() < 1e-6 * th_d.max()
    # And the SOR really saw the cut-cell links: the program's network gives another field on the same board
    th_p, _ = fvm.Network(p, 30, 30).solve_steady("direct")
    assert np.abs(th_p - th_d).max() > 1e-3


def test_cut_cell_matrix_is_symmetric_positive_definite_and_conservative_with_exact_geometry():
    """!
    @brief The matrix stays symmetric, its diagonal positive, and the heat balance closes to rounding with the exact geometry on a turned square and a disc.
    @return None.
    """
    for p in (_square(33.0, 800.0), rotsq.disc_board(20.0, 1.5, 800.0, box_mm=30.0)):
        with fc.using_cutcell("links", exact=True):
            net = fvm.Network(p, 30, 30)
            theta, _ = net.solve_steady("direct")
        K = net.K.tocsr()
        assert abs(K - K.T).max() < 1e-12 * abs(K).max()
        assert (K.diagonal() > 0).all()
        assert abs(sum(net.power_out(theta).values()) / float(net.Q.sum()) - 1.0) < 1e-10
