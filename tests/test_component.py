"""!
@file test_component.py
@brief The junction of a part: theta in the worst case, the limit and its margin, the power limit, the ring temperature with psi_JB and the power temperature coefficient.
"""

import numpy as np
import pytest

from pcbthermal import Problem, SolverOptions, analysis, fvm, simulate
from pcbthermal.model import PACKAGE_THETA, problem_from_dict, problem_to_dict


def part(power=2.0, theta=4.5, **kw):
    """!
    @brief A 60 x 60 mm, 2-layer board with copper on both faces, constant h, and a 4 x 4 mm part at the centre.
    @param power Power in W.
    @param theta Junction-to-pad resistance in K/W.
    @param kw Further arguments of Problem.add_heater.
    @return Problem.
    """
    p = Problem.new(60, 60, 2)
    p.board.h_mode = "manual"
    p.board.h_top, p.board.h_bottom = 15.0, 10.0
    p.add_zone(1, rect=(5, 5, 55, 55))
    p.add_zone(2, rect=(5, 5, 55, 55))
    p.add_heater(1, power, rect=(28, 28, 32, 32), name="Q1", theta=theta, **kw)
    return p


def test_junction_is_the_hottest_board_point_plus_p_theta_and_the_board_does_not_change():
    plain, with_theta = part(theta=0.0), part(theta=4.5)
    a, b = fvm.solve_steady(plain, 0.5), fvm.solve_steady(with_theta, 0.5)
    assert a.t_max == pytest.approx(b.t_max, abs=1e-9)                  # Worst case: the board sees the same power
    row = analysis.heater_stats(b, with_theta)[0]
    assert row["t_junction"] == pytest.approx(row["t_max"] + 2.0 * 4.5)
    assert analysis.heater_stats(a, plain)[0]["t_junction"] is None


def test_limit_margin_power_limit_and_ring():
    p = part(tj_max=150.0, psi_jb=6.0)
    r = fvm.solve_steady(p, 0.5)
    row = analysis.heater_stats(r, p)[0]
    assert row["margin_k"] == pytest.approx(150.0 - row["t_junction"])
    # Linear board: the power limit brings the junction exactly to the limit
    q = part(power=row["p_limit_w"], tj_max=150.0)
    assert analysis.heater_stats(fvm.solve_steady(q, 0.5), q)[0]["t_junction"] == pytest.approx(150.0, abs=1e-6)
    assert row["t_ring"] < row["t_max"]                                  # The ring is cooler than the hottest point under the part
    assert row["t_junction_psi"] == pytest.approx(row["t_ring"] + 2.0 * 6.0)
    coarse = analysis.heater_stats(fvm.solve_steady(p, 4.0), p)[0]
    assert coarse["t_ring"] is None or coarse["t_ring"] > 25.0


def test_power_temperature_coefficient_matches_the_closed_form_and_runs_away():
    base = part()
    s0 = simulate(base, SolverOptions(models=("fvm",), cell_mm=1.0))
    r_total = (s0.heater_rows()[0]["t_junction"] - 25.0) / 2.0          # K/W from the junction to the ambient at constant coefficients
    for tc in (0.0033, 0.005):
        p = part(power_tc=tc)
        s = simulate(p, SolverOptions(models=("fvm", "lumped", "analytic"), cell_mm=1.0))
        row = s.heater_rows()[0]
        closed = 25.0 + 2.0 * r_total / (1.0 - tc * 2.0 * r_total)       # dT = P0 R (1 + tc dT)  ->  dT = P0 R / (1 - tc P0 R)
        assert row["t_junction"] == pytest.approx(closed, abs=0.05)
        assert row["power_w"] == pytest.approx(2.0 * (1 + tc * (row["t_junction"] - 25.0)), rel=1e-4)
        assert s.reference.extras["power_tc_iterations"] > 1 and not s.reference.extras["thermal_runaway"]
        assert abs(s.reference.balance_error) < 1e-9 and s.reference.power_in == pytest.approx(row["power_w"], rel=1e-6)
        assert set(s.power_used) == {"fvm", "lumped", "analytic"}
    run = simulate(part(power_tc=0.03), SolverOptions(models=("fvm",), cell_mm=1.0))
    assert run.reference.extras["thermal_runaway"] == 1.0
    assert any("thermal runaway" in w for w in run.warnings)


def test_warnings_for_the_limit_and_for_an_implausible_theta():
    over = simulate(part(power=4.0, tj_max=100.0), SolverOptions(models=("fvm",), cell_mm=1.0))
    assert any("above its limit" in w and "power limit" in w for w in over.warnings)
    ok = simulate(part(power=1.0, tj_max=200.0), SolverOptions(models=("fvm",), cell_mm=1.0))
    assert not any("above its limit" in w for w in ok.warnings)
    wrong = simulate(part(power=1.0, theta=65.0), SolverOptions(models=("fvm",), cell_mm=1.0))      # A theta_JA entered by mistake
    assert any("junction-to-pad" in w for w in wrong.warnings)
    assert "limit 200" in ok.report() or ok.report().count("Heater Q1") == 1
    with_limit = simulate(part(tj_max=150.0, psi_jb=5.0), SolverOptions(models=("fvm",), cell_mm=1.0)).report()
    assert "margin" in with_limit and "psi_JB" in with_limit and "board ring" in with_limit


def test_files_and_the_package_presets():
    p = part(tj_max=150.0, psi_jb=6.0, power_tc=0.004)
    q = problem_from_dict(problem_to_dict(p))
    h = q.heaters[0]
    assert (h.theta, h.tj_max, h.psi_jb, h.power_tc) == (4.5, 150.0, 6.0, 0.004)
    d = problem_to_dict(part())
    assert "tj_max_c" not in d["heaters"][0] and d["heaters"][0]["theta_k_per_w"] == 4.5
    old = problem_to_dict(part())
    old["heaters"][0]["theta_jb_k_per_w"] = old["heaters"][0].pop("theta_k_per_w")        # The key of files saved before the rename
    assert problem_from_dict(old).heaters[0].theta == 4.5
    with pytest.raises(ValueError):
        part(theta=-1.0).validate()
    with pytest.raises(ValueError):
        part(power_tc=0.5).validate()
    assert len(PACKAGE_THETA) >= 6 and all(th > 0 for _, th in PACKAGE_THETA)
    # The datasheet case of the study: a 2 W MOSFET with 4.5 K/W adds 9 K to the board point under it
    r = fvm.solve_steady(part(), 0.5)
    assert analysis.heater_stats(r, part())[0]["t_junction"] - r.t_max == pytest.approx(9.0)
