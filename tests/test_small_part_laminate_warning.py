#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_small_part_laminate_warning.py
@brief The warning for a small part over a thick insulating layer (layered laminate rule of the FVM and FDM, four slabs of the 3D solid): it fires at the stated ratio of the
       sub-layer to the smaller side of the part, only where the rule cuts the gap, and changes no result.
"""

import time

import numpy as np

from pcbthermal import Problem, SolverOptions, laminate, simulate
from pcbthermal.analysis import heater_stats
from pcbthermal.checks import SMALL_PART_RATIO, SMALL_PART_RATIO_PAD, check_input, check_small_part_laminate, small_part_ratios


def board(part_mm, thickness_mm=1.6, plane=False, pad_mm=0.0, top_plane=False):
    """!
    @brief A 40 mm two-layer board with a centred square part on top.
    @param part_mm Side of the part in mm.
    @param thickness_mm Board thickness in mm.
    @param plane True: full copper on the bottom layer and on the top (the gap is not cut).
    @param pad_mm Side of a copper pad under the part on the top layer in mm (0: bare laminate).
    @param top_plane True: full copper on the top layer only (the gap is cut, the heat spreads in the plane).
    @return Problem.
    """
    p = Problem.new(40, 40, 2, thickness_mm=thickness_mm)
    if plane:
        p.add_full_copper()
    elif top_plane:
        p.add_full_copper(layers=[1])
    elif pad_mm > 0:
        p.add_zone(1, rect=(20 - pad_mm / 2, 20 - pad_mm / 2, 20 + pad_mm / 2, 20 + pad_mm / 2))
    a, b = 20 - part_mm / 2, 20 + part_mm / 2
    p.add_heater(1, 1.0, rect=(a, a, b, b), name="U")
    return p


def test_threshold_and_boundary_of_the_layered_rule():
    """!
    @brief With the default rule the warning fires below the side s / 0.15 and not at or above it (exact boundary, the equal case is silent).
    @return None.
    """
    for thick in (1.6, 3.2):
        p = board(2.0, thick)
        d = float(p.board.gap_thicknesses()[0])
        s = d / laminate.n_for_gap(d)
        edge_mm = s / SMALL_PART_RATIO * 1e3
        assert edge_mm < 3.0 if thick == 1.6 else edge_mm > 5.0
        for side, expect in ((edge_mm * 0.99, True), (edge_mm, False), (edge_mm * 1.01, False)):
            w = [x for x in check_small_part_laminate(board(side, thick), ("fvm",)) if "sub-layer" in x]
            assert bool(w) == expect, (thick, side)
        w = check_small_part_laminate(board(2.0, thick), ("fdm",))
        assert len(w) == 1 and w[0].kind == "heater" and w[0].index == 0 and 'Laminate sub-gap' in w[0]
        assert w[0].short and len(w[0].short) < len(str(w[0]))


def test_options_move_the_threshold():
    """!
    @brief A smaller sub-gap rule silences a part that the default warns about; the full text names the options in force.
    @return None.
    """
    p = board(2.0, 1.6)
    assert check_small_part_laminate(p, ("fvm",))
    with laminate.using(0.2e-3, 8):
        assert not check_small_part_laminate(p, ("fvm",))                  # 0.2 mm / 2 mm = 0.1


def test_silent_where_the_gap_is_not_cut():
    """!
    @brief Copper on both layers (a plane under the part), a Lumped or Analytic run alone, and a large part are silent; a copper pad over a bare bottom layer still warns.
    @return None.
    """
    assert check_small_part_laminate(board(2.0, 3.2, plane=True), ("fvm", "fdm")) == []
    assert check_small_part_laminate(board(2.0, 3.2), ("lumped", "analytic")) == []
    assert check_small_part_laminate(board(10.0, 3.2), ("fvm", "fdm")) == []
    assert len(check_small_part_laminate(board(2.0, 3.2, pad_mm=4.0), ("fvm",))) == 1


def test_pad_limit_and_spread_of_the_copper():
    """!
    @brief Over a copper pad of the part's size the layered limit is SMALL_PART_RATIO_PAD (the review measured -5 to -7 % at 0.12 to 0.14, silent before); a pad larger than the part counts
           by its own size, and a plane on the layer of the part is silent although the gap is cut (the review measured 0.02 %).
    @return None.
    """
    d = float(board(2.0).board.gap_thicknesses()[0])
    s = d / laminate.n_for_gap(d)
    edge_mm = s / SMALL_PART_RATIO_PAD * 1e3
    for side, expect in ((edge_mm * 0.97, True), (edge_mm * 1.03, False)):
        w = check_small_part_laminate(board(side, pad_mm=side), ("fvm",), 0.25)
        assert bool(w) == expect, side
        if w:
            assert "over a copper pad" in w[0]
    assert check_small_part_laminate(board(2.7, pad_mm=2.7), ("fvm",), 0.5)          # ratio 0.14: -5 to -7 % measured, warned now
    assert not check_small_part_laminate(board(2.7), ("fvm",), 0.5)                  # bare at 0.14: -3.4 %, silent
    r_pad = small_part_ratios(board(2.0, pad_mm=2.0), ("fvm",), 0.25)[0][4]
    r_big = small_part_ratios(board(2.0, pad_mm=4.0), ("fvm",), 0.25)[0][4]
    assert r_big < 0.6 * r_pad                                                         # the larger pad spreads the heat: a smaller ratio
    assert check_small_part_laminate(board(2.0, pad_mm=16.0), ("fvm", "solid3d"), 0.5) == []
    assert check_small_part_laminate(board(2.0, top_plane=True), ("fvm", "fdm", "solid3d"), 1.0) == []


def test_solid3d_warning_uses_four_slabs():
    """!
    @brief The 3D solid warns when d / 4 exceeds 0.15 of the side on bare laminate, also where the layered rule would not cut (a 0.8 mm board), and is silent under copper planes
           (4 against 16 slabs: 0.03 %, review).
    @return None.
    """
    p = board(2.0, 1.6)
    w = check_small_part_laminate(p, ("solid3d",))
    assert len(w) == 1 and "3D solid" in w[0]
    d = float(p.board.gap_thicknesses()[0])
    edge_mm = d / 4 / SMALL_PART_RATIO * 1e3
    assert not check_small_part_laminate(board(edge_mm * 1.001, 1.6), ("solid3d",))
    assert check_small_part_laminate(board(edge_mm * 0.999, 1.6), ("solid3d",))
    assert check_small_part_laminate(board(2.0, 1.6, plane=True), ("solid3d",)) == []
    both = check_small_part_laminate(board(2.0, 3.2), ("fvm", "solid3d"))
    assert len(both) == 2


# Values of the FVM on board(2.0, 3.2) at 1 mm computed on develop (ec227ab) before this branch: the warning must not move them
FROZEN_FVM_SMALL_BARE = (439.5514011355619, 454.13473446889503)      # (t_max, mean of the part with its face term) in degC


def test_wired_into_the_live_check_and_no_result_moves():
    """!
    @brief check_input carries the warning, the live check stays fast, and the temperatures of a run are those of the program before the warning existed.
    @return None.
    """
    p = board(2.0, 3.2)
    assert any("sub-layer" in str(w) for w in check_input(p, ("fvm",), 1.0))
    t0 = time.perf_counter()
    check_input(p, ("fvm", "fdm", "solid3d"), 1.0)
    assert time.perf_counter() - t0 < 0.8
    r = simulate(p, SolverOptions(models=("fvm",), cell_mm=1.0))
    assert any("sub-layer" in w for w in r.warnings)                                 # the run reports it ...
    res = r.results["fvm"]
    t_max, t_part = FROZEN_FVM_SMALL_BARE
    assert abs(res.t_max - t_max) < 1e-8 and abs(heater_stats(res, p)[0]["t_mean"] - t_part) < 1e-8   # ... and the numbers are those of develop


def many_parts(n, size_mm=1.0):
    """!
    @brief A 200 x 150 mm bare two-layer board with n small parts on a grid.
    @param n Number of parts.
    @param size_mm Side of every part in mm.
    @return Problem.
    """
    p = Problem.new(200, 150, 2)
    for i in range(n):
        x, y = 5 + 9 * (i % 20), 5 + 9 * (i // 20)
        s = size_mm + 0.002 * i                                         # Distinct sizes: the worst (smallest) first
        p.add_heater(1, 0.1, rect=(x, y, x + s, y + s), name=f"R{i + 1}")
    return p


def test_aggregation_of_many_parts():
    """!
    @brief One, three, four and 300 parts: up to three keep one warning each, more give one message with the count, the five worst (smallest first) and the limit; the live check stays fast.
    @return None.
    """
    for n, count in ((1, 1), (3, 3), (4, 1), (300, 1)):
        w = check_small_part_laminate(many_parts(n), ("fvm",))
        assert len(w) == count, n
    w = check_small_part_laminate(many_parts(4), ("fvm",))[0]
    assert w.kind is None and "4 parts" in w and "R1 (" in w and "R5" not in w and w.short and "4 small parts" in w.short
    w = check_small_part_laminate(many_parts(300), ("fvm", "solid3d"))
    assert [x for x in w if "300 parts" in x] and len(w) == 2
    first = [x for x in w if "layered" in x or "FVM" in x][0]
    assert "R1 (" in first and "R5 (" in first and "R6 (" not in first and "0.15" in first
    t0 = time.perf_counter()
    check_small_part_laminate(many_parts(300), ("fvm", "fdm", "solid3d"), 1.0)         # (check_input also runs the pairwise overlap test of 300 parts, 1.9 s, not this check)
    assert time.perf_counter() - t0 < 0.8
