#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_via_partial_copper_warning.py
@brief Tests of the live warning for a via whose footprint covers a copper layer with copper over only part of it (checks.partial_copper_vias,
       checks.check_via_partial_copper; research/via-partial-copper, INTEGRATION.md proposal A).

@details The warning is text only: no temperature changes, so these tests look at which problems warn, the boundary of the rule, the aggregation and that nothing
         of the problem is touched. The boards are the documented 30 x 30 mm copper-edge board of test_maximum_principle.py and the small boards of the study.
"""

import copy
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "regression"))

from pcbthermal import checks                                   # noqa: E402
from pcbthermal.model import Problem, problem_to_dict           # noqa: E402
from test_maximum_principle import copper_edge_board            # noqa: E402
import regress_boards as rb                                     # noqa: E402


def _antipad_array(side=0.8, n=3, pitch=1.2):
    """!
    @brief A four-layer 12 x 12 mm board with a thermal-via array whose layer 3 has a square clearance around every via (the stand-in of the study).
    @param side Side of the clearance in mm.
    @param n Vias per side.
    @param pitch Via pitch in mm.
    @return Problem.
    """
    wb, c = 12.0, 6.0
    p = Problem.new(wb, wb, 4, 1.6, 35.0, h_top=50.0, h_bottom=50.0, h_side=None)
    p.add_zone(1, rect=(c - 3, c - 3, c + 3, c + 3))
    p.add_zone(2, rect=(0, 0, wb, wb))
    p.add_zone(4, rect=(0, 0, wb, wb))
    pts = [(c + (i - (n - 1) / 2) * pitch, c + (j - (n - 1) / 2) * pitch) for i in range(n) for j in range(n)]
    a = side / 2
    ys = sorted({y for _, y in pts})
    edges = [0.0]
    for y in ys:
        edges += [y - a, y + a]
    edges.append(wb)
    for k in range(0, len(edges), 2):
        if edges[k + 1] - edges[k] > 1e-9:
            p.add_zone(3, rect=(0, edges[k], wb, edges[k + 1]))                       # a band without a hole
    for y in ys:
        xs = sorted({x for x, yy in pts if abs(yy - y) < 1e-9})
        xe = [0.0]
        for x in xs:
            xe += [x - a, x + a]
        xe.append(wb)
        for k in range(0, len(xe), 2):
            if xe[k + 1] - xe[k] > 1e-9:
                p.add_zone(3, rect=(xe[k], y - a, xe[k + 1], y + a))                  # the copper between the holes of this row
    p.add_heater(1, 1.0, rect=(c - 2, c - 2, c + 2, c + 2), name="Q")
    for x, y in pts:
        p.add_via(x, y, 0.3)
    return p


def _track(width=0.4, length=2.0):
    """!
    @brief A 10 x 10 mm two-layer board: a 2 x 2 mm pad, a thin track that ends at the centre of a 0.3 mm via, a full bottom plane.
    @param width Track width in mm.
    @param length Track length in mm from the pad to the via centre.
    @return Problem.
    """
    p = Problem.new(10, 10, 2, 1.6, 35.0, h_top=50.0, h_bottom=50.0, h_side=None)
    p.add_zone(2, rect=(0, 0, 10, 10))
    p.add_zone(1, rect=(5 - length - 2, 4, 5 - length, 6))
    p.add_zone(1, rect=(5 - length, 5 - width / 2, 5, 5 + width / 2))
    p.add_heater(1, 0.5, rect=(5 - length - 2, 4, 5 - length, 6), name="Q")
    p.add_via(5, 5, 0.3)
    return p


def _two_planes(ratio, n_vias=1):
    """!
    @brief A 10 x 10 mm two-layer board with a full top plane and a bottom plane whose right half is a hatched zone of the fill that gives a sheet conductance
           `ratio` times that of the full copper, with the vias on the line where the two meet.
    @param ratio Wanted ratio of the smallest to the largest sheet conductance per unit of board in the footprint.
    @param n_vias Number of vias, spread along the junction.
    @return Problem.
    """
    p = Problem.new(10, 10, 2, 1.6, 35.0, h_top=50.0, h_bottom=50.0, h_side=None)
    b = p.board
    t = float(b.copper_thickness[1])
    k_lam = float(b.layer_laminate()[0][1])
    slab = float(b.slab_thicknesses()[1])
    kc = b.materials.k_copper
    full = kc * t + k_lam * (slab - t)
    f = (ratio * full - k_lam * slab) / (t * (kc - k_lam))                           # linear in the fill: rel(f) = k_lam slab + f t (kc - k_lam)
    assert 0.0 < f < 1.0
    p.add_zone(1, rect=(0, 0, 10, 10))
    p.add_zone(2, rect=(0, 0, 5, 10))
    p.add_zone(2, rect=(5, 0, 10, 10), fill=f)
    p.add_heater(1, 0.5, rect=(3, 4, 4, 6), name="Q")
    for y in np.linspace(2.0, 8.0, n_vias):
        p.add_via(5.0, float(y), 0.3)
    return p


@pytest.mark.parametrize("cell", [1.0, 0.5, 0.25, 0.125])
def test_the_documented_copper_edge_board_warns_at_every_cell(cell):
    problem = copper_edge_board()
    partial, n = checks.partial_copper_vias(problem, cell)
    assert n == 1 and len(partial) == 1 and partial[0][0] == 0 and partial[0][1] == 0 and partial[0][2] < 0.1
    out = checks.check_input(problem, ("fvm",), cell)
    msgs = [w for w in out if "copper over only part" in w]
    assert len(msgs) == 1 and msgs[0].kind == "via" and msgs[0].index == 0
    assert "1 of 1 via has copper over only part of its footprint" in msgs[0]


@pytest.mark.parametrize("model", ["fvm", "fdm"])
def test_the_warning_is_for_the_footprint_models_only(model):
    problem = copper_edge_board()
    assert any("copper over only part" in w for w in checks.check_via_partial_copper(problem, (model,), 0.5))
    for other in (("lumped",), ("analytic",), ("lumped", "analytic")):
        assert checks.check_via_partial_copper(problem, other, 0.5) == []


def test_a_track_ending_at_the_via_warns():
    for cell in (0.5, 0.25):
        partial, n = checks.partial_copper_vias(_track(), cell)
        assert n == 1 and len(partial) == 1


@pytest.mark.parametrize("name", ["example_board", "profile_board", "example_cut_to_T", "plate_vias", "plate_lone_via"])
@pytest.mark.parametrize("cell", [2.0, 1.0, 0.5])
def test_the_frozen_boards_with_vias_raise_no_false_alarm(name, cell):
    problem = rb.build(name)
    assert problem.vias
    partial, n = checks.partial_copper_vias(problem, cell)
    assert n > 0 and partial == []
    assert checks.check_via_partial_copper(problem, ("fvm", "fdm"), cell) == []


@pytest.mark.parametrize("cell", [1.0, 0.5, 0.25])
def test_antipads_are_silent(cell):
    for side in (0.8, 1.0):
        problem = _antipad_array(side)
        partial, n = checks.partial_copper_vias(problem, cell)
        assert n == 9 and partial == [], (side, cell)


def test_the_rule_changes_at_half_the_sheet_conductance():
    # Just above the ratio of 0.5 (0.55) silent, just below (0.45) it fires; the ratio the check reports is the one the board was built for
    quiet = checks.partial_copper_vias(_two_planes(0.55), 0.5)[0]
    loud = checks.partial_copper_vias(_two_planes(0.45), 0.5)[0]
    assert quiet == []
    assert len(loud) == 1 and loud[0][1] == 1 and loud[0][2] == pytest.approx(0.45, abs=0.01)


def test_only_the_cells_with_a_share_of_the_footprint_weight_count():
    # A copper edge far from the via, beyond the footprint, changes nothing: the via stays silent
    p = Problem.new(10, 10, 2, 1.6, 35.0, h_top=50.0, h_bottom=50.0, h_side=None)
    p.add_zone(1, rect=(0, 0, 10, 10))
    p.add_zone(2, rect=(0, 0, 6.0, 10))
    p.add_via(2.0, 5.0, 0.3)
    assert checks.partial_copper_vias(p, 0.25) == ([], 1)


def test_many_vias_give_one_aggregated_message_with_the_count_and_the_worst_few():
    problem = _two_planes(0.2, n_vias=7)
    out = checks.check_via_partial_copper(problem, ("fvm",), 0.5)
    assert len(out) == 1
    text = str(out[0])
    assert text.startswith("7 of 7 vias have copper over only part of their footprint")
    assert "and 4 more" in text                                   # three are named, the others counted
    assert out[0].short.startswith("7 of 7 vias") and "\n" not in out[0].short


def test_the_text_says_both_directions_and_does_not_say_exaggerated():
    text = str(checks.check_via_partial_copper(copper_edge_board(), ("fvm",), 0.5)[0])
    assert "higher or lower" in text and "numerical artefact" in text and "3D solid" in text
    assert "exaggerat" not in text.lower()


def test_a_board_without_vias_or_with_one_layer_is_silent():
    assert checks.partial_copper_vias(Problem.new(10, 10, 2), 0.5) == ([], 0)
    p = Problem.new(10, 10, 1)
    p.add_via(5, 5, 0.3)
    assert checks.partial_copper_vias(p, 0.5) == ([], 0)


def test_a_via_off_the_board_is_not_counted():
    problem = copper_edge_board()
    problem.add_via(60.0, 60.0, 0.3)                              # No board under it: ignored by every model
    partial, n = checks.partial_copper_vias(problem, 0.5)
    assert n == 1 and len(partial) == 1


def test_the_check_changes_nothing_in_the_problem():
    problem = copper_edge_board()
    before = copy.deepcopy(problem_to_dict(problem))
    checks.check_input(problem, ("fvm", "fdm", "lumped", "analytic"), 0.5)
    assert problem_to_dict(problem) == before


def test_the_warning_is_in_the_live_list_of_check_input():
    out = checks.check_input(copper_edge_board(), ("fvm",), 0.5)
    assert sum("copper over only part" in w for w in out) == 1
    assert not any("copper over only part" in w for w in checks.check_input(copper_edge_board(), ("lumped",), 0.5))


def _exact_partial(problem, cell_mm):
    """!
    @brief Reference of the check: the rule applied to the footprint of every via, with no prefilter.
    @param problem The Problem.
    @param cell_mm Cell size in mm.
    @return List of via indices that fire.
    """
    from pcbthermal import copper, viawell
    b = problem.board
    nx, ny = max(int(round(b.width * 1000.0 / cell_mm)), 8), max(int(round(b.height * 1000.0 / cell_mm)), 8)
    dx, dy = b.width / nx, b.height / ny
    fill = copper.problem_fill(problem, nx, ny, dx, dy, 4)
    cover = b.cover(nx, ny, dx, dy)
    t = np.asarray(b.copper_thickness)[:, None, None]
    k_lam = b.layer_laminate()[0][:, None, None]
    rel = fill * b.materials.k_copper * t + k_lam * (b.slab_thicknesses()[:, None, None] - fill * t)
    out = []
    for k, v in enumerate(problem.vias):
        w, _, _ = viawell.footprint(v.x, v.y, v.diameter / 2.0, dx, 0.0, cover, dy, 0.0)
        if not w:
            continue
        wmax = max(w.values())
        cells = [c for c, x in w.items() if x >= 0.05 * wmax]
        vals = rel[:, [c[0] for c in cells], [c[1] for c in cells]]
        if (vals.min(axis=1) < 0.5 * vals.max(axis=1)).any():
            out.append(k)
    return out


@pytest.mark.parametrize("seed", [0, 1, 2])
@pytest.mark.parametrize("cell", [1.0, 0.5, 0.25])
def test_the_prefilter_loses_no_via_of_the_exact_rule(seed, cell):
    rng = np.random.default_rng(seed)
    p = Problem.new(14, 11, 3, 1.6, 35.0, h_side=None)
    for layer in (1, 2, 3):
        for _ in range(4):
            x0, y0 = rng.uniform(0, 10), rng.uniform(0, 7)
            p.add_zone(layer, rect=(x0, y0, x0 + rng.uniform(1, 5), y0 + rng.uniform(1, 5)), fill=float(rng.choice([1.0, 1.0, 0.4])))
    for x, y in rng.uniform([0.2, 0.2], [13.8, 10.8], (60, 2)):
        p.add_via(float(x), float(y), float(rng.choice([0.2, 0.3, 0.6])))
    want = _exact_partial(p, cell)
    got = [k for k, _, _ in checks.partial_copper_vias(p, cell)[0]]
    assert got == want and 0 < len(want) < 60
