#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_profiles.py
@brief Power profiles: square wave, average-or-resolve decision, time simulation in the three models.
"""

import json

import numpy as np
import pytest

from pcbthermal import Problem, SolverOptions, SquareWave, fvm, laminate, lumped, analytic, profiles, simulate
from pcbthermal.examples import example_board
from pcbthermal.model import problem_from_dict, problem_to_dict, reference_problem
from pcbthermal.profiles import ProfileError, ProfileOptions


def example_with_profiles(fast_hz=100.0):
    """!
    @brief The example board with U1 switching fast (averaged) and U2 on a 20 s cycle (resolved).
    @param fast_hz Frequency of U1 in hertz.
    @return Problem.
    """
    p = example_board()
    p.heaters[0].set_profile(SquareWave(p_on=4.0 / 0.30, period=1.0 / fast_hz, duty=0.30))
    p.heaters[1].set_profile(SquareWave(p_on=1.5 / 0.25, period=20.0, duty=0.25))
    return p


def test_square_wave_energy_is_exact_for_any_step_alignment():
    w = SquareWave(p_on=10.0, period=1.0, duty=0.3, p_off=1.0)
    assert w.average() == pytest.approx(3.7)
    assert w.mean_power(0.0, 1.0) == pytest.approx(3.7)
    assert w.mean_power(0.2, 0.5) == pytest.approx((0.1 * 10 + 0.2 * 1) / 0.3)         # An edge inside the interval
    # Whatever the step, the energy of n steps equals the exact integral
    for dt in (0.013, 0.1, 0.37):
        t = np.arange(0, 200) * dt
        assert np.sum(w.mean_power(t, t + dt) * dt) == pytest.approx(float(w.cumulative(200 * dt)), rel=1e-12)
    for bad in (SquareWave(1, 0, 0.5), SquareWave(1, 1, 0.0), SquareWave(1, 1, 1.5), SquareWave(1, 1, 0.5, p_off=2)):
        with pytest.raises(ValueError):
            bad.validate()


def test_profiles_roundtrip_and_steady_copy():
    p = example_with_profiles()
    q = problem_from_dict(json.loads(json.dumps(problem_to_dict(p))))
    assert q.has_profiles() and q.heaters[1].profile.period == 20.0
    assert q.total_power() == pytest.approx(5.5)
    assert q.steady_copy("peak").total_power() == pytest.approx(4.0 / 0.30 + 1.5 / 0.25)
    assert q.steady_copy("average").total_power() == pytest.approx(5.5)
    assert q.heaters[0].profile is not None                    # The copy keeps the profiles
    with pytest.raises(ValueError):
        q.steady_copy("rms")


def test_decision_averages_the_fast_heater_and_resolves_the_slow_one():
    p = example_with_profiles()
    resp = profiles.step_response_fvm(p, 2.0)
    d = profiles.decide(p, resp, 1.0)
    assert [x.regime for x in d] == ["average", "resolved"]
    assert d[0].oscillation < 1.0 < d[1].oscillation
    # With a huge threshold everything is averaged; with a zero threshold every wave that oscillates is resolved
    assert [x.regime for x in profiles.decide(p, resp, 1e6)] == ["average", "average"]
    assert [x.regime for x in profiles.decide(p, resp, 0.0)] == ["resolved", "resolved"]


def test_error_budget_is_shared_between_heaters():
    p = Problem.new(100, 80, 2).add_full_copper()
    for k in range(3):
        p.add_heater(1, 1.0, rect=(10 + 25 * k, 30, 20 + 25 * k, 40),
                     profile=SquareWave(p_on=5.0, period=0.05, duty=0.2))
    resp = profiles.step_response_fvm(p, 2.0)
    one = profiles.decide(p, resp, 1e6)[0].oscillation
    d = profiles.decide(p, resp, 1.5 * one)               # Room for only one heater's oscillation
    assert sorted(x.regime for x in d) == ["average", "resolved", "resolved"]


def test_fvm_matches_the_exact_rc_response_of_a_uniform_board(monkeypatch):
    # One layer, a heater over the whole board, insulated edges: the temperature is uniform and obeys C T' = P(t) - G T
    # (a single node: the laminate nodes of a one-layer board are switched off, the time integration is what is tested)
    monkeypatch.setattr(laminate, "LAMINATE_NODES", 0)
    p = reference_problem(layers=1, heater_mm=100.0, power=10.0)
    p.board.h_side = None
    net = fvm.Network(p, 8, 8, assemble=False)
    C, G = net.C.sum(), net.g_amb.sum()
    tau = C / G
    wave = SquareWave(p_on=40.0, period=40.0, duty=0.25)
    p.heaters[0].set_profile(wave)
    a, b = np.exp(-10.0 / tau), np.exp(-30.0 / tau)
    peak = 40.0 * (1 - a) / (G * (1 - a * b))                         # Periodic steady state, end of the on-phase
    resp = profiles.step_response_fvm(p, 12.5)
    dec = profiles.decide(p, resp, 0.0)
    assert dec[0].regime == "resolved"
    # The periodic peak of the decision step uses only Z(t): it must match the exact value as well
    assert dec[0].periodic_peak_rise == pytest.approx(peak, rel=0.003)
    for theta, tol in ((0.5, 0.004), (1.0, 0.03)):
        r = profiles.run_fvm(p, dec, ProfileOptions(theta=theta, duration="cycles", cycles=12), cell_mm=12.5)
        assert r.converged
        assert r.peak - p.board.ambient == pytest.approx(peak, rel=tol)


def test_mixed_regimes_match_the_fully_resolved_run():
    # Averaging the fast heater changes the answer by no more than the oscillation that was neglected
    p = Problem.new(60, 50, 2).add_full_copper()
    p.add_heater(1, 3.0, rect=(10, 20, 20, 30), name="fast", profile=SquareWave(p_on=10.0, period=0.05, duty=0.3))
    p.add_heater(1, 1.0, rect=(35, 20, 45, 30), name="slow", profile=SquareWave(p_on=4.0, period=2.0, duty=0.25))
    resp = profiles.step_response_fvm(p, 4.0)
    mixed_dec = profiles.decide(p, resp, 1.0)
    assert [d.regime for d in mixed_dec] == ["average", "resolved"]
    full_dec = profiles.decide(p, resp, 0.0)
    opt = ProfileOptions(duration="cycles", cycles=4)
    mixed = profiles.run_fvm(p, mixed_dec, opt, cell_mm=4.0)
    full = profiles.run_fvm(p, full_dec, opt, cell_mm=4.0)
    assert full.steps > 5 * mixed.steps                                 # Averaging the fast heater is much cheaper
    assert abs(full.peak - mixed.peak) <= mixed_dec[0].oscillation + 0.15
    assert abs(float(np.mean(full.t_max)) - float(np.mean(mixed.t_max))) < 0.15


def test_models_agree_on_a_profile_run():
    p = example_with_profiles()
    sim = simulate(p, SolverOptions(cell_mm=2.0))
    peaks = {k: r.peak for k, r in sim.profile_results.items()}
    assert set(peaks) == {"fvm", "lumped", "analytic"}
    assert all(r.resolved and r.converged for r in sim.profile_results.values())
    assert peaks["lumped"] == pytest.approx(peaks["fvm"], rel=0.05)
    assert peaks["analytic"] == pytest.approx(peaks["fvm"], rel=0.05)
    f = sim.profile_results["fvm"]
    assert f.steady_average_max < f.peak < f.steady_peak_max                  # The bracket holds
    assert f.peak_map.max() == pytest.approx(f.peak, abs=0.01)                # The map is consistent with the series
    assert any("smears" in w for w in sim.warnings)                          # The analytic transient says what it ignores


def test_run_options_duration_start_and_limits():
    p = example_with_profiles()
    sim_stable = simulate(p, SolverOptions(models=("fvm",), cell_mm=2.0))
    assert sim_stable.profile_results["fvm"].windows <= 12
    cyc = simulate(p, SolverOptions(models=("fvm",), cell_mm=2.0, profile=ProfileOptions(duration="cycles", cycles=3)))
    assert cyc.profile_results["fvm"].windows == 3
    # Start temperature: the default is the ambient (a cold start); two windows from there are still cooler than the stable cycle
    cold = simulate(p, SolverOptions(models=("fvm",), cell_mm=2.0,
                                     profile=ProfileOptions(initial="temperature", duration="cycles", cycles=2)))
    r = cold.profile_results["fvm"]
    assert r.initial_c == p.board.ambient
    assert r.peak < sim_stable.profile_results["fvm"].peak - 5.0
    warm = simulate(p, SolverOptions(models=("fvm",), cell_mm=2.0,
                                     profile=ProfileOptions(initial="temperature", initial_c=60.0, duration="cycles", cycles=2)))
    assert warm.profile_results["fvm"].initial_c == 60.0                        # The temperature typed by the user is used
    assert warm.profile_results["fvm"].peak > r.peak
    hot = simulate(p, SolverOptions(models=("fvm",), cell_mm=2.0, profile=ProfileOptions(max_steps=100)))
    assert "steps" in hot.profile_error and not hot.profile_results           # Too expensive: reported, steady results kept
    assert hot.results["fvm"].t_max > 25.0
    # Steady models can use the peak power (the worst-case bound)
    peak = simulate(p, SolverOptions(models=("fvm",), cell_mm=2.0, steady_power="peak"))
    assert peak.results["fvm"].power_in == pytest.approx(4.0 / 0.30 + 1.5 / 0.25)


def test_all_heaters_averaged_needs_no_time_stepping():
    p = example_with_profiles(fast_hz=1000.0)
    p.heaters[1].set_profile(SquareWave(p_on=1.5 / 0.25, period=0.002, duty=0.25))
    sim = simulate(p, SolverOptions(models=("fvm",), cell_mm=2.0))
    r = sim.profile_results["fvm"]
    assert not r.resolved and r.steps == 0
    assert r.peak == pytest.approx(r.steady_average_max)


def test_profile_outputs_are_saved(tmp_path):
    sim = simulate(example_with_profiles(), SolverOptions(models=("fvm",), cell_mm=2.0))
    files = sim.save(tmp_path)
    names = {f.split("/")[-1] for f in files}
    assert {"profile_fvm.csv", "profile_fvm.png", "peak_map_fvm.png"} <= names
    report = sim.report()
    assert "Power profiles" in report and "resolved" in report and "average" in report
    assert sim.to_dict()["profile"]["models"]["fvm"]["peak_c"] == pytest.approx(sim.profile_results["fvm"].peak)


def test_cli_runs_a_profile_project(tmp_path, capsys):
    from pcbthermal import cli
    path = tmp_path / "p.pcbt.json"
    assert cli.main(["example", str(path), "--which", "profile"]) == 0
    assert cli.main(["run", str(path), "--model", "fvm", "--cell-mm", "2", "--out", str(tmp_path / "o"),
                     "--no-plots", "--duration", "cycles", "--cycles", "2"]) == 0
    out = capsys.readouterr().out
    assert "Power profiles" in out and "resolved" in out
    assert (tmp_path / "o" / "profile_fvm.csv").exists()


# ------------------------------------------------------------------ table profiles and CSV files

def test_table_profile_energy_average_and_hold():
    from pcbthermal import TableProfile
    t = TableProfile([0, 2, 5, 9, 20], [6, 1, 3, 0], True)
    assert t.average() == pytest.approx((12 + 3 + 12) / 20.0) and t.peak() == 6.0 and t.period == 20.0
    assert t.shortest_feature() == 2.0
    for dt in (0.013, 0.7, 3.1):
        x = np.arange(0, 100) * dt
        assert np.sum(t.mean_power(x, x + dt) * dt) == pytest.approx(float(t.cumulative(100 * dt)), rel=1e-12)
    assert t.mean_power(1.0, 3.0) == pytest.approx((6 * 1 + 1 * 1) / 2.0)             # An edge inside the interval
    assert t.mean_power(19.0, 21.0) == pytest.approx((0 * 1 + 6 * 1) / 2.0)           # Wraps to the next period
    once = TableProfile([0, 2, 5], [6, 1], False)
    assert once.mean_power(5.0, 105.0) == pytest.approx(1.0)                           # The last power is held
    assert once.initial_power() == 6.0 and t.initial_power() == pytest.approx(t.average())
    for bad in (TableProfile([1, 2], [1], True), TableProfile([0, 2, 2], [1, 1], True), TableProfile([0, 1], [-1], True),
                TableProfile([0, 1, 2], [1], True)):
        with pytest.raises(ValueError):
            bad.validate()


def test_square_wave_as_table_gives_the_same_decision(monkeypatch):
    p = example_with_profiles()
    resp = profiles.step_response_fvm(p, 2.0)
    for i in (0, 1):
        w = p.heaters[i].profile
        assert profiles.wave_response(resp, i, w.as_table()) == pytest.approx(profiles.wave_response(resp, i, w), rel=1e-9)
    # Against the exact RC solution (uniform board): a three-level table
    from pcbthermal import TableProfile
    monkeypatch.setattr(laminate, "LAMINATE_NODES", 0)                 # The exact RC solution is that of a single node
    u = reference_problem(layers=1, heater_mm=100.0, power=10.0)
    u.board.h_side = None
    net = fvm.Network(u, 8, 8, assemble=False)
    C, G = net.C.sum(), net.g_amb.sum()
    tau = C / G
    table = TableProfile([0, 10, 25, 40], [40.0, 10.0, 0.0], True)
    resp_u = profiles.step_response_fvm(u, 12.5)
    peak, valley = profiles.wave_response(resp_u, 0, table)
    # Exact periodic solution of C T' = P(t) - G T by marching until it repeats
    dt, T = 0.01, 40.0
    steps = int(T / dt)
    power = table.mean_power(np.arange(steps) * dt, np.arange(1, steps + 1) * dt)
    x, series = 0.0, None
    for cycle in range(40):
        series = np.empty(steps)
        for k in range(steps):
            x = x + dt * (power[k] - G * x) / C
            series[k] = x
    assert peak == pytest.approx(series.max(), rel=0.01) and valley == pytest.approx(series.min(), rel=0.01)
    assert tau > 100                                                                  # A board much slower than the cycle


def test_csv_reading_writing_units_and_errors(tmp_path):
    from pcbthermal import ProfileFileError, TableProfile, read_profile_csv, write_profile_csv
    from pcbthermal.profile_io import parse_profile_csv, profile_to_csv
    t = parse_profile_csv("# note\n# repeat: no\ntime_ms;power_mw\n0;6000\n500;0\n1500;0\n")
    assert t.times == [0.0, 0.5, 1.5] and t.powers == [6.0, 0.0] and t.repeat is False
    assert parse_profile_csv("time_min,power_kw\n0,0.001\n2,0.001\n").times == [0.0, 120.0]
    # Round trip, also from a square wave
    w = SquareWave(10.0, 2.0, 0.25, 1.0)
    path = tmp_path / "w.csv"
    write_profile_csv(w, path, "U9")
    back = read_profile_csv(path)
    assert back.times == [0.0, 0.5, 2.0] and back.powers == [10.0, 1.0] and back.repeat is True
    assert "U9" in path.read_text() and profile_to_csv(back).count("\n") == 7
    for text, fragment in (("time_s,power_w\n0,1\n", "at least two rows"), ("time_s,power_w\n1,1\n2,1\n", "must be 0"),
                           ("time_s,power_w\n0,1\n0,2\n", "increasing"), ("time_s,power_w\n0,-1\n1,1\n", "not negative"),
                           ("time_s,power_w\n0,1\nx,y\n", "line 3"), ("time_xx,power_w\n0,1\n1,1\n", "unknown time unit"),
                           ("# repeat: maybe\n0,1\n1,1\n", "repeat"), ("0\n1\n", "two columns")):
        with pytest.raises(ProfileFileError, match=fragment):
            parse_profile_csv(text)
    # Project files keep tables and old square-wave files still open
    p = example_board()
    p.heaters[0].set_profile(TableProfile([0, 1, 3], [5.0, 1.0], False))
    q = problem_from_dict(json.loads(json.dumps(problem_to_dict(p))))
    assert q.heaters[0].profile.kind == "table" and q.heaters[0].profile.repeat is False and q.heaters[0].power == pytest.approx(2.333333, abs=1e-5)
    old = problem_to_dict(example_with_profiles())
    del old["heaters"][0]["profile"]["type"]
    assert problem_from_dict(old).heaters[0].profile.kind == "square"


def test_one_shot_and_repeating_tables_run_in_all_models():
    from pcbthermal import TableProfile
    p = example_board()
    p.heaters[0].set_profile(TableProfile([0, 2, 10, 30], [12.0, 5.0, 0.5], True))
    p.heaters[1].set_profile(TableProfile([0, 10, 20, 120], [0.0, 3.0, 1.5], False))
    sim = simulate(p, SolverOptions(cell_mm=2.0))
    assert [d.regime for d in sim.decisions] == ["resolved", "resolved"]
    assert sim.decisions[1].repeat is False and sim.decisions[1].oscillation > 10.0
    f = sim.profile_results["fvm"]
    assert f.windows >= 1 and f.window == pytest.approx(120.0)                     # One-shot length, a multiple of 30 s
    assert f.converged and any("one-shot" in w for w in f.warnings)
    # U2 starts at the steady state of its first power (0 W): about ambient plus the U1 average, much cooler than 60 degC
    assert f.t_heaters[1][0] < 45.0 and f.t_heaters[1].max() > f.t_heaters[1][0] + 15.0
    # After the end the last power is held: a longer fixed time settles at the steady state of the final powers
    long_run = simulate(p, SolverOptions(models=("fvm",), cell_mm=2.0,
                                         profile=ProfileOptions(duration="time", time_s=2400.0, theta=1.0)))
    assert long_run.profile_results["fvm"].t_heaters[1][-1] < long_run.profile_results["fvm"].peak
    assert simulate(p, SolverOptions(cell_mm=2.0)).profile_results["lumped"].peak == pytest.approx(f.peak, rel=0.06)


def test_common_period_is_the_least_common_multiple():
    assert profiles._common_period([2.0, 3.0]) == (6.0, True)
    assert profiles._common_period([0.1, 0.25]) == (0.5, True)
    period, exact = profiles._common_period([1.0, 2.0 ** 0.5])
    assert not exact and period == 2.0 ** 0.5 or period == 1.0 or not exact


def test_cli_profile_files_and_gui_buttons(tmp_path, capsys):
    from pcbthermal import cli
    path = tmp_path / "e.pcbt.json"
    cli.main(["example", str(path), "--which", "example"])
    csv = tmp_path / "u1.csv"
    csv.write_text("# repeat: yes\ntime_s,power_w\n0,12\n2,5\n10,0.5\n30,0.5\n")
    assert cli.main(["run", str(path), "--model", "fvm", "--cell-mm", "2", "--out", str(tmp_path / "o"), "--no-plots",
                     "--profile", f"U1={csv}", "--duration", "cycles", "--cycles", "3"]) == 0
    assert "resolved" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        cli.main(["run", str(path), "--profile", f"nobody={csv}"])
    # The examples folder works end to end
    import importlib.util, pathlib
    root = pathlib.Path(__file__).resolve().parent.parent / "examples" / "csv_profiles"
    for name in ("u1_motor_driver_cycle", "u2_regulator_startup", "u2_pwm_1khz"):
        from pcbthermal import read_profile_csv
        prof = read_profile_csv(root / "profiles" / f"{name}.csv")
        assert prof.average() > 0
    assert read_profile_csv(root / "profiles" / "u2_pwm_1khz.csv").average() == pytest.approx(1.5)


def test_analytic_step_response_animation_matches_the_fvm():
    from pcbthermal import analytic
    p = example_board()
    a = analytic.solve_transient(p, 120.0, n_out=20, cell_mm=2.0)
    f = fvm.solve_transient(p, 120.0, n_out=20, cell_mm=2.0)
    assert a.times[0] == 0.0 and a.t_max[0] == pytest.approx(25.0) and len(a.times) == len(f.times)
    # With the per-heater calibration of the smeared vias the whole curve follows the FVM within 2.5 degC (10 degC without it)
    assert np.max(np.abs(a.t_max - f.t_max)) < 2.5
    assert a.t_max[-1] == pytest.approx(f.t_max[-1], rel=0.03)
    assert a.frames.shape[1] == f.frames.shape[1]
    assert np.all(np.diff(a.t_max) >= -1e-9)                                    # Monotone heating
    assert a.steady_t_max > a.t_max[-1]
