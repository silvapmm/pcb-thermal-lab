#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_real_board.py
@brief Tests of the board builders of study S2 (`lib/real_board.py`, `lib/matrix_stats.py`): the own via field, window search, statistics, and the reading of the real boards when their files are present.
"""

import os
import sys

import pytest

LIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib")
sys.path.insert(0, LIB)

import matrix_stats as ms                                                   # noqa: E402
import real_board as rbd                                                    # noqa: E402


def test_own_via_field_counts_and_stays_on_the_board():
    """!@brief n x n thermal vias plus the ring, all inside the board."""
    holes, w, h = rbd.own_via_field(10)
    assert len(holes) == 100 + 24
    assert all(0 < x < w and 0 < y < h for x, y, _ in holes)


def test_densest_window_finds_the_thermal_field():
    """!@brief The densest 7 mm window of the own field is the one over the array (all 100 vias inside)."""
    holes, w, h = rbd.own_via_field(10)
    cx, cy, n = rbd.densest_window(holes, 7.5, w, h, 0.5)
    assert n >= 100 and abs(cx - w / 2) < 1.0 and abs(cy - h / 2) < 1.0


def test_problem_has_one_via_per_hole_and_one_source():
    """!@brief problem_from_holes: layers, vias and the source on the densest window."""
    holes, w, h = rbd.own_via_field(5)
    p = rbd.problem_from_holes(holes, w, h, layers=4)
    assert len(p.vias) == len(holes) and len(p.heaters) == 1 and p.board.layers == 4


def test_hole_statistics_counts_shared_cells_and_overlaps():
    """!@brief Two holes in one cell are a shared cell; far holes are not an overlapping pair."""
    s = rbd.hole_statistics([(0.2, 0.2, 0.3), (0.4, 0.4, 0.3), (9.0, 9.0, 0.3)], 1.0, 10.0, 10.0)
    assert s["n"] == 3 and s["cells_with_via"] == 2 and s["max_per_cell"] == 2 and s["pairs_closer_than"] == 1


def test_dense_entries_estimate_grows_with_vias_and_fineness():
    """!@brief The guard of the fill-in study: quadratic in the footprint, linear in the number of vias."""
    a = ms.estimate_dense_entries(100, 0.3, 0.5, 4)
    assert ms.estimate_dense_entries(200, 0.3, 0.5, 4) == pytest.approx(2 * a)
    assert ms.estimate_dense_entries(100, 0.3, 0.125, 4) > a


@pytest.mark.parametrize("name,minimum", [("alleg", 280), ("storm", 100)])
def test_real_boards_have_enough_plated_holes_when_fetched(name, minimum):
    """!@brief The Allegro board has 283 plated holes and the Stormduino 109 (skipped when the files are not in the data folder)."""
    try:
        holes, w, h = rbd.holes_of(name)
    except FileNotFoundError:
        pytest.skip(f"{name} not fetched")
    assert len(holes) >= minimum and w > 10 and h > 10
