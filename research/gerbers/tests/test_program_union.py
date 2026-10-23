"""!
@file test_program_union.py
@brief How the program combines zones: abutting zones are combined with a maximum per cell, not a sum of coverage, so a copper layer made of many small polygons loses copper in every cell they share.
@details This documents the behaviour of the program as it is (nothing in pcbthermal/ was changed by the research). It matters for importing copper as polygons (`research/gerbers/INTEGRATION.md`):
         two zones that each cover half of a cell give a cell fill of one half of the single zone's value, not the full value. If the program is changed to add the coverage of non-overlapping zones,
         the first test below must be inverted. Skipped when the program's dependencies are not installed.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
pcbthermal = pytest.importorskip("pcbthermal")


def mean_rise(zones, model="fvm"):
    """!
    @brief Mean heater rise of a 20 x 20 mm single-layer board with the given zones, 1 mm cells.
    @param zones List of (x0, y0, x1, y1) rectangles in mm, all with fill 1.
    @param model Model key.
    @return Mean rise (K) of the 4 x 4 mm heater at the centre.
    """
    from pcbthermal import Problem, SolverOptions, simulate
    from pcbthermal.analysis import heater_stats
    p = Problem.new(width_mm=20.0, height_mm=20.0, layers=1, thickness_mm=1.6, copper_um=35.0, h_top=10.0, h_bottom=10.0, h_side=None)
    p.add_heater(1, 1.0, rect=(8.0, 8.0, 12.0, 12.0))
    for r in zones:
        p.add_zone(1, rect=r, fill=1.0)
    sim = simulate(p, SolverOptions(models=(model,), cell_mm=1.0))
    return heater_stats(sim.results[model], p)[0]["t_mean"] - p.board.ambient


def test_union_by_maximum_loses_copper_when_zones_share_cells():
    """!@brief One zone covering the board against the same copper cut into 0.5 mm strips: every 1 mm cell is shared by two strips, each covering half of it, and the program counts half the copper. @return None."""
    for model in ("fvm", "fdm", "solid3d", "analytic", "lumped"):
        whole = mean_rise([(0.0, 0.0, 20.0, 20.0)], model)
        strips = mean_rise([(0.5 * j, 0.0, 0.5 * (j + 1), 20.0) for j in range(40)], model)
        assert strips > 1.04 * whole, model                             # the same copper, hotter: +7 % FVM, +17 % FDM, +10 % 3D solid, +7 % Analytic, +8 % Lumped when written


def test_aligned_zones_are_exact():
    """!@brief The same copper cut into 1 mm strips on the cell boundaries gives the same result as the single zone: the rule only distorts cells shared by several zones. @return None."""
    whole = mean_rise([(0.0, 0.0, 20.0, 20.0)])
    aligned = mean_rise([(1.0 * j, 0.0, 1.0 * (j + 1), 20.0) for j in range(20)])
    assert aligned == pytest.approx(whole, rel=1e-6)
