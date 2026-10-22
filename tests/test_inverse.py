"""!
@file test_inverse.py
@brief Power from a measured temperature: the forward model reproduces the measurement, with constant and computed heat transfer coefficients.
"""

import pytest

from pcbthermal import Problem, SolverOptions, simulate
from pcbthermal.inverse import power_from_temperature, power_from_theta


def part(power=2.0, h_mode="manual", theta=5.0):
    """!
    @brief A two-layer board with a part and a second heater.
    @param power Power of the part in W.
    @param h_mode "manual" or "computed".
    @param theta Junction-to-pad resistance in K/W.
    @return Problem.
    """
    p = Problem.new(60, 60, 2)
    p.board.h_mode = h_mode
    p.add_zone(1, rect=(5, 5, 55, 55))
    p.add_zone(2, rect=(5, 5, 55, 55))
    p.add_heater(1, power, rect=(27, 27, 33, 33), name="Q1", theta=theta)
    p.add_heater(1, 1.0, rect=(10, 10, 14, 14), name="Q2")
    return p


@pytest.mark.parametrize("point", ["max", "mean", "ring", "junction", "top"])
def test_the_recovered_power_reproduces_the_measurement(point):
    truth = part(power=3.3)
    row = simulate(truth, SolverOptions(models=("fvm",), cell_mm=1.0)).heater_rows()[0]
    measured = {"max": row["t_max"], "mean": row["t_mean"], "ring": row["t_ring"], "junction": row["t_junction"], "top": row["t_junction"] - 1.5 * 3.3}[point]
    out = power_from_temperature(part(power=1.0), 0, measured, point=point, cell_mm=1.0, psi_jt=1.5)
    assert out["power_w"] == pytest.approx(3.3, rel=1e-3)
    if point in ("mean", "ring"):                         # The hottest point can move with the power when another heater is near: only then it is not affine
        assert out["linear"] and out["runs"] == 4                  # Two runs to build the line, one to check it, one for the report of the temperatures


def test_computed_convection_is_not_linear_and_still_converges():
    truth = part(power=3.3, h_mode="computed")
    row = simulate(truth, SolverOptions(models=("fvm",), cell_mm=1.0)).heater_rows()[0]
    out = power_from_temperature(part(power=1.0, h_mode="computed"), 0, row["t_max"], point="max", cell_mm=1.0)
    assert out["power_w"] == pytest.approx(3.3, rel=2e-3) and not out["linear"] and out["runs"] > 3


def test_ambient_of_the_measurement_and_errors():
    p = part(power=2.0)
    hot = simulate(p, SolverOptions(models=("fvm",), cell_mm=1.0)).heater_rows()[0]["t_max"]
    a = power_from_temperature(p, 0, hot + 10.0, point="max", ambient_c=35.0, cell_mm=1.0)       # A warmer room: the same rise
    assert a["power_w"] == pytest.approx(2.0, rel=1e-3)
    with pytest.raises(ValueError):
        power_from_temperature(p, 0, 20.0, cell_mm=1.0)                           # Below the ambient
    with pytest.raises(ValueError):
        power_from_temperature(p, 5, 60.0, cell_mm=1.0)
    with pytest.raises(ValueError):
        power_from_temperature(part(theta=0.0), 0, 60.0, point="junction", cell_mm=1.0)
    assert power_from_theta(100.0, 80.0, 10.0) == pytest.approx(2.0)
    with pytest.raises(ValueError):
        power_from_theta(70.0, 80.0, 10.0)


def test_the_top_of_the_package_needs_theta_and_depends_on_the_board_and_psi():
    """T_top = T_board,max + (theta - psi_JT) P: no theta is refused; a board with less copper gives a lower power for the same top temperature (the board is worse
    per watt, so fewer watts explain the reading); a larger psi_JT, which lowers the top temperature per watt, gives more power."""
    truth = part(power=3.0)
    row = simulate(truth, SolverOptions(models=("fvm",), cell_mm=1.0)).heater_rows()[0]
    t_top = row["t_junction"] - 1.5 * 3.0
    with pytest.raises(ValueError, match="theta"):
        power_from_temperature(part(theta=0.0), 0, t_top, point="top", cell_mm=1.0, psi_jt=1.5)
    with pytest.raises(ValueError, match="negative"):
        power_from_temperature(part(), 0, t_top, point="top", cell_mm=1.0, psi_jt=-1.0)
    poor = part()
    poor.zones = poor.zones[:1]                                              # Only the top copper: worse spreading to the bottom face
    assert power_from_temperature(poor, 0, t_top, point="top", cell_mm=1.0, psi_jt=1.5)["power_w"] < 3.0
    low = power_from_temperature(part(), 0, t_top, point="top", cell_mm=1.0, psi_jt=1.0)["power_w"]
    high = power_from_temperature(part(), 0, t_top, point="top", cell_mm=1.0, psi_jt=2.0)["power_w"]
    assert low < 3.0 < high


def test_power_band_orders_best_nominal_worst_and_the_sources_add_in_quadrature():
    from pcbthermal.inverse import power_band
    truth = part(power=3.0)
    row = simulate(truth, SolverOptions(models=("fvm",), cell_mm=1.0)).heater_rows()[0]
    t_top = row["t_junction"] - 1.5 * 3.0
    out = power_band(part(power=1.0), 0, t_top, point="top", cell_mm=1.0, psi_jt=1.5)
    assert out["power_w"] == pytest.approx(3.0, rel=1e-3)                                  # The nominal is the plain calculator
    assert out["best_w"] < out["power_w"] < out["worst_w"]
    names = [c["factor"] for c in out["contributions"]]
    assert names == ["copper", "heat transfer", "θ junction-pad", "ψJT", "reading"]
    for c in out["contributions"]:
        assert c["low_w"] <= out["power_w"] + 1e-9 <= c["high_w"] + 2e-9
    down = sum((out["power_w"] - c["low_w"]) ** 2 for c in out["contributions"]) ** 0.5
    up = sum((c["high_w"] - out["power_w"]) ** 2 for c in out["contributions"]) ** 0.5
    assert out["best_w"] == pytest.approx(out["power_w"] - down) and out["worst_w"] == pytest.approx(out["power_w"] + up)
    # A board point needs neither theta nor psi_JT: those two sources are not in its band; a bigger uncertainty widens it
    ring = power_band(part(power=1.0), 0, row["t_ring"], point="ring", cell_mm=1.0)
    assert [c["factor"] for c in ring["contributions"]] == ["copper", "heat transfer", "reading"]
    wide = power_band(part(power=1.0), 0, row["t_ring"], point="ring", cell_mm=1.0, uncertainty={"copper_pct": 50.0, "h_pct": 60.0})
    assert wide["worst_w"] - wide["best_w"] > ring["worst_w"] - ring["best_w"]
    # More copper means a lower board resistance: more watts for the same reading
    copper = next(c for c in ring["contributions"] if c["factor"] == "copper")
    assert copper["high_w"] > ring["power_w"] > copper["low_w"]
