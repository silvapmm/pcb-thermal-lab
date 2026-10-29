#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_fin_channel_warning.py
@brief The post-run warning about close plate fins (channel Rayleigh number Ra_b < 90) that replaced the "gap below 4 mm" rule, and the proof that it changes no result.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from pcbthermal import SolverOptions, simulate
from pcbthermal.checks import FIN_CHANNEL_RA_LIMIT, check_fin_channels, check_problem, fin_channel_fraction, fin_channel_rayleigh
from test_heatsink_part import board


def channel_warnings(sim):
    """!
    @brief The channel warnings of a simulation.
    @param sim Simulation.
    @return List of strings.
    """
    return [w for w in sim.warnings if "channel between the fins" in w]


def run(gap_mm, power=3.0, model="fvm", fin_mm=(15.0, 1.5), air_speed=0.0):
    """!
    @brief Solve the 60 x 40 mm board with a 40 x 30 mm finned block (fin pitch = gap + thickness) in one model.
    @param gap_mm Air gap between the fins in mm.
    @param power Part power in W.
    @param model Model key.
    @param fin_mm (height, thickness) of the fins in mm.
    @param air_speed Air speed in m/s.
    @return Simulation.
    """
    p = board((fin_mm[0], fin_mm[1], gap_mm + fin_mm[1]))
    p.heaters[0].power = power
    p.board.air_speed = air_speed
    return simulate(p, SolverOptions(models=(model,), cell_mm=1.0))


def test_channel_fraction_function_values_of_the_study():
    # The values of research/fin-channel INTEGRATION.md 2
    assert fin_channel_fraction(54.38) == pytest.approx(0.816, abs=5e-4)
    assert fin_channel_fraction(121.5) == pytest.approx(0.933, abs=5e-4)
    assert fin_channel_fraction(90.07) == pytest.approx(0.900, abs=5e-4)
    assert fin_channel_fraction(FIN_CHANNEL_RA_LIMIT) == pytest.approx(0.9, abs=1e-3)       # The threshold is phi = 0.9
    assert fin_channel_fraction(16.5) == pytest.approx(0.5, abs=0.01) and fin_channel_fraction(40.5) == pytest.approx(0.75, abs=0.01)


def test_rayleigh_of_the_table_cases_at_a_stated_excess():
    # Ra_b at 20 degC ambient for the block excess named in the table (the study's "about 62" had a rise of 36 K; the number moves as theta^(1/2-ish))
    assert fin_channel_rayleigh(5.5e-3, 40e-3, 40.0, 20.0) == pytest.approx(70.4, rel=0.01)
    assert fin_channel_rayleigh(6.5e-3, 40e-3, 40.0, 20.0) == pytest.approx(137.4, rel=0.01)       # The table: about 137
    assert fin_channel_rayleigh(6.5e-3, 100e-3, 20.0, 20.0) == pytest.approx(32.0, rel=0.01)       # The table: about 32
    assert fin_channel_rayleigh(20e-3, 40e-3, 40.0, 20.0) > 1e4
    assert fin_channel_rayleigh(0.0, 40e-3, 40.0, 20.0) == 0.0 and fin_channel_rayleigh(5e-3, 40e-3, 0.0, 20.0) == 0.0


@pytest.mark.parametrize("model", ["fvm", "fdm", "solid3d", "lumped", "analytic"])
def test_table_cases_in_every_model(model):
    # Gap 5.5 mm warns, 6.5 mm at 3 W (Ra_b about 100) and 20 mm do not, 3.5 mm warns with a strong loss; Lumped and Analytic through the auxiliary FVM run
    w = channel_warnings(run(5.5, model=model))
    assert len(w) == 1 and "0.79 of its coefficient" in w[0] and "21 % less" in w[0] and "27 K above the air" in w[0]
    assert channel_warnings(run(6.5, model=model)) == []
    w = channel_warnings(run(3.5, model=model))
    assert len(w) == 1 and "71 % less" in w[0] and "Valid for a vertical board" in w[0]
    assert channel_warnings(run(20.0, model=model)) == []


def test_a_cooler_block_makes_the_same_gap_warn():
    # Gap 6.5 mm at 1 W: the block is 10 K above the air, Ra_b about 39 (the weaker the buoyancy, the earlier the channel chokes)
    assert channel_warnings(run(6.5, power=3.0)) == []
    w = channel_warnings(run(6.5, power=1.0))
    assert len(w) == 1 and "26 % less" in w[0]


def test_the_old_pre_run_rule_is_gone_and_forced_air_is_not_checked():
    p = board((15.0, 1.5, 4.0))                                       # A 2.5 mm gap: the old rule fired before any run
    assert not any("channel" in w or "choke" in w for w in check_problem(p))
    assert channel_warnings(run(3.5, air_speed=2.0)) == []
    assert check_fin_channels(p, None) == []                         # No result: nothing is said


def test_no_fins_no_warning_and_no_result_changes():
    plain = simulate(board(), SolverOptions(models=("fvm",), cell_mm=1.0))
    assert channel_warnings(plain) == []
    # The warning is text only: the result of a finned block is the one of the same run with the check disabled
    import pcbthermal.api as api
    sim = run(3.5)
    saved = api.check_fin_channels
    api.check_fin_channels = lambda problem, result=None: []
    try:
        quiet = run(3.5)
    finally:
        api.check_fin_channels = saved
    assert channel_warnings(quiet) == [] and len(channel_warnings(sim)) == 1
    assert sim.reference.t_max == quiet.reference.t_max
