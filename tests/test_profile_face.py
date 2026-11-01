#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_profile_face.py
@brief The face of a part over absent copper in the curves of a power profile (profiles._FVMAdapter, _FDMAdapter): the curve of a heater is the node plus the drop over the half layer
       of laminate of the power of the step, so that the steady maxima and the end of a long on-phase equal the temperature the steady table reports for the part.
"""

import numpy as np
import pytest

from pcbthermal import Problem, analysis, fdm, fvm, profiles
from pcbthermal.model import SquareWave
from pcbthermal.profiles import ProfileOptions


def board(parts=((15.0, 1.0, 2.0),), bare=True):
    """!
    @brief A 30 x 30 mm two-layer board with a full bottom plane and parts on the top layer.
    @param parts Tuples (centre x in mm, power in W, side in mm); the centre y is 15 mm.
    @param bare True: no copper on the top layer (the parts sit on bare laminate); False: a full top layer.
    @return Problem.
    """
    p = Problem.new(30, 30, 2, 1.6, 35, ambient=25.0, h_top=10, h_bottom=10, h_side=None)
    if not bare:
        p.add_zone(1, rect=(0, 0, 30, 30))
    p.add_zone(2, rect=(0, 0, 30, 30))
    for k, (cx, w, s) in enumerate(parts):
        p.add_heater(1, w, rect=(cx - s / 2, 15 - s / 2, cx + s / 2, 15 + s / 2), name=f"U{k}")
    return p


def steady_rows(p, mod, cell):
    return analysis.heater_stats(mod.solve_steady(p, cell), p)


@pytest.mark.parametrize("adapter,mod", [(profiles._FVMAdapter, fvm), (profiles._FDMAdapter, fdm)])
def test_the_steady_maxima_and_the_start_state_are_the_steady_table(adapter, mod):
    p = board(parts=((13.0, 1.0, 2.0), (16.5, 2.0, 3.0)))
    rows = steady_rows(p, mod, 1.0)
    ad = adapter(p, 1.0)
    state, _ = ad.begin(ProfileOptions())
    hottest, under = ad.observe(state)
    assert under == pytest.approx([r["t_max"] for r in rows], abs=1e-9)
    assert ad.steady_average_max == pytest.approx(max(r["t_max"] for r in rows), abs=1e-9)
    assert hottest == pytest.approx(ad.steady_average_max, abs=1e-9)
    assert max(r["t_max"] for r in rows) > mod.solve_steady(p, 1.0).t_max + 1.0       # the face term is not small here


@pytest.mark.parametrize("adapter", [profiles._FVMAdapter, profiles._FDMAdapter])
def test_without_absent_copper_the_curves_are_the_nodes_bit_for_bit(adapter):
    p = board(bare=False)
    ad = adapter(p, 1.0)
    assert all(loc is None for loc in ad._face_loc)
    state, _ = ad.begin(ProfileOptions())
    hottest, under = ad.observe(state)
    assert hottest == float(state.max() + 25.0)
    assert np.array_equal(under, np.array([state[idx].max() for idx in ad.net.footprints]) + 25.0)


def test_the_face_follows_the_power_of_the_step_with_no_lag():
    p = board()
    ad = profiles._FVMAdapter(p, 1.0)
    state, _ = ad.begin(ProfileOptions())
    node = state[ad.net.footprints[0]].max() + 25.0
    ad._powers = np.array([0.0])                                       # the power drops to zero in this step: the face term is gone at once, the node stays
    assert ad.observe(state)[1][0] == pytest.approx(node, abs=1e-12)
    ad._powers = np.array([0.5])
    half = ad.observe(state)[1][0] - node
    ad._powers = np.array([1.0])
    full = ad.observe(state)[1][0] - node
    assert full == pytest.approx(2.0 * half, rel=1e-12) and full > 10.0


def test_a_long_square_wave_ends_at_the_steady_table_value():
    p = board()
    tau = fvm.estimate_time_constant(p)
    steady = steady_rows(p, fvm, 1.0)[0]["t_max"]
    p.heaters[0].set_profile(SquareWave(p_on=1.0, period=40 * tau, duty=0.5, p_off=0.0))
    resp = profiles.step_response_fvm(p, cell_mm=2.0)
    opts = ProfileOptions(threshold_c=0.0, duration="cycles", cycles=3, theta=1.0, initial="temperature", initial_c=25.0)
    res = profiles.run_fvm(p, profiles.decide(p, resp, 0.0), opts, cell_mm=1.0)
    assert res.resolved
    assert res.steady_peak_max == pytest.approx(steady, abs=1e-9)
    assert res.t_heaters[0].max() == pytest.approx(steady, abs=5e-3)    # implicit Euler and a finite on-phase: the curve has not quite reached the end
    assert res.t_heaters[0].max() <= steady + 1e-9
