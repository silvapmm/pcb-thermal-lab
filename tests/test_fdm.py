#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_fdm.py
@brief The finite-difference comparison model: same physics as the FVM, different discretisation.
"""

import pytest

from pcbthermal import Problem, SolverOptions, fdm, fvm, simulate
from pcbthermal.examples import example_board
from pcbthermal.model import reference_problem


def test_fdm_matches_the_fvm_on_a_uniform_board_and_converges():
    p = reference_problem(layers=2, heater_mm=20.0, power=5.0)
    reference = fvm.solve_steady(p, 0.5).t_max
    for cell, tol in ((4.0, 1.8), (2.0, 0.3), (1.0, 0.1)):
        r = fdm.solve_steady(p, cell)
        assert r.t_max == pytest.approx(reference, abs=tol)               # Same equations, only the sampling differs
        assert abs(r.balance_error) < 1e-9 and r.power_in == pytest.approx(5.0)
    errors = [abs(fdm.solve_steady(p, c).t_max - reference) for c in (4.0, 2.0, 1.0)]
    assert errors[0] > errors[1] > errors[2]                              # Area sampling converges monotonically
    # The classic point sampling is also available and lands on the same limit
    assert fdm.solve_steady(p, 1.0, sampling="point").t_max == pytest.approx(reference, abs=0.2)
    with pytest.raises(ValueError):
        fdm.solve_steady(p, 2.0, sampling="magic")


def test_fdm_on_the_example_board_with_both_face_means():
    p = example_board()
    ref = fvm.solve_steady(p, 0.5).t_max
    for mean in ("arithmetic", "harmonic"):
        r = fdm.solve_steady(p, 1.0, mean)
        assert r.t_max == pytest.approx(ref, abs=2.0) and abs(r.balance_error) < 1e-9
        assert r.T.shape == (4, 81, 101)                                  # Nodes, not cells
    assert fdm.solve_steady(p, 2.0).grid == "nodes"
    xs, ys = fdm.solve_steady(p, 2.0).coords()
    assert xs[0] == 0.0 and xs[-1] == pytest.approx(0.1) and ys[-1] == pytest.approx(0.08)


def test_fdm_is_selectable_through_the_api_and_runs_the_time_simulation():
    from pcbthermal.examples import example_profile_board
    s = simulate(example_board(), SolverOptions(models=("fvm", "fdm"), cell_mm=2.0))
    assert set(s.results) == {"fvm", "fdm"} and s.results["fdm"].t_max == pytest.approx(s.results["fvm"].t_max, abs=1.5)
    t = simulate(example_profile_board(), SolverOptions(models=("fvm", "fdm"), cell_mm=2.0))
    assert set(t.profile_results) == {"fvm", "fdm"} and not t.profile_error
    f, d = t.profile_results["fvm"], t.profile_results["fdm"]
    assert d.resolved and d.peak == pytest.approx(f.peak, rel=0.05) and d.steady_average_max == pytest.approx(f.steady_average_max, abs=1.5)
    assert d.peak_map.shape[1:] == (41, 51) and d.frames.shape[2:] == (41, 51)                 # Nodes
    # The FDM alone decides and simulates
    only = simulate(example_profile_board(), SolverOptions(models=("fdm",), cell_mm=2.0))
    assert not only.profile_error and only.profile_reference == "fdm" and only.profile_results["fdm"].resolved
    with pytest.raises(ValueError):
        SolverOptions(models=("fem",)).validate()


def test_cli_compare(tmp_path, capsys):
    from pcbthermal import cli
    path = tmp_path / "e.pcbt.json"
    cli.main(["example", str(path), "--which", "example"])
    assert cli.main(["run", str(path), "--model", "compare", "--cell-mm", "2", "--out", str(tmp_path / "o"), "--no-plots"]) == 0
    assert "fdm" in capsys.readouterr().out


def test_fdm_results_work_in_the_analysis_and_plots(tmp_path):
    from pcbthermal import analysis, plots
    p = example_board()
    r = fdm.solve_steady(p, 1.0)
    ref = fvm.solve_steady(p, 1.0)
    stats = {h["name"]: h for h in analysis.heater_stats(r, p)}
    base = {h["name"]: h for h in analysis.heater_stats(ref, p)}
    assert stats["U1"]["t_max"] == pytest.approx(base["U1"]["t_max"], abs=1.5)
    spots = analysis.hotspots(r, 80.0)
    assert spots and spots[0]["x_mm"] == pytest.approx(ref and analysis.hotspots(ref, 80.0)[0]["x_mm"], abs=6.0)
    fig = plots.new_figure()
    plots.draw_field(fig, r.T[0], p, r.dx, r.dy)                       # The node field has one sample more than the cells
    plots.draw_profile(fig, {"fvm": ref, "fdm": r}, p)
    plots.draw_fields(fig, r, p)


def test_fdm_transient_and_step_responses_follow_the_fvm(tmp_path):
    from pcbthermal import plots
    p = example_board()
    a = fdm.solve_transient(p, 120.0, n_out=20, cell_mm=2.0)
    b = fvm.solve_transient(p, 120.0, n_out=20, cell_mm=2.0)
    assert a.grid == "nodes" and b.grid == "cells" and a.frames.shape[2:] == (41, 51)
    assert a.times[0] == 0.0 and a.t_max[0] == pytest.approx(25.0) and len(a.times) == len(b.times)
    assert float(abs(a.t_max - b.t_max).max()) < 1.0                       # The same time stepping on the same physics
    assert a.steady_t_max == pytest.approx(fdm.solve_steady(p, 2.0).t_max)
    dx, dy = plots.frame_spacing(a, p)
    assert dx == pytest.approx(0.1 / 50) and dy == pytest.approx(0.08 / 40)
    plots.save_transient_gif(fdm.solve_transient(p, 30.0, n_out=10, cell_mm=4.0), p, str(tmp_path / "t.gif"))
    assert (tmp_path / "t.gif").stat().st_size > 1000
    t, z, rth = fdm.step_responses(p, 2.0)
    assert rth == pytest.approx(fvm.step_responses(p, 2.0)[2], rel=0.08) and z.shape[0] == 2
    with pytest.raises(ValueError):
        fdm.step_responses(Problem.new(50, 40, 2).add_full_copper())


def test_cli_transient_with_every_model(tmp_path, capsys):
    from pcbthermal import cli
    path = tmp_path / "e.pcbt.json"
    cli.main(["example", str(path), "--which", "example"])
    for model in ("fvm", "fdm", "analytic"):
        assert cli.main(["transient", str(path), "--model", model, "--t-end", "60", "--steps", "10", "--cell-mm", "4",
                         "--out", str(tmp_path / model), "--no-plots"]) == 0
        assert (tmp_path / model / "transient.csv").exists()
