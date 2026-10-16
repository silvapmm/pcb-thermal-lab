"""!
@file test_api.py
@brief Tests of the public API: options, builder, project files, analysis, accuracy of the simplified models.
"""

import json

import numpy as np
import pytest

from pcbthermal import Problem, SolverOptions, fvm, simulate
from pcbthermal import analysis, analytic, lumped
from pcbthermal.examples import example_board
from pcbthermal.model import problem_from_dict, problem_to_dict
from pcbthermal.project import Project, load_project, save_project


def test_builder_matches_manual_construction():
    p = Problem.new(width_mm=100, height_mm=80, layers=2)
    p.add_full_copper().add_heater(1, 3.0, rect=(10, 10, 20, 20), name="U1")
    p.add_via_array((10, 10, 20, 20), 2, 2)
    p.add_sink(2, 20.0, rect=(0, 0, 30, 30))
    p.validate()
    assert p.total_power() == 3.0 and len(p.vias) == 4 and len(p.zones) == 2
    # Via array is symmetric inside its rectangle
    xs = sorted({round(v.x * 1000, 6) for v in p.vias})
    assert xs == [12.5, 17.5]
    with pytest.raises(ValueError):
        p.add_zone(1)                         # neither rect nor polygon
    with pytest.raises(ValueError):
        p.add_zone(1, rect=(0, 0, 1, 1), polygon=[[0, 0], [1, 0], [1, 1]])


def test_options_validation_and_roundtrip():
    o = SolverOptions(models=("fvm", "analytic"), cell_mm=0.5)
    assert SolverOptions.from_dict(json.loads(json.dumps(o.to_dict()))) == o
    for bad in (dict(models=("magic",)), dict(models=()), dict(cell_mm=0.0), dict(linear_solver="x"),
                dict(lumped_rings=1)):
        with pytest.raises(ValueError):
            SolverOptions(**bad).validate()


def test_simulate_returns_table_report_and_saves(tmp_path):
    sim = simulate(example_board(), SolverOptions(cell_mm=2.0))
    assert set(sim.results) == {"fvm", "lumped", "analytic"}
    rows = {r["model"]: r for r in sim.table()}
    assert rows["fvm"]["error_vs_reference"] == 0.0
    assert "Heater U1" in sim.report() and "junction" in sim.report()
    files = sim.save(tmp_path, plots=False)
    assert any(f.endswith("summary.json") for f in files) and any(f.endswith("field_fvm.csv") for f in files)


def test_project_roundtrip_keeps_everything(tmp_path):
    p = example_board()
    path = tmp_path / "board.pcbt.json"
    save_project(path, Project(problem=p, options=SolverOptions(cell_mm=0.8), view={"zoom": 2.5}))
    q = load_project(path)
    assert q.options.cell_mm == 0.8 and q.view == {"zoom": 2.5}
    assert q.problem.heaters[0].name == "U1" and q.problem.heaters[0].theta_jb == 6.0
    assert len(q.problem.vias) == 9 and q.problem.sinks[0].name == "bottom heatsink"


def test_analysis_hotspots_zones_and_junction():
    p = example_board()
    r = fvm.solve_steady(p, cell_mm=1.0)
    hs = analysis.hotspots(r, 70.0)
    assert hs and hs[0]["t_max"] == pytest.approx(r.t_max, abs=1e-9)
    g = analysis.gradient_magnitude(r)
    assert g.shape == r.T.shape and g.max() > 0
    heaters = analysis.heater_stats(r, p)
    assert heaters[0]["t_junction"] == pytest.approx(heaters[0]["t_max"] + 4.0 * 6.0)
    zones = analysis.zone_stats(r, p)
    assert all(z["t_min"] <= z["t_mean"] <= z["t_max"] for z in zones)
    with pytest.raises(ValueError):
        analysis.hotspots(lumped.solve_steady(p).__class__(model="x", ambient=0, power_in=0, t_max=0, t_min=0,
                                                         t_mean=0, layer_mean=[]), 1.0)


def test_lumped_is_accurate_on_the_multi_feature_example():
    p = example_board()
    f = fvm.solve_steady(p, cell_mm=1.0)
    l = lumped.solve_steady(p)
    assert l.delta_t == pytest.approx(f.delta_t, rel=0.10)
    assert abs(l.balance_error) < 1e-9


def test_lumped_handles_corner_heater_and_two_heaters():
    p = Problem.new(100, 100, layers=2).add_full_copper()
    p.add_heater(1, 4.0, rect=(5, 5, 15, 15)).add_heater(1, 2.0, rect=(70, 70, 80, 80))
    f = fvm.solve_steady(p, cell_mm=1.0)
    l = lumped.solve_steady(p)
    assert l.delta_t == pytest.approx(f.delta_t, rel=0.12)
    assert l.t_mean == pytest.approx(f.t_mean, abs=1.0)


def test_analytic_local_corrections_beat_smearing_and_handle_partial_copper():
    p = example_board()
    f = fvm.solve_steady(p, cell_mm=1.0)
    a_local = analytic.solve_steady(p)
    a_smear = analytic.solve_steady(p, local_corrections=False)
    assert abs(a_local.delta_t / f.delta_t - 1) < abs(a_smear.delta_t / f.delta_t - 1)
    assert abs(a_local.delta_t / f.delta_t - 1) < 0.05      # Per-layer copper weighting handles the partial top copper
    assert abs(a_local.balance_error) < 1e-9


def test_analytic_warns_when_the_copper_edge_crosses_the_heater():
    p = Problem.new(100, 80, 4).add_full_copper([2, 3, 4]).add_zone(1, rect=(15, 15, 85, 65))
    p.add_heater(1, 4.0, rect=(10, 35, 20, 45))               # Straddles the left edge of the top copper
    assert analytic.solve_steady(p).warnings
    sim = simulate(p, SolverOptions(cell_mm=2.0))
    assert any("copper edge" in w for w in sim.problem_warnings)


def test_analytic_exact_on_uniform_board_with_vias_and_sink():
    p = Problem.new(100, 100, layers=2).add_full_copper().add_heater(1, 5.0, rect=(40, 40, 60, 60))
    p.add_via_array((40, 40, 60, 60), 4, 4, 0.3)
    p.add_sink(2, 40.0, rect=(30, 30, 70, 70))
    p.board.h_side = None
    f = fvm.solve_steady(p, cell_mm=1.0)
    a = analytic.solve_steady(p)
    assert a.delta_t == pytest.approx(f.delta_t, rel=0.06)
    assert not a.warnings


def test_legacy_file_is_still_readable(tmp_path):
    d = problem_to_dict(example_board())
    assert problem_from_dict(d).total_power() == pytest.approx(5.5)


def test_lumped_follows_the_footprint_shape_and_missing_copper():
    thin = Problem.new(100, 80, 4).add_full_copper().add_heater(1, 4.0, rect=(30, 38, 70, 42))
    f, l = fvm.solve_steady(thin, cell_mm=1.0), lumped.solve_steady(thin)
    assert l.delta_t == pytest.approx(f.delta_t, rel=0.12)       # A long strip is not a disc (it was +35 % before)
    bare = Problem.new(100, 80, 4).add_full_copper([2, 3, 4]).add_heater(1, 4.0, rect=(40, 35, 50, 45))
    f, l = fvm.solve_steady(bare, cell_mm=1.0), lumped.solve_steady(bare)
    assert l.delta_t == pytest.approx(f.delta_t, rel=0.08)       # Vertical loss under the footprint (it was +24 % before)
    assert abs(l.balance_error) < 1e-9


def test_input_checks_report_doubtful_models():
    from pcbthermal import check_problem

    p = Problem.new(100, 80, 2).add_zone(1, rect=(0, 0, 100, 80))
    p.add_heater(1, 3.0, rect=(90, 30, 110, 50), name="U9")                 # Half outside the board
    p.add_heater(2, 1.0, rect=(10, 10, 20, 20), name="U1")                  # No copper on layer 2
    p.add_heater(1, 1.0, rect=(40, 10, 41, 40), name="strip")               # Thin: too few cells at 1 mm? (1 mm wide)
    p.add_via(150, 10)
    text = "\n".join(check_problem(p, cell_mm=1.0))
    assert "U9" in text and "outside the board" in text
    assert "U1" in text and "no copper" in text
    assert "strip" in text and "cells wide" in text
    assert "Via 1 is outside the board" in text
    assert check_problem(example_board(), cell_mm=1.0) == []                # The example board is clean


def test_suggest_cell_size_follows_the_smallest_heater():
    from pcbthermal import suggest_cell_mm

    p = Problem.new(100, 80, 2).add_heater(1, 1.0, rect=(10, 10, 14, 14))
    assert suggest_cell_mm(p) == pytest.approx(1.0)
    q = Problem.new(100, 80, 2).add_heater(1, 1.0, rect=(10, 10, 12, 12))
    assert suggest_cell_mm(q) == pytest.approx(0.5)
    assert suggest_cell_mm(Problem.new(100, 80, 2)) == 2.0
