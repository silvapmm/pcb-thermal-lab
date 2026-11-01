#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_via_off_outline.py
@brief A via whose drill disc has no board under it (centre in the cut-away part of an outline, or outside the box) conducts nothing in any model, and
       the input check says so; a via that is only partly on the board keeps its footprint restricted to the board (and warns when more than half is off).
       Regression of the point-via footprint, which moved such a via onto the nearest board cell at the full barrel conductance (2.7 K on the T preset of the
       example board, where the via is worth nothing).
"""

import copy

import numpy as np
import pytest

from pcbthermal import Problem, api, checks, fdm, fvm, solid3d
from pcbthermal.examples import example_board
from pcbthermal.geometry import disc_board_share

A = 10.0                                         # The stem of the small T starts here (mm), on a grid line of a 1 mm cell


def small_t(vias):
    """!
    @brief A small T board (30 x 24 mm, two copper planes, 2 W part on the top bar) with the given vias.
    @param vias List of (x_mm, y_mm, diameter_mm).
    @return Problem.
    """
    b = 30.0 - A
    p = Problem.new(30.0, 24.0, 2, h_side=10.0).add_full_copper()
    p.add_heater(1, 2.0, rect=(11, 14, 15, 18), name="U")
    p.set_outline([[0, 12], [A, 12], [A, 0], [b, 0], [b, 12], [30, 12], [30, 24], [0, 24]])
    for x, y, d in vias:
        p.add_via(x, y, d)
    return p


ON = [(15.0, 6.0, 0.6), (15.0, 14.0, 0.6)]
OFF = (3.0, 6.0, 0.6)                            # In the cut-away corner, far from the stem
HALF = (A, 6.0, 0.6)                             # Centre on the edge of the stem: half of the disc on the board
BAR = [(13.0, 16.0, 0.6), (13.0, 14.5, 0.6)]    # Vias under the part: they matter


@pytest.mark.parametrize("model", [fvm, fdm, solid3d])
def test_via_with_no_board_under_it_changes_nothing(model):
    # The field of the board with the via off the outline equals that of the board without it, to the last bit
    with_off = model.solve_steady(small_t(BAR + [OFF]), cell_mm=1.0)
    without = model.solve_steady(small_t(BAR), cell_mm=1.0)
    assert with_off.t_max == without.t_max
    assert np.array_equal(with_off.T, without.T)
    # ... and the vias that are on the board do matter, so the test is not vacuous
    bare = model.solve_steady(small_t([]), cell_mm=1.0)
    assert bare.t_max - without.t_max > 0.5


@pytest.mark.parametrize("name", ["lumped", "analytic"])
def test_off_outline_via_changes_nothing_in_the_reduced_models(name):
    # The Lumped and Analytic models run on the rectangle of the same area; a via off the outline must be dropped before the positions are scaled
    o = api.SolverOptions(cell_mm=1.0, models=(name,))
    a = api.simulate(small_t(BAR + [OFF]), o).results[name]
    b = api.simulate(small_t(BAR), o).results[name]
    assert a.t_max == pytest.approx(b.t_max, abs=1e-9)
    # a via that is on the board is still counted
    assert api.simulate(small_t([]), o).results[name].t_max > b.t_max + 0.3


@pytest.mark.parametrize("name", ["lumped", "analytic", "fvm", "fdm", "solid3d"])
def test_via_outside_the_box_changes_nothing(name):
    # A rectangle board, a via outside the box: ignored by every model (the live check already said so)
    def board(extra):
        p = Problem.new(30.0, 24.0, 2, h_side=10.0).add_full_copper()
        p.add_heater(1, 2.0, rect=(11, 14, 15, 18), name="U")
        for x, y, d in BAR + extra:
            p.add_via(x, y, d)
        return p
    o = api.SolverOptions(cell_mm=1.0, models=(name,))
    a = api.simulate(board([(40.0, 6.0, 0.6)]), o).results[name]
    b = api.simulate(board([]), o).results[name]
    assert a.t_max == pytest.approx(b.t_max, abs=1e-9)


@pytest.mark.parametrize("model", [fvm, fdm, solid3d])
def test_via_half_on_the_board_still_works(model):
    # The disc is half on the stem: its footprint is restricted to the board (designed behaviour), so it conducts, but less than a whole via
    n_with = model.solve_steady(small_t(BAR + [HALF]), cell_mm=1.0).t_max
    n_without = model.solve_steady(small_t(BAR), cell_mm=1.0).t_max
    assert n_with < n_without                    # it removes some heat


def test_shares_and_warnings():
    p = small_t(ON + [OFF, HALF, (10.2, 3.0, 2.0), (A + 0.9, 3.0, 2.0)])       # the last two: 1.0 mm radius at 0.2 mm out of / 0.9 mm into the stem
    shares = p.via_board_shares()
    assert shares[0] == 1.0 and shares[1] == 1.0
    assert shares[2] == 0.0
    assert 0.3 < shares[3] < 0.7
    assert shares[5] > 0.5                       # centre well inside
    assert shares[4] > 0.5                       # centre 0.2 mm inside the stem edge: most of the disc is on the board
    warn = [w for w in checks.check_problem(p) if getattr(w, "kind", None) == "via"]
    texts = {w.index: str(w) for w in warn}
    assert "outside the board outline" in texts[2]
    assert 3 not in texts or "more than half" not in texts[3]      # exactly half on the board: no warning (share is about 0.5)
    # a via with 0.25 of its disc on the board warns that more than half is off
    q = small_t([(A - 0.7, 6.0, 2.0)])           # centre 0.7 mm outside the stem, radius 1 mm
    w = [w for w in checks.check_problem(q) if getattr(w, "kind", None) == "via"]
    assert w and "more than half" in str(w[0])
    # no warning for vias on the board
    assert not [w for w in checks.check_problem(small_t(ON)) if getattr(w, "kind", None) == "via"]


def test_disc_board_share_basics():
    assert disc_board_share(0.5, 0.5, 0.1, 1.0, 1.0) == 1.0
    assert disc_board_share(2.0, 0.5, 0.1, 1.0, 1.0) == 0.0
    assert 0.4 < disc_board_share(1.0, 0.5, 0.1, 1.0, 1.0) < 0.6          # centre on the edge
    assert disc_board_share(0.5, 0.5, 0.0, 1.0, 1.0) == 1.0               # a point


def test_energy_balance_with_an_off_board_via():
    r = fvm.solve_steady(small_t(BAR + [OFF, HALF]), cell_mm=1.0)
    assert sum(r.power_out.values()) == pytest.approx(r.power_in, rel=1e-6)


def test_example_board_without_outline_is_unchanged_by_the_drop():
    # Every via of the example board is on the board: the problem is returned as it is, nothing is copied
    p = example_board()
    assert p.drop_off_board_vias() is p
    q = copy.deepcopy(p)
    q.add_via(500.0, 500.0, 0.3)                 # far outside the box
    assert len(q.drop_off_board_vias().vias) == len(p.vias)


def mid_cell_t(vias):
    """!
    @brief The small T with the edge of its stem in the middle of a 1 mm cell (x = 10.5 mm), so the cells along the stem are cut cells.
    @param vias List of (x_mm, y_mm, diameter_mm).
    @return Problem.
    """
    p = Problem.new(30.0, 24.0, 2, h_side=10.0).add_full_copper()
    p.add_heater(1, 2.0, rect=(11, 14, 15, 18), name="U")
    p.set_outline([[0, 12], [10.5, 12], [10.5, 0], [19.5, 0], [19.5, 12], [30, 12], [30, 24], [0, 24]])
    for x, y, d in vias:
        p.add_via(x, y, d)
    return p


@pytest.mark.parametrize("name", ["fvm", "fdm", "solid3d", "lumped", "analytic"])
def test_via_off_the_outline_in_a_cut_cell_is_ignored_by_every_model(name):
    # The disc (10.1 to 10.4 mm) is off the stem (10.5 mm) but inside a cut cell (10 to 11 mm, half board): the grid models must follow the same
    # geometric rule as the warning and the Lumped and Analytic runs (a cover test alone kept it: -0.15 K in the FVM, -0.13 K in the 3D solid)
    off = (10.25, 11.0, 0.3)
    p = mid_cell_t(BAR + [off])
    assert p.via_board_shares()[-1] == 0.0
    o = api.SolverOptions(cell_mm=1.0, models=(name,))
    a = api.simulate(p, o).results[name]
    b = api.simulate(mid_cell_t(BAR), o).results[name]
    assert a.t_max == pytest.approx(b.t_max, abs=1e-9)


def test_solid3d_keeps_a_via_whose_centre_is_just_off_the_box():
    # A via whose centre is 0.1 mm beyond the right edge of a rectangle has a quarter of its disc on the board: the FVM and FDM keep it, and so must the
    # 3D solid (its old test on the centre dropped it, and a via with its centre exactly on the right edge too)
    def board(extra):
        p = Problem.new(30.0, 24.0, 2, h_side=10.0).add_full_copper()
        p.add_heater(1, 2.0, rect=(11, 14, 15, 18), name="U")
        for x, y, d in BAR + extra:
            p.add_via(x, y, d)
        return p
    base = solid3d.solve_steady(board([]), cell_mm=1.0).t_max
    for x in (30.1, 30.0):
        assert solid3d.solve_steady(board([(x, 20.0, 0.6)]), cell_mm=1.0).t_max < base - 1e-3


def test_off_board_via_gets_no_edge_warning():
    # A via that is ignored does not also get the warning that its effect near the edge is too large
    p = small_t(BAR + [OFF])
    w = [str(x) for x in checks.check_via_limits(p, ("fvm",), cell_mm=1.0) if getattr(x, "index", None) == len(p.vias) - 1]
    assert not w
    q = Problem.new(30.0, 24.0, 2).add_full_copper()
    q.add_via(40.0, 6.0, 0.6)
    assert not [x for x in checks.check_via_limits(q, ("fvm",), cell_mm=1.0) if getattr(x, "index", None) == 0]


@pytest.mark.parametrize("name", ["lumped", "analytic"])
def test_off_board_via_changes_nothing_in_the_reduced_transients(name):
    # The step responses (power profiles) and the Analytic animation must drop a via outside the box like the steady run (the Lumped read it through its
    # via constriction: 0.28 K/W on the response of the small board)
    from pcbthermal import analytic, lumped
    def board(extra):
        p = Problem.new(30.0, 24.0, 2, h_side=10.0).add_full_copper()
        p.add_heater(1, 2.0, rect=(11, 14, 15, 18), name="U")
        for x, y, d in BAR + extra:
            p.add_via(x, y, d)
        return p
    mod = lumped if name == "lumped" else analytic
    ra = mod.step_responses(board([(40.0, 6.0, 0.6)]), cell_mm=1.0)
    rb = mod.step_responses(board([]), cell_mm=1.0)
    assert np.array_equal(np.asarray(ra[2]), np.asarray(rb[2]))


def test_discs_board_share_matches_the_single_disc_sample():
    # The vectorised share (only the discs near an edge are sampled) equals the plain sample of every disc, on a box, a T and a polygon circle
    from pcbthermal.geometry import discs_board_share, points_in_polygon
    import math
    rng = np.random.default_rng(3)
    n = 400
    x, y = rng.uniform(-2e-3, 32e-3, n), rng.uniform(-2e-3, 26e-3, n)
    r = rng.choice([0.0, 0.1e-3, 0.3e-3, 1.5e-3], n)
    x[:50], y[:50] = np.round(x[:50] * 1e3) / 1e3, np.round(y[:50] * 1e3) / 1e3        # centres on vertices and edges
    t = np.array([[0, 12], [10, 12], [10, 0], [20, 0], [20, 12], [30, 12], [30, 24], [0, 24]]) * 1e-3
    circ = np.array([[15e-3 + 12e-3 * math.cos(a), 12e-3 + 12e-3 * math.sin(a)] for a in np.linspace(0, 2 * math.pi, 65)[:-1]])
    rad = np.sqrt((np.arange(6) + 0.5) / 6)
    ang = 2 * math.pi * (np.arange(24) + 0.5) / 24
    ux = np.concatenate([[0.0], (rad[:, None] * np.cos(ang)).ravel()])
    uy = np.concatenate([[0.0], (rad[:, None] * np.sin(ang)).ravel()])
    for outline in (None, t, circ):
        plain = []
        for xi, yi, ri in zip(x, y, r):
            px, py = xi + ri * ux, yi + ri * uy
            ins = ((px >= 0) & (px <= 30e-3) & (py >= 0) & (py <= 24e-3)) if outline is None else points_in_polygon(px, py, outline)
            plain.append(ins.mean())
        assert np.array_equal(discs_board_share(x, y, r, 30e-3, 24e-3, outline), np.array(plain))
