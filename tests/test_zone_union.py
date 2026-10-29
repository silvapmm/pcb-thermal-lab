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
