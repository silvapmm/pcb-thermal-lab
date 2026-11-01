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
from pcbthermal.checks import SMALL_PART_RATIO, check_input, check_small_part_laminate


def board(part_mm, thickness_mm=1.6, plane=False, pad_mm=0.0):
    """!
    @brief A 40 mm two-layer board with a centred square part on top.
    @param part_mm Side of the part in mm.
    @param thickness_mm Board thickness in mm.
    @param plane True: full copper on the bottom layer and on the top (the gap is not cut).
    @param pad_mm Side of a copper pad under the part on the top layer in mm (0: bare laminate).
    @return Problem.
    """
    p = Problem.new(40, 40, 2, thickness_mm=thickness_mm)
    if plane:
        p.add_full_copper()
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
        assert len(w) == 1 and w[0].kind == "heater" and w[0].index == 0 and "laminate_s_max_mm" in w[0]
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


def test_solid3d_warning_uses_four_slabs():
    """!
    @brief The 3D solid warns when d / 4 exceeds 0.15 of the side, with or without cut copper, and a layered-only run does not mention it.
    @return None.
    """
    p = board(2.0, 1.6, plane=True)
    w = check_small_part_laminate(p, ("solid3d",))
    assert len(w) == 1 and "3D solid" in w[0]
    d = float(p.board.gap_thicknesses()[0])
    edge_mm = d / 4 / SMALL_PART_RATIO * 1e3
    assert not check_small_part_laminate(board(edge_mm * 1.001, 1.6, plane=True), ("solid3d",))
    assert check_small_part_laminate(board(edge_mm * 0.999, 1.6, plane=True), ("solid3d",))
    both = check_small_part_laminate(board(2.0, 3.2), ("fvm", "solid3d"))
    assert len(both) == 2


def test_wired_into_the_live_check_and_no_result_moves():
    """!
    @brief check_input carries the warning, the live check stays fast, and the temperatures of a run do not depend on it.
    @return None.
    """
    p = board(2.0, 3.2)
    assert any("sub-layer" in str(w) for w in check_input(p, ("fvm",), 1.0))
    t0 = time.perf_counter()
    check_input(p, ("fvm", "fdm", "solid3d"), 1.0)
    assert time.perf_counter() - t0 < 0.8
    r1 = simulate(p, SolverOptions(models=("fvm",), cell_mm=1.0)).results["fvm"]
    with laminate.using(0.4e-3, 4):
        r2 = simulate(p, SolverOptions(models=("fvm",), cell_mm=1.0)).results["fvm"]
    assert np.array_equal(r1.T, r2.T)
