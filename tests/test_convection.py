"""!
@file test_convection.py
@brief Computed heat transfer coefficients: correlations, Picard iteration, settings and interfaces.
"""

import copy
import json

import pytest

from pcbthermal import SolverOptions, convection, simulate
from pcbthermal.examples import example_board
from pcbthermal.model import problem_from_dict, problem_to_dict, reference_problem


def test_air_properties_match_textbook_values():
    # Incropera tables: 300 K k = 0.0263, nu = 15.89e-6, Pr = 0.707; 400 K k = 0.0338, nu = 25.9e-6, Pr = 0.690
    a = convection.air_properties(26.85)
    assert a["k"] == pytest.approx(0.0263, rel=0.01) and a["nu"] == pytest.approx(15.89e-6, rel=0.03)
    assert a["pr"] == pytest.approx(0.707, rel=0.01) and a["beta"] == pytest.approx(1 / 300.0, rel=1e-3)
    b = convection.air_properties(126.85)
    assert b["k"] == pytest.approx(0.0338, rel=0.01) and b["nu"] == pytest.approx(25.9e-6, rel=0.02)


def test_correlations_have_the_expected_ordering_and_trends():
    length = 0.1 * 0.08 / (2 * 0.18)
    up, ra = convection.h_natural_horizontal(75.0, 25.0, length, True)
    down, _ = convection.h_natural_horizontal(75.0, 25.0, length, False)
    assert 3.0 < down < up < 15.0                                           # Facing up cools better than down
    assert convection.h_natural_horizontal(125.0, 25.0, length, True)[0] > up   # Hotter surface, larger h
    assert convection.h_natural_horizontal(25.0, 75.0, length, True)[0] == pytest.approx(down, rel=0.02)  # Cold plate: reversed
    assert convection.h_forced(60.0, 25.0, 0.0, 0.1) == 0.0
    assert convection.h_forced(60.0, 25.0, 5.0, 0.1) > convection.h_forced(60.0, 25.0, 1.0, 0.1) > 5.0
    assert convection.h_radiation(75.0, 25.0, 0.0) == 0.0
    # Linearised radiation against the exact difference eps sigma (Ts^4 - Ta^4) / (Ts - Ta)
    exact = 0.9 * convection.SIGMA * (348.15 ** 4 - 298.15 ** 4) / 50.0
    assert convection.h_radiation(75.0, 25.0, 0.9) == pytest.approx(exact, rel=1e-9)
    # Vertical plate, Churchill and Chu: a 0.1 m plate with 50 K is about 5 to 6 W/m2K in air
    assert 4.0 < convection.h_natural_vertical(75.0, 25.0, 0.1)[0] < 8.0


def test_board_h_adds_radiation_scales_convection_and_blends_forced():
    b = reference_problem().board
    b.h_mode = "computed"
    ht, hb, info = convection.board_h(b, 70.0, 70.0)
    assert ht == pytest.approx(info["top"]["convection"] + info["top"]["radiation"])
    b2 = copy.deepcopy(b)
    b2.h_calibration = 2.0
    ht2, _, info2 = convection.board_h(b2, 70.0, 70.0)
    assert info2["top"]["convection"] == pytest.approx(2.0 * info["top"]["convection"])
    assert info2["top"]["radiation"] == pytest.approx(info["top"]["radiation"])      # The multiplier never touches radiation
    b3 = copy.deepcopy(b)
    b3.air_speed = 2.0
    assert convection.board_h(b3, 70.0, 70.0)[0] > ht
    b4 = copy.deepcopy(b)
    b4.emissivity_top = 0.0
    assert convection.board_h(b4, 70.0, 70.0)[0] == pytest.approx(info["top"]["convection"])


def test_computed_mode_is_a_fixed_point_and_conserves_energy():
    p = example_board()
    p.board.h_mode = "computed"
    sim = simulate(p, SolverOptions(cell_mm=2.0))
    for name, r in sim.results.items():
        ht, hb = sim.h_used[name]
        # The coefficients are those of the converged face temperatures
        nt, nb, _ = convection.board_h(p.board, r.layer_mean[0], r.layer_mean[-1])
        assert nt == pytest.approx(ht, abs=0.05) and nb == pytest.approx(hb, abs=0.05)
        assert abs(r.balance_error) < 1e-9
        assert 2 <= r.extras["h_iterations"] <= 8
    # The three models agree on the coefficients and on the temperature as they do with typed values
    tmax = {k: r.t_max for k, r in sim.results.items()}
    assert tmax["lumped"] == pytest.approx(tmax["fvm"], rel=0.04) and tmax["analytic"] == pytest.approx(tmax["fvm"], rel=0.04)
    assert sim.effective_problem.board.h_mode == "manual"
    assert sim.effective_problem.board.h_top == pytest.approx(sim.h_used["fvm"][0])
    assert "computed from correlations" in sim.report()


def test_computed_h_responds_to_power_air_speed_and_multiplier():
    def tmax(power_scale=1.0, **board):
        p = example_board()
        for h in p.heaters:
            h.power *= power_scale
        p.board.h_mode = "computed"
        for k, v in board.items():
            setattr(p.board, k, v)
        return simulate(p, SolverOptions(models=("fvm",), cell_mm=2.0)).results["fvm"].t_max

    base = tmax()
    assert tmax(air_speed=2.0) < base - 5.0                                  # A fan cools
    assert tmax(h_calibration=0.8) > base                                    # Less convection, hotter
    assert tmax(emissivity_top=0.1, emissivity_bottom=0.1) > base + 5.0      # Bare surfaces radiate little
    # Hotter boards lose heat better than a constant h would say: the temperature rise grows less than the power
    rise = lambda s: tmax(s) - 25.0
    assert rise(4.0) < 4.0 * rise(1.0) * 0.95


def test_settings_roundtrip_validation_and_profiles_use_the_computed_h(tmp_path):
    p = example_board()
    p.board.h_mode, p.board.air_speed, p.board.h_calibration = "computed", 1.5, 0.9
    q = problem_from_dict(json.loads(json.dumps(problem_to_dict(p))))
    assert (q.board.h_mode, q.board.air_speed, q.board.h_calibration) == ("computed", 1.5, 0.9)
    for field, value in (("h_mode", "magic"), ("orientation", "tilted"), ("emissivity_top", 1.5), ("h_calibration", 0.0)):
        bad = example_board()
        setattr(bad.board, field, value)
        with pytest.raises(ValueError):
            bad.validate()
    from pcbthermal.examples import example_profile_board
    pp = example_profile_board()
    pp.board.h_mode = "computed"
    sim = simulate(pp, SolverOptions(models=("fvm",), cell_mm=2.0))
    assert sim.profile_results["fvm"].resolved
    # The time simulation starts from the steady state computed with the same coefficients
    r = sim.profile_results["fvm"]
    assert r.steady_average_max == pytest.approx(sim.results["fvm"].t_max, abs=0.3)


def test_cli_computed_h(tmp_path, capsys):
    from pcbthermal import cli
    path = tmp_path / "e.pcbt.json"
    cli.main(["example", str(path), "--which", "example"])
    assert cli.main(["run", str(path), "--model", "fvm", "--cell-mm", "2", "--out", str(tmp_path / "o"), "--no-plots",
                     "--air-speed", "1"]) == 0
    assert (tmp_path / "o" / "report.txt").read_text().count("computed from correlations") == 1


def test_rayleigh_warning_outside_the_fitted_range():
    # A very small heated board with almost no power sits below Ra = 1e4: the correlation is an extrapolation
    p = reference_problem(layers=2, heater_mm=5.0, power=0.01)
    p.board.h_mode = "computed"
    sim = simulate(p, SolverOptions(models=("fvm",), cell_mm=2.0))
    assert any("Rayleigh" in w for w in sim.results["fvm"].warnings)
    q = example_board()
    q.board.h_mode = "computed"
    assert not any("Rayleigh" in w for w in simulate(q, SolverOptions(models=("fvm",), cell_mm=2.0)).results["fvm"].warnings)
