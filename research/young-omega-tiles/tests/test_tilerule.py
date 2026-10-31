#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_tilerule.py
@brief Tests of `lib/tilerule.py` (S4): the rules for the tile, the floor and the cap, the coarsening, the mode rule, the cost, that the patch is installed and removed cleanly, and that
       with the correction switched off it reproduces the program bit for bit.
@details Run from the repository root: `.venv/bin/python -m pytest -q research/young-omega-tiles/tests/test_tilerule.py`.
"""

import os
import sys

import numpy as np
import pytest

LIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib")
sys.path.insert(0, LIB)

import s4cases as sc                                                        # noqa: E402
import tilerule as tr                                                       # noqa: E402
from pcbthermal import analytic                                             # noqa: E402


def setup_module(module):
    """!
    @brief Load the program's libraries once.
    @param module Unused.
    @return None.
    """
    sc.load_libraries()


@pytest.fixture(scope="module")
def array3():
    """!
    @brief The 3 x 3 array at 3.5 mm pitch (nearest-neighbour distance 3.5 mm).
    @return Problem.
    """
    import cases
    return cases.array(4, 3, 3.5, 0.3, 385.0)


def rule(**kw):
    """!
    @brief A rule dict with the defaults of `tilerule.RULE` and the given changes.
    @param kw Overrides.
    @return dict.
    """
    r = {"kind": "program", "t_mm": 1.0, "k_nn": 0.75, "m_rad": 8.0, "floor_mm": 0.25, "cap_mm": 1.0, "modes_c": 0.0, "max_active": 1200}
    r.update(kw)
    return r


def test_nearest_neighbour_distance_and_radius(array3):
    """!
    @brief The median nearest-neighbour distance of the 3 x 3 array is the pitch, the target radius is exp(-1/4) of the drill radius.
    @param array3 Fixture.
    @return None.
    """
    assert tr.nn_median(array3) == pytest.approx(3.5e-3, rel=1e-9)
    assert tr.via_target_radius(array3) == pytest.approx(np.exp(-0.25) * 0.15e-3, rel=1e-9)


def test_rules_give_the_documented_tiles(array3):
    """!
    @brief fixed, nn, radius, nn_radius and cap_nn on the array: the program's tile is the cap, the floor is respected.
    @param array3 Fixture.
    @return None.
    """
    W, H, tp = array3.board.width, array3.board.height, 5e-3
    a = tr.via_target_radius(array3)
    assert tr.tile_by_rule(array3, W, H, tp, rule(kind="program")) == tp
    assert tr.tile_by_rule(array3, W, H, tp, rule(kind="fixed", t_mm=1.0)) == pytest.approx(1e-3)
    assert tr.tile_by_rule(array3, W, H, tp, rule(kind="fixed", t_mm=9.0)) == tp
    assert tr.tile_by_rule(array3, W, H, tp, rule(kind="nn", k_nn=0.5)) == pytest.approx(1.75e-3)
    assert tr.tile_by_rule(array3, W, H, tp, rule(kind="radius", m_rad=8.0)) == pytest.approx(8 * a)
    assert tr.tile_by_rule(array3, W, H, tp, rule(kind="nn_radius", k_nn=0.75, m_rad=8.0)) == pytest.approx(min(0.75 * 3.5e-3, 8 * a))
    assert tr.tile_by_rule(array3, W, H, tp, rule(kind="cap_nn", cap_mm=1.0, k_nn=0.75)) == pytest.approx(1e-3)
    assert tr.tile_by_rule(array3, W, H, tp, rule(kind="fixed", t_mm=0.05, floor_mm=0.25)) == pytest.approx(0.25e-3)
    with pytest.raises(ValueError):
        tr.tile_by_rule(array3, W, H, tp, rule(kind="nope"))


def test_coarsening_keeps_the_active_tiles_bounded():
    """!
    @brief 400 vias with a 1 mm tile and max_active = 100: the tile grows by sqrt(estimate / max_active).
    @return None.
    """
    prob = sc.big_array(20, 1.0)
    W, H = prob.board.width, prob.board.height
    t = tr.tile_by_rule(prob, W, H, 5e-3, rule(kind="fixed", t_mm=1.0, max_active=100))
    est = min(4 * 400, (W / 1e-3) * (H / 1e-3))
    assert t == pytest.approx(1e-3 * np.sqrt(est / 100), rel=1e-9)
    assert tr.tile_by_rule(prob, W, H, 5e-3, rule(kind="fixed", t_mm=1.0, max_active=100000)) == pytest.approx(1e-3)


def test_no_vias_keeps_the_programs_tile():
    """!
    @brief A board without vias gets the program's tile whatever the rule.
    @return None.
    """
    import cases
    prob = cases.array(4, 3, 3.5, 0.3, 385.0)
    prob.vias = []
    assert tr.tile_by_rule(prob, prob.board.width, prob.board.height, 5e-3, rule(kind="fixed", t_mm=1.0)) == 5e-3


def test_modes_rule():
    """!
    @brief The modes of G: 64 for c = 0 and for small boards, 2 W / t for a long board and a small tile.
    @return None.
    """
    assert tr.modes_needed(0.03, 0.03, 1e-3, 2.0) == (64, 64)
    assert tr.modes_needed(0.1, 0.05, 0.5e-3, 2.0) == (400, 200)
    tr.RULE.update(modes_c=0.0)
    assert tr._g_modes(300, 300, 0.1, 0.1, 1e-3, 1e-3) == (64, 64)
    tr.RULE.update(modes_c=2.0)
    try:
        assert tr._g_modes(300, 300, 0.1, 0.1, 1e-3, 1e-3) == (200, 200)
        assert tr._g_modes(150, 300, 0.1, 0.1, 1e-3, 1e-3) == (150, 200)
    finally:
        tr.RULE.update(modes_c=0.0)


def test_cost_counts_unknowns(array3):
    """!
    @brief The unknowns of the dense system are the active tiles times the layers, the active tiles at most four per via.
    @param array3 Fixture.
    @return None.
    """
    c = tr.cost(array3, rule(kind="fixed", t_mm=1.0))
    assert c["t_mm"] == pytest.approx(21.0 / np.ceil(21.0 / 1.0), rel=1e-6)
    assert c["active"] == min(36, c["tiles"])
    assert c["unknowns"] == c["active"] * 4


def test_patch_is_installed_and_removed(array3):
    """!
    @brief Entering the context replaces `analytic.solve_steady` and adds the hooks; leaving it restores the program's function and removes the hooks and the rule.
    @param array3 Fixture.
    @return None.
    """
    orig = analytic.solve_steady
    before = dict(tr.RULE)
    with tr.patched("fixed", t_mm=1.0):
        assert analytic.solve_steady is not orig
        assert hasattr(analytic, "_g_modes") and hasattr(analytic, "_tile_grid_vias")
        assert tr.RULE["kind"] == "fixed"
    assert analytic.solve_steady is orig
    assert not hasattr(analytic, "_g_modes") and not hasattr(analytic, "_tile_grid_vias")
    assert tr.RULE == before


def test_patch_removed_after_an_exception(array3):
    """!
    @brief An error inside the context leaves the program's function in place.
    @param array3 Fixture.
    @return None.
    """
    orig = analytic.solve_steady
    with pytest.raises(RuntimeError):
        with tr.patched("fixed"):
            raise RuntimeError("boom")
    assert analytic.solve_steady is orig


def test_switched_off_patch_reproduces_the_program_bit_for_bit(array3):
    """!
    @brief mode "off", no spread, the program's tile and 64 modes: the maximum temperature equals the program's to the last digit.
    @param array3 Fixture.
    @return None.
    """
    base = sc.rise(array3, "analytic", 0.5, 300)
    with tr.patched("program", mode="off", spread="none"):
        patched = sc.rise(array3, "analytic", 0.5, 300)
    assert patched == base


def test_modes_hook_changes_the_answer_only_when_asked(array3):
    """!
    @brief With c = 0 the fixed 1 mm tile gives the same result as the explicit call without modes; with c = 2 on a board longer than 32 mm the result differs slightly.
    @param array3 Fixture.
    @return None.
    """
    import cases
    prob = cases.pad(4, 5, 1.2, 0.3, 385.0, side_mm=60.0, source_mm=6.0)
    with tr.patched("fixed", t_mm=1.0, modes_c=0.0):
        a = sc.rise(prob, "analytic", 0.5, 300)
    with tr.patched("fixed", t_mm=1.0, modes_c=2.0):
        b = sc.rise(prob, "analytic", 0.5, 300)
    assert a != b
    assert abs(a - b) < 0.05 * a


def test_reference_parameters_of_a_cell_below_half_a_millimetre():
    """!
    @brief Regression (review): `program_cases.layer_parameters` rounded a 0.45 mm unit cell to 0 cells of 1 mm and divided by zero, which dropped the 0.45 mm pitch from the plan;
           with at least one cell it reads the same uniform parameters as a larger cell, and the fine-grid reference runs.
    @return None.
    """
    import program_cases as pc
    small, big = pc.layer_parameters(sc.unit_cell(0.45, 2)), pc.layer_parameters(sc.unit_cell(1.0, 2))
    for key in ("S", "gz_area"):
        assert np.allclose(small[key], big[key])
    assert small["h_bottom"] == pytest.approx(big["h_bottom"])
    assert sc.reference_e(sc.unit_cell(0.45, 2), 0.05) > 0.0


def test_rule_keeps_the_tile_below_the_pitch_of_a_dense_pad():
    """!
    @brief The rule gives 0.75 d_nn below 1.33 mm of pitch (0.34 mm at 0.45 mm, the held-out pad of `study_s4_heldout.py`), and the coarsening can lift it above that on a large
           array (400 vias at 1.0 mm: 0.87 mm), which is why the coarsening has a warning in the proposal.
    @return None.
    """
    import cases
    rule = dict(tr.RULE, kind="cap_nn", cap_mm=1.0, k_nn=0.75, floor_mm=0.25)
    pad = cases.pad(4, 5, 0.45, 0.3, 385.0, side_mm=16.0, source_mm=4.0)
    assert tr.tile_by_rule(pad, 16e-3, 16e-3, 5e-3, rule) == pytest.approx(0.75 * 0.45e-3)
    big = sc.big_array(20, 1.0)
    w = big.board.width
    assert tr.tile_by_rule(big, w, w, 5e-3, rule) > 0.75e-3 * 1.1
