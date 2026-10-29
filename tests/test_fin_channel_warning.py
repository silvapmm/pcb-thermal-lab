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
    # Ra_b at 20 degC ambient for the block excess named in the INTEGRATION table: 40 K gives 70.4 at 5.5 mm, not the "about 62" written there
    assert fin_channel_rayleigh(5.5e-3, 40e-3, 40.0, 20.0) == pytest.approx(70.4, rel=0.01)
    # The 62.4 and 11.9 of research/fin-channel README 5 table A are at the board's 25 degC ambient and the mean wall excess of the channel run
    # (37.4 K at 5.5 mm, 46.6 K at 3.5 mm, convection-only plate coefficient): the same function reproduces them
    assert fin_channel_rayleigh(5.5e-3, 40e-3, 37.37, 25.0) == pytest.approx(62.4, rel=0.005)
    assert fin_channel_rayleigh(3.5e-3, 40e-3, 46.6, 25.0) == pytest.approx(11.9, rel=0.005)
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
    assert len(w) == 1 and "up to 71 % less" in w[0] and "Fins down on a horizontal board" in w[0]
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


def test_a_block_cut_at_the_outline_reads_the_excess_of_the_block_on_the_board():
    # An L-shaped board cuts a quarter of the block away; the cut cells hold the ambient temperature and must not lower the mean excess (review:
    # the unweighted mean over the polygon read 27 K for a block 35 K above the air)
    import numpy as np
    p = board((15.0, 1.5, 7.0))
    p.board.outline = np.array([[0, 0], [0.06, 0], [0.06, 0.02], [0.03, 0.02], [0.03, 0.04], [0, 0.04]])
    sim = simulate(p, SolverOptions(models=("fvm",), cell_mm=1.0))
    bt, cov = sim.reference.arrays["block_T"][0], sim.reference.arrays["block_cov"][0]
    mean = float(((bt - sim.reference.ambient) * cov).sum() / cov.sum())
    w = channel_warnings(sim)
    assert len(w) == 1 and f"block {mean:.0f} K above the air" in w[0] and mean > 33


def test_the_3d_solid_uses_its_own_block_temperature():
    # The FVM, FDM and 3D solid give the check their own block temperatures; only the Lumped and Analytic use the auxiliary FVM run
    import pcbthermal.api as api
    seen = []
    saved = api.check_fin_channels
    api.check_fin_channels = lambda problem, result=None: seen.append(result) or []
    try:
        sims = {m: run(5.5, model=m) for m in ("solid3d", "fdm", "lumped")}
    finally:
        api.check_fin_channels = saved
    # The auxiliary FVM run is a simulation of its own and calls the check too, so look for the result of every model among the calls
    assert any(r is sims["solid3d"].reference for r in seen) and any(r is sims["fdm"].reference for r in seen)
    assert not any(r is sims["lumped"].reference for r in seen) and all(r is not None and "block_T" in r.arrays for r in seen)


def test_the_text_depends_on_the_orientation_and_the_face_and_bounds_the_loss_of_a_very_close_channel():
    # Ra_b below 14 gives the loss as a bound; Ra_b above it states it. The last sentence follows Board.orientation and the face of the block
    def text(orientation, face_up, gap=3.5):
        p = board((15.0, 1.5, gap + 1.5))
        p.heaters[0].power = 3.0
        p.board.orientation = orientation
        if face_up:
            p.heatsinks[0].layer = 0                                        # the test block is on the bottom layer (fins down) unless moved
        sim = simulate(p, SolverOptions(models=("fvm",), cell_mm=1.0))
        return channel_warnings(sim)

    up = text("horizontal", True)
    assert len(up) == 1 and "Fins up on a horizontal board" in up[0] and "up to" in up[0]
    vertical = text("vertical", True)
    assert len(vertical) == 1 and vertical[0].endswith("Valid for a vertical board.")
    down = text("horizontal", False)
    assert len(down) == 1 and "Fins down on a horizontal board" in down[0]
    moderate = text("horizontal", False, gap=5.5)
    assert len(moderate) == 1 and "up to" not in moderate[0] and "% less than a plate" in moderate[0]
