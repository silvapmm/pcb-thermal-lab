#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_program_union.py
@brief How the program combines zones: since release 2.4.3 (`fix/zone-union`, `geometry.zone_fill`) the union is taken at every sample point, so a copper layer made of many abutting polygons keeps all its copper.
@details Frozen history: up to 2.4.2 the program took the maximum per cell, so two zones that each covered half of a cell gave half of the single zone's fill and the same copper cut into 0.5 mm strips
         read +7 % (FVM), +17 % (FDM), +10 % (3D solid), +7 % (Analytic), +8 % (Lumped) hotter (the numbers that the first test below used to assert; README of this folder, 4.10, 4.11). The test is
         inverted as its docstring announced: the strips now give the single zone's answer in all five models. Skipped when the program's dependencies are not installed.
"""

import sys
from pathlib import Path

import pytest

if not any(Path(x, "pcbthermal").is_dir() for x in sys.path[:-1] if x):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))      # the repository root, unless a copy of the program is given on PYTHONPATH
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


def test_union_per_sample_point_keeps_the_copper_when_zones_share_cells():
    """!@brief One zone covering the board against the same copper cut into 0.5 mm strips: every 1 mm cell is shared by two strips, and the program (since 2.4.3) counts all the copper, as the single zone. @return None."""
    for model in ("fvm", "fdm", "solid3d", "analytic", "lumped"):
        whole = mean_rise([(0.0, 0.0, 20.0, 20.0)], model)
        strips = mean_rise([(0.5 * j, 0.0, 0.5 * (j + 1), 20.0) for j in range(40)], model)
        assert strips == pytest.approx(whole, rel=1e-6), model          # measured: identical to the digit in the five models (before 2.4.3: +7 to +17 %)


def test_aligned_zones_are_exact():
    """!@brief The same copper cut into 1 mm strips on the cell boundaries gives the same result as the single zone: the rule only distorts cells shared by several zones. @return None."""
    whole = mean_rise([(0.0, 0.0, 20.0, 20.0)])
    aligned = mean_rise([(1.0 * j, 0.0, 1.0 * (j + 1), 20.0) for j in range(20)])
    assert aligned == pytest.approx(whole, rel=1e-6)
