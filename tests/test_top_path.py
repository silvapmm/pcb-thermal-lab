#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_top_path.py
@brief The split of the power of a part with a top path (a heatsink on the package) is the root of a scalar equation, also on small pads where a fixed-point loop diverges.
@details Before the correction `api._solve_with_tc` iterated P_b <- P - p_top(T_max(P_b)), whose slope -R_b/(R_top + theta) exceeds 1 when the board under the part
         resists more than the top path (a small pad): the iteration oscillated, stopped after 80 iterations 17 to 58 K below the operating point and warned about a thermal
         runaway. These tests check the operating point against independent references (a closed form on a linear board, a Brent root on the board alone, and a re-solve of
         the plain board with the heat that the result says it received).
"""

import copy
import os
import sys

import pytest
from scipy.optimize import brentq

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "research", "component-heatsink", "scripts"))

import component_study as cs  # noqa: E402
from pcbthermal import Problem, SolverOptions, simulate  # noqa: E402
from pcbthermal import api  # noqa: E402
from pcbthermal.analysis import part_split  # noqa: E402

MOSFET = cs.PARTS["MOSFET CSD17308Q3 (SON 3.3x3.3)"]


def mosfet_board(pad_mm, interface=0.5, theta_sa=12.0):
    """!
    @brief The board of the component study with the MOSFET and a top path (theta_JC(top) 30 K/W, paste, clip-on heatsink).
    @param pad_mm Side of the copper pad in mm.
    @param interface Interface resistance in K cm2/W.
    @param theta_sa Heatsink resistance in K/W.
    @return Problem (computed heat transfer coefficients).
    """
    p = cs.part_board(MOSFET, pad_mm)
    h = p.heaters[0]
    h.power, h.theta, h.theta_jc_top, h.interface, h.theta_sa = MOSFET["p"], MOSFET["th"], MOSFET["thtop"], interface, theta_sa
    return p


def board_tmax(problem, p_board, options):
    """!
    @brief Hottest board point under the first part when the board alone receives p_board (top path off).
    @param problem Problem with a top path (copied, not modified).
    @param p_board Power into the board in W.
    @param options SolverOptions.
    @return Temperature in degC.
    """
    q = copy.deepcopy(problem)
    q.heaters[0].power, q.heaters[0].theta_sa = p_board, 0.0
    return simulate(q, options).heater_rows()[0]["t_max"]


def test_small_pad_reaches_the_operating_point_and_not_a_thermal_runaway_warning():
    # 8 mm pad: R_b / (R_top + theta) = 2, the old loop stopped at 33.2 degC; the operating point is 90.9 degC (exact root, node prototype 90.7)
    p = mosfet_board(8.0)
    opts = SolverOptions(models=("fvm",), cell_mm=0.5)
    sim = simulate(p, opts)
    row, h = sim.heater_rows()[0], p.heaters[0]
    amb = p.board.ambient
    # Independent reference: Brent's method on g(P_b) = P_b - P + p_top(T_max(P_b)) with the board solved alone
    power = MOSFET["p"]
    root = brentq(lambda pb: pb - power + part_split(h, board_tmax(p, pb, opts), power, amb)[1], 1e-6, power, xtol=1e-5)
    tj_exact = part_split(h, board_tmax(p, root, opts), power, amb)[0]
    assert row["t_junction"] == pytest.approx(tj_exact, abs=0.1)
    assert row["t_junction"] == pytest.approx(90.9, abs=0.1)
    # Energy and the series-parallel closure
    assert row["power_top_w"] + row["power_board_w"] == pytest.approx(power)
    assert row["t_junction"] - amb == pytest.approx(h.top_resistance() * row["power_top_w"], rel=1e-6)
    assert row["power_top_w"] > 0.5 * power                                   # Most of the heat goes up on a small pad
    # No misleading message and the solve count is small
    w = sim.results["fvm"].warnings
    assert not any("runaway" in x or "did not settle" in x or "did not converge" in x for x in w)
    assert sim.results["fvm"].extras["top_path_solves"] <= 12


def test_linear_board_closed_form_where_the_fixed_point_loop_diverges():
    # Constant h: the board is affine in P_b, T_max = T0 + R_b P_b, so the operating point has a closed form from part_split's algebra
    p = mosfet_board(8.0)
    p.board.h_mode, p.board.h_top, p.board.h_bottom = "manual", 12.0, 9.0
    opts = SolverOptions(models=("fvm",), cell_mm=1.0)
    t0, t1 = board_tmax(p, 0.0, opts), board_tmax(p, 1.0, opts)
    r_b = t1 - t0
    h = p.heaters[0]
    ratio = r_b / (h.top_resistance() + h.theta)
    assert ratio > 1.0                                                       # The old loop's slope is minus this: it diverges
    power, amb, theta, r_top = MOSFET["p"], p.board.ambient, h.theta, h.top_resistance()
    # Tj - Ta = (T_max - Ta + P theta)/(1 + theta/R_top) with T_max = t0 + R_b (P - p_top), p_top = (Tj - Ta)/R_top  ->  linear in p_top
    # p_top (R_top + theta + R_b) = (t0 - amb) + P (theta + R_b)
    p_top = ((t0 - amb) + power * (theta + r_b)) / (r_top + theta + r_b)
    tj = amb + r_top * p_top
    row = simulate(p, opts).heater_rows()[0]
    assert row["power_top_w"] == pytest.approx(p_top, abs=1e-3)
    assert row["t_junction"] == pytest.approx(tj, abs=0.02)


def test_several_parts_with_top_paths_share_one_board():
    # Two parts close to each other on a small board; their splits interact through the board
    p = Problem.new(40, 40, 2)
    p.board.h_mode, p.board.h_top, p.board.h_bottom = "manual", 12.0, 9.0
    for layer in (1, 2):
        p.add_zone(layer, rect=(12, 12, 28, 28))
    for k, (x, power) in enumerate(((17.0, 2.0), (23.0, 1.5))):
        p.add_heater(1, power, rect=(x - 2.0, 18.0, x + 2.0, 22.0), name=f"U{k + 1}", theta=4.5, theta_jc_top=30.0, theta_sa=12.0, interface=0.5)
    opts = SolverOptions(models=("fvm",), cell_mm=0.5)
    sim = simulate(p, opts)
    rows = sim.heater_rows()
    for row, h in zip(rows, p.heaters):
        assert row["power_top_w"] + row["power_board_w"] == pytest.approx(row["power_w"])
        assert row["t_junction"] - p.board.ambient == pytest.approx(h.top_resistance() * row["power_top_w"], rel=1e-6)
    # Independent check of the coupled root: the plain board given exactly the heat the result says it received reproduces the hottest points
    q = copy.deepcopy(p)
    for h, row in zip(q.heaters, rows):
        h.power, h.theta_sa = row["power_board_w"], 0.0
    plain = simulate(q, opts).heater_rows()
    for a, b in zip(plain, rows):
        assert a["t_max"] == pytest.approx(b["t_max"], abs=0.01)
    assert not any("did not converge" in x or "runaway" in x for x in sim.results["fvm"].warnings)


def split_residuals(problem, sim, options):
    """!
    @brief Independent check of a coupled split: re-solve the plain board with the heat the result says it received and evaluate every part's equation.
    @param problem Problem with top paths (copied, not modified).
    @param sim Simulation of that problem.
    @param options SolverOptions used for the simulation.
    @return Tuple (list of |g_i|/P_i, list of |T_max plain - T_max result| in K).
    """
    rows = sim.heater_rows()
    q = copy.deepcopy(problem)
    for h, row in zip(q.heaters, rows):
        h.power, h.theta_sa = row["power_board_w"], 0.0                        # The top path off: the board alone gets exactly that heat
    plain = simulate(q, options).heater_rows()
    g = [abs(row["power_board_w"] - row["power_w"] + part_split(h, pl["t_max"], row["power_w"], problem.board.ambient)[1]) / row["power_w"]
         for h, row, pl in zip(problem.heaters, rows, plain)]
    return g, [abs(pl["t_max"] - row["t_max"]) for row, pl in zip(rows, plain)]


def test_three_coupled_parts_on_one_small_pad_with_computed_coefficients():
    # Three parts with different powers 4 mm apart on one 12 mm pad, computed h: Broyden on three coupled unknowns (the middle part sends 99.6 % up, close to the clip)
    p = Problem.new(40, 40, 2)
    for layer in (1, 2):
        p.add_zone(layer, rect=(14, 14, 26, 26))
    for k, power in enumerate((1.5, 1.0, 1.2)):
        x = 16.0 + 4.0 * k
        p.add_heater(1, power, rect=(x - 1.6, 18.4, x + 1.6, 21.6), name=f"U{k + 1}", theta=4.5, theta_jc_top=30.0, theta_sa=12.0, interface=0.5)
    opts = SolverOptions(models=("fvm",), cell_mm=0.5)
    sim = simulate(p, opts)
    g, dt = split_residuals(p, sim, opts)
    assert max(g) < 1e-4 and max(dt) < 0.01
    assert all(0.0 < row["power_top_w"] < row["power_w"] for row in sim.heater_rows())    # Every split inside (0, P): the coupled root, not a clip
    assert not any("did not converge" in x or "runaway" in x or "did not settle" in x for x in sim.results["fvm"].warnings)


def test_a_part_heated_by_its_neighbour_sends_all_its_heat_up_and_the_others_still_split():
    # A 4 W part without a top path heats the board under a 0.02 W part with a strong top path above that part's own top path:
    # part_split clips its top heat at P (the board does not feed the part), so its root is P_b = 0; a third part farther away splits normally
    p = Problem.new(40, 40, 2)
    for layer in (1, 2):
        p.add_zone(layer, rect=(13, 13, 27, 27))
        p.add_zone(layer, rect=(28, 28, 38, 38))
    p.add_heater(1, 4.0, rect=(14.4, 18.4, 17.6, 21.6), name="hot", theta=4.5)
    p.add_heater(1, 0.02, rect=(18.4, 18.4, 21.6, 21.6), name="weak", theta=4.5, theta_jc_top=0.5, theta_sa=0.5)
    p.add_heater(1, 0.5, rect=(31.4, 31.4, 34.6, 34.6), name="far", theta=4.5, theta_jc_top=30.0, theta_sa=200.0, interface=0.5)
    opts = SolverOptions(models=("fvm",), cell_mm=0.5)
    sim = simulate(p, opts)
    hot, weak, far = sim.heater_rows()
    assert hot["power_top_w"] == 0.0
    assert weak["power_board_w"] == pytest.approx(0.0, abs=1e-6)                         # Clipped: all its heat goes up
    assert weak["t_junction"] == pytest.approx(weak["t_max"])                             # ... and the junction sits at the board temperature
    assert 0.0 < far["power_top_w"] < far["power_w"]
    g, dt = split_residuals(p, sim, opts)
    assert max(g) < 1e-4 and max(dt) < 0.01
    assert not any("did not converge" in x for x in sim.results["fvm"].warnings)


def test_power_coefficient_with_a_top_path_on_a_small_pad():
    # The power loop goes around the top-path solve: P = P0 (1 + tc (Tj - 25)) must hold at the end, with the split consistent
    p = mosfet_board(8.0)
    p.board.h_mode, p.board.h_top, p.board.h_bottom = "manual", 12.0, 9.0
    h = p.heaters[0]
    h.power_tc = 0.002
    sim = simulate(p, SolverOptions(models=("fvm",), cell_mm=1.0))
    row = sim.heater_rows()[0]
    assert row["power_w"] == pytest.approx(MOSFET["p"] * (1 + 0.002 * (row["t_junction"] - 25.0)), rel=1e-4)
    assert row["power_top_w"] + row["power_board_w"] == pytest.approx(row["power_w"])
    assert row["t_junction"] - p.board.ambient == pytest.approx(h.top_resistance() * row["power_top_w"], rel=1e-6)
    assert not sim.results["fvm"].extras["thermal_runaway"]


def test_a_split_that_does_not_converge_is_not_called_a_thermal_runaway(monkeypatch):
    real = api._top_path_split

    def failing(*a, **k):
        # Same answer, but flagged as not converged
        res, hh, board, n, _ = real(*a, **k)
        return res, hh, board, n, False

    monkeypatch.setattr(api, "_top_path_split", failing)
    p = mosfet_board(25.0)
    sim = simulate(p, SolverOptions(models=("fvm",), cell_mm=1.0))
    w = sim.results["fvm"].warnings
    assert any("top-path split did not converge" in x for x in w)
    assert not any("runaway" in x for x in w)
