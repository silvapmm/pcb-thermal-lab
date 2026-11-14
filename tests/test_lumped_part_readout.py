#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_lumped_part_readout.py
@brief The part rows of a Lumped run read the part's own peak (node + peak term), the same quantity as the Lumped board maximum, not the footprint node of the drawn field.
"""

import numpy as np
import pytest

from pcbthermal import Problem, fvm, lumped
from pcbthermal.analysis import heater_stats


def _board(kind):
    """!
    @brief A small synthetic board.
    @param kind 'block' (one 12 mm pad, 6 mm part, aluminium plate), 'plain' (a 6 mm part on a plane) or 'two' (two parts, one with a junction resistance).
    @return Problem.
    """
    p = Problem.new(100.0, 80.0, 2).add_zone(1, rect=(0, 0, 100, 80))
    if kind == "block":
        p.add_zone(2, rect=(44, 34, 56, 46))
        p.add_heater(1, 5.0, rect=(47, 37, 53, 43))
        p.add_heatsink(2, 0.0, rect=(10, 10, 90, 70), thickness_mm=1.5, k=204.0, contact_r=5e-4)
    elif kind == "plain":
        p.add_heater(1, 3.0, rect=(47, 37, 53, 43))
    else:
        p.add_heater(1, 2.0, rect=(30, 37, 36, 43))
        p.add_heater(1, 1.0, rect=(64, 37, 70, 43))
        p.heaters[0].theta = 5.0
    return p


@pytest.mark.parametrize("kind", ["block", "plain", "two"])
def test_the_part_row_reads_the_peak_not_the_node(kind):
    p = _board(kind)
    res = lumped.solve_steady(p, cell_mm=0.5)
    amb = res.ambient
    rows = heater_stats(res, p)
    peak = res.arrays["heater_peak"]
    # The row is the larger of the drawn field (the reading without the array) and the part's own peak
    assert peak.shape == (len(p.heaters),)
    held = res.arrays.pop("heater_peak")
    field_rows = heater_stats(res, p)
    res.arrays["heater_peak"] = held
    for row, f_row, pk in zip(rows, field_rows, peak):
        assert row["t_max"] == pytest.approx(max(f_row["t_max"], pk), abs=1e-12)
    # The hottest part's reading is the board maximum the model reports (same quantity)
    assert max(r["t_max"] for r in rows) == pytest.approx(res.t_max, abs=1e-9)
    # Against the FVM: the node read-out was 10 % of the rise too cool; the peak is within 8 %
    ref = heater_stats(fvm.solve_steady(p, 0.5), p)
    for row, r in zip(rows, ref):
        assert abs(row["t_max"] - r["t_max"]) < 0.08 * (r["t_max"] - amb)
    # Junction temperature follows the part reading
    if kind == "two":
        assert rows[0]["t_junction"] == pytest.approx(rows[0]["t_max"] + 2.0 * 5.0)


def test_the_node_reading_was_too_cool():
    # The same part read from the drawn field only (the old behaviour) is far below the peak: this is what the fix removes
    p = _board("block")
    res = lumped.solve_steady(p, cell_mm=0.5)
    res.arrays.pop("heater_peak")
    old = heater_stats(res, p)[0]["t_max"]
    new = heater_stats(lumped.solve_steady(p, cell_mm=0.5), p)[0]["t_max"]
    assert (new - old) > 0.05 * (new - res.ambient)


def test_a_result_without_the_array_reads_the_field_as_before():
    p = _board("plain")
    res = fvm.solve_steady(p, 1.0)
    assert "heater_peak" not in res.arrays
    assert np.isfinite(heater_stats(res, p)[0]["t_max"])


def test_the_board_maximum_of_the_lumped_is_unchanged_by_the_array():
    p = _board("two")
    res = lumped.solve_steady(p, cell_mm=1.0)
    own = np.nanmax(res.arrays["heater_peak"])
    assert own <= res.t_max + 1e-9


def test_a_neighbour_hotter_than_the_peak_keeps_the_field():
    # Two parts 2 mm apart: under the first footprint the painted field (its node plus the neighbour's profile near the neighbour) is above the own peak, which reads the
    # neighbour at the centroid only; the larger value is kept, so the row never falls below what the map shows
    p = Problem.new(100.0, 80.0, 2).add_zone(1, rect=(0, 0, 100, 80))
    p.add_heater(1, 2.0, rect=(40, 37, 46, 43))
    p.add_heater(1, 2.0, rect=(48, 37, 54, 43))
    res = lumped.solve_steady(p, cell_mm=0.5)
    rows = heater_stats(res, p)
    assert rows[0]["t_max"] > res.arrays["heater_peak"][0]
    assert rows[0]["t_max"] <= res.t_max + 1e-9


def test_an_outline_board_reads_the_peak_of_the_equivalent_rectangle():
    # simulate() solves the Lumped on the rectangle of the same area and stretches the field back; the own peak is a temperature per part (no frame), so the
    # single part reads the Lumped board maximum
    from pcbthermal import SolverOptions, simulate
    p = Problem.new(100.0, 80.0, 2).add_zone(1, rect=(0, 0, 100, 80)).add_zone(2, rect=(0, 0, 100, 80))
    p.set_outline([[0, 0], [100, 0], [100, 40], [50, 40], [50, 80], [0, 80]])
    p.add_heater(1, 2.0, rect=(22, 37, 28, 43))
    sim = simulate(p, SolverOptions(models=("lumped",), cell_mm=1.0))
    assert sim.heater_rows()[0]["t_max"] == pytest.approx(sim.results["lumped"].t_max, abs=1e-9)


def test_the_top_path_split_of_a_lumped_run_converges_on_the_peak():
    # The split reads the part through heater_stats: with the peak the part is hotter, more heat leaves by the top, and the root is still found
    from pcbthermal import SolverOptions, simulate
    p = Problem.new(100.0, 80.0, 2).add_zone(1, rect=(30, 20, 70, 60))
    p.add_heater(1, 3.0, rect=(47, 37, 53, 43), theta=2.0, theta_jc_top=5.0, theta_sa=10.0)
    sim = simulate(p, SolverOptions(models=("lumped",), cell_mm=1.0))
    row = sim.heater_rows()[0]
    assert not any("did not converge" in w for w in sim.results["lumped"].warnings)
    assert row["t_max"] == pytest.approx(sim.results["lumped"].t_max, abs=1e-9)
    assert 0.0 < row["power_top_w"] < 3.0
