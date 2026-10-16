"""!
@file test_profiles.py
@brief Power profiles: square wave, average-or-resolve decision, time simulation in the three models.
"""

import json

import numpy as np
import pytest

from pcbthermal import Problem, SolverOptions, SquareWave, fvm, lumped, analytic, profiles, simulate
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


def test_fvm_matches_the_exact_rc_response_of_a_uniform_board():
    # One layer, a heater over the whole board, insulated edges: the temperature is uniform and obeys C T' = P(t) - G T
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
    assert any("smeared" in w for w in sim.warnings)                          # The analytic transient says what it ignores


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
