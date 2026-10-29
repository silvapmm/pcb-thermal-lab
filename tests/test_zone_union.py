#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_zone_union.py
@brief Zones of one layer are combined by the union of their points, not by the larger of their shares of a cell.
@details Two zones that meet inside a cell each cover part of it; the older rule kept the larger part and lost the copper of the other (5 to 15 % too
         cool on real copper). The union per sample point keeps both parts.
"""

import numpy as np
import pytest

from pcbthermal import Problem, SolverOptions, simulate
from pcbthermal.geometry import coverage_fraction, zone_fill


def two_zone_board():
    """!
    @brief A 40 x 20 mm board whose top copper is two zones that meet at x = 20.25 mm, inside the 0.5 mm cell that spans 20.0 to 20.5 mm.
    @return Problem.
    """
    p = Problem.new(40, 20, 2)
    p.add_zone(1, rect=(0, 0, 20.25, 20))
    p.add_zone(1, rect=(20.25, 0, 40, 20))
    p.add_zone(2, rect=(0, 0, 40, 20))
    p.add_heater(1, 2.0, rect=(15, 8, 25, 12), name="U")
    return p


def one_zone_board():
    """!
    @brief The same board with the top copper drawn as one zone.
    @return Problem.
    """
    p = Problem.new(40, 20, 2)
    p.add_zone(1, rect=(0, 0, 40, 20))
    p.add_zone(2, rect=(0, 0, 40, 20))
    p.add_heater(1, 2.0, rect=(15, 8, 25, 12), name="U")
    return p


def test_two_zones_that_meet_inside_a_cell_leave_no_gap():
    p = two_zone_board()
    nx, ny = 80, 40
    dx, dy = p.board.width / nx, p.board.height / ny
    field = zone_fill(p.zones, 2, nx, ny, dx, dy, 4)
    assert np.allclose(field, 1.0)
    # The rule that was replaced: the larger of the two shares of the cell
    old = np.zeros((nx and ny, nx))
    for z in p.zones:
        if z.layer == 0:
            old = np.maximum(old, coverage_fraction(z.polygon, nx, ny, dx, dy, 4) * z.fill)
    assert old.min() < 0.6                                    # The column of cells at x = 20.0 to 20.5 mm lost half of its copper


@pytest.mark.parametrize("model", ["fvm", "fdm", "solid3d", "analytic"])
def test_two_zones_equal_one_zone(model):
    opt = SolverOptions(models=(model,), cell_mm=0.5 if model != "solid3d" else 1.0)
    split = simulate(two_zone_board(), opt).results[model].t_max
    whole = simulate(one_zone_board(), opt).results[model].t_max
    assert split == pytest.approx(whole, abs=1e-6)


def test_a_hatched_zone_keeps_its_fill_and_zones_that_do_not_touch_are_unchanged():
    p = Problem.new(30, 20, 2)
    p.add_zone(1, rect=(0, 0, 10, 20), fill=0.5)
    p.add_zone(1, rect=(12, 0, 30, 20), fill=1.0)
    nx, ny = 60, 40
    dx, dy = 0.03 / nx, 0.02 / ny
    field = zone_fill(p.zones, 2, nx, ny, dx, dy, 4)
    assert np.allclose(field[0, :, :19], 0.5) and np.allclose(field[0, :, 25:], 1.0)
    assert np.allclose(field[0, :, 20:24], 0.0)               # The gap between the zones has no copper
    assert not field[1].any()                                  # A layer without zones stays empty


def test_a_zone_whose_outline_crosses_itself_is_warned_and_ordinary_shapes_are_not():
    from pcbthermal.checks import check_problem
    from pcbthermal.geometry import polygon_self_intersects
    square = [[0, 0], [10, 0], [10, 10], [0, 10]]
    l_shape = [[0, 0], [10, 0], [10, 4], [4, 4], [4, 10], [0, 10]]
    bowtie = [[0, 0], [10, 10], [10, 0], [0, 10]]
    pentagram = [[5, 0], [8, 10], [0, 4], [10, 4], [2, 10]]
    assert not polygon_self_intersects(square) and not polygon_self_intersects(l_shape)
    assert not polygon_self_intersects([[0, 0], [5, 0], [2, 3]])
    assert polygon_self_intersects(bowtie) and polygon_self_intersects(pentagram)
    p = Problem.new(40, 20, 2)
    p.add_zone(1, polygon=bowtie, name="Pour")
    p.add_zone(2, rect=(0, 0, 40, 20))
    msgs = [str(w) for w in check_problem(p) if "crosses itself" in str(w)]
    assert len(msgs) == 1 and "Pour" in msgs[0]
    ok = Problem.new(40, 20, 2)
    ok.add_zone(1, polygon=l_shape)
    assert not [w for w in check_problem(ok) if "crosses itself" in str(w)]


def test_the_fdm_point_sampling_path_keeps_the_maximum_per_node_which_is_exact_there():
    from pcbthermal import fdm
    split = fdm.solve_steady(two_zone_board(), 0.5, sampling="point").t_max
    whole = fdm.solve_steady(one_zone_board(), 0.5, sampling="point").t_max
    assert split == pytest.approx(whole, abs=1e-9)
