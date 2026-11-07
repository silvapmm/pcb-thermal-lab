#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_stackimpedance.py
@brief Tests of pcbthermal.stackimpedance (the closed-form impedance of the stack under a part and the ripple of a fast square wave): closed forms, an independent radial
       finite-volume solution, the reference numbers of research/fast-wave-oscillation, the status of a part, and the decision, the run and the warnings that use it.
"""

import numpy as np
import pytest
from scipy.linalg import solve_banded

from pcbthermal import api, checks, profiles, stackimpedance as S
from pcbthermal.model import Dielectric, Problem, SquareWave


def two_layer(part_mm=10.0, layer=1, wave=None):
    """!
    @brief The 60 x 40 mm two-layer full-copper board of the study with a square part in the middle and h = 10 W/m2K on both faces.
    @param part_mm Side of the part in millimetres.
    @param layer 1-based layer of the part.
    @param wave SquareWave or None.
    @return Problem.
    """
    p = Problem.new(60, 40, 2, 1.6, h_top=10.0, h_bottom=10.0, h_side=0.0).add_full_copper()
    p.add_heater(layer, 3.0, rect=(30 - part_mm / 2, 20 - part_mm / 2, 30 + part_mm / 2, 20 + part_mm / 2), name="fast", profile=wave)
    return p


# ------------------------------------------------------------------ closed forms

def test_thick_layer_shows_the_effusivity_whatever_lies_beyond():
    # A layer much thicker than the penetration depth: Y = k gamma = sqrt(j w k rho c), the far face is not felt
    w = np.array([10.0, 1e3])
    k, rc = 0.3, 1.66e6
    y = S.half_admittance([(0.5, k, rc)], w, h_end=1e6)
    assert y == pytest.approx(np.sqrt(1j * w * k * rc), rel=1e-9)


def test_thin_layer_at_low_frequency_is_the_convection_plus_its_capacity():
    # w -> 0: the layer is isothermal and adds its capacity to the far convection, Y = h + j w c d
    d, k, rc, h = 35e-6, 385.0, 3.45e6, 10.0
    w = np.array([1e-4, 1e-3])
    y = S.half_admittance([(d, k, rc)], w, h)
    assert y == pytest.approx(h + 1j * w * rc * d, rel=1e-5)
    assert S.half_admittance([], w, h) == pytest.approx(np.full(2, h, dtype=complex))        # no layers: the face itself


def _radial_centre(y, sheet, a, n=6000, reach=12.0):
    """!
    @brief Independent solution of sheet * (theta'' + theta'/r) - y theta = -q for a uniform flux on r < a (finite volumes in r, complex y), the rise of the first cell.
    @param y Complex admittance per area in W/m2K.
    @param sheet Sheet conductance in W/K.
    @param a Radius of the disc in m.
    @param n Cells.
    @param reach Domain radius in units of the decay length sqrt(sheet / |y|) or of a, whichever is larger.
    @return Complex rise per watt (K/W) at the centre (extrapolated from the first two cells).
    """
    rmax = max(reach * np.sqrt(sheet / abs(y)), 4.0 * a)
    dr = rmax / n
    r = (np.arange(n) + 0.5) * dr
    rf = np.arange(1, n) * dr                                              # faces between cells
    flux = 2.0 * np.pi * sheet * rf / dr                                   # conductance between cells i and i+1
    diag = np.zeros(n, dtype=complex)
    diag[:-1] += flux
    diag[1:] += flux
    diag += y * 2.0 * np.pi * r * dr
    diag[-1] += 2.0 * np.pi * sheet * rmax / (dr / 2.0)                    # theta = 0 at rmax, half a cell from the last centre
    ab = np.zeros((3, n), dtype=complex)
    ab[0, 1:] = -flux
    ab[1] = diag
    ab[2, :-1] = -flux
    q = np.where(r < a, 1.0 / (np.pi * a * a), 0.0) * 2.0 * np.pi * r * dr
    th = solve_banded((1, 1), ab, q.astype(complex))
    return th[0] + (th[0] - th[1]) / 8.0                                   # centre by extrapolation in r^2 (theta ~ c0 - c1 r^2 at r = dr/2 and 3 dr/2)


def test_disc_on_a_sheet_matches_an_independent_radial_solution():
    # A 10 mm part (a = 5.64 mm) on a 35 um sheet over a complex admittance, three frequencies from the slow to the fast
    col = S.HeaterColumn(radius=np.sqrt(1e-4 / np.pi), sheet=385.0 * 35e-6, capacity=3.45e6 * 35e-6,
                         up=[], down=[(0.78e-3, 0.3, 1.66e6), (35e-6, 385.0, 3.45e6)], h_top=10.0, h_bottom=10.0)
    for f in (0.1, 5.0, 300.0):
        w = 2.0 * np.pi * f
        z = col.impedance(np.array([w]))[0]
        y = col.admittance(np.array([w]))[0]
        ref = _radial_centre(y, col.sheet, col.radius)
        assert z == pytest.approx(ref, rel=0.01)


def test_slow_limit_swing_is_the_steady_rise_and_the_wave_has_no_mean():
    col, status = S.column_for_heater(two_layer(), 0)
    assert status == "ok"
    z0 = col.impedance(np.array([1e-9]))[0].real                           # the steady resistance of the model: the limit of a very slow wave
    assert col.swing(1e6, 0.5) == pytest.approx(z0, rel=0.02)              # on for half of a very long period: the rise reaches the steady value
    rip = col.ripple(0.05, 0.3)
    assert abs(float(rip.samples.mean())) < 1e-12 * max(abs(rip.samples).max(), 1.0)
    assert rip.plus - rip.minus == pytest.approx(col.swing(0.05, 0.3), rel=1e-12)


def test_mean_over_a_step_is_the_wave_for_a_short_step_and_zero_for_a_long_one():
    col, _ = S.column_for_heater(two_layer(), 0)
    rip = col.ripple(0.05, 0.3)
    t = np.array([0.011, 0.0123, 0.031])
    assert rip.mean_over(t - 1e-6, t) == pytest.approx(rip.at(t), abs=1e-3 * (rip.plus - rip.minus))
    # A step of exactly the period (aliasing case: the samples of the old code were all at phase 0) and of 20 periods: the mean of the wave, zero
    ends = np.array([0.05, 1.0, 2.0])
    assert rip.mean_over(ends - 0.05, ends) == pytest.approx(np.zeros(3), abs=1e-6)
    assert rip.mean_over(ends - 1.0, ends) == pytest.approx(np.zeros(3), abs=1e-6)


# ------------------------------------------------------------------ the reference numbers of research/fast-wave-oscillation

def test_headline_case_against_the_reference_solvers():
    # 20 Hz, 30 %, 10 W on the 10 mm part of the 2-layer board: the reviewer's independent Cartesian 3D solver gives 6.375 K (README 8.7), the author's axisymmetric one 6.36 K
    p = two_layer(wave=SquareWave(p_on=10.0, period=0.05, duty=0.3))
    col, _ = S.column_for_heater(p, 0)
    assert 10.0 * col.swing(0.05, 0.3) == pytest.approx(6.375, rel=0.01)
    assert 10.0 * col.swing(0.05, 0.3) == pytest.approx(6.351, abs=0.005)    # the value of this implementation (the research module gave 6.355)


def test_example_board_u1_at_100_hz():
    # tests.test_profiles.example_with_profiles(): U1 13.3 W swing at 100 Hz, duty 30 %: the reference gives 2.02 K, the research module 2.013 K, the node structure 0.393 K
    from test_profiles import example_with_profiles
    p = example_with_profiles(100.0)
    col, status = S.column_for_heater(p, 0)
    assert status == "ok"
    w = p.heaters[0].profile
    assert (w.p_on - w.p_off) * col.swing(w.period, w.duty) == pytest.approx(2.02, rel=0.01)


# Swings per watt of the reviewer's Cartesian 3D reference (research/fast-wave-oscillation/out/review_cases.json, produced by lib/review_rect3d.py: duty 30 %, h 10 W/m2K on both faces,
# 60 x 40 mm, 35 um copper, 1.6 mm, a square part in the middle, the hottest cell of the part), written here once (K per W of swing): (layers, layer 0-based, side mm, frequency Hz) ->
# (reference, highest accepted ratio of the closed form). The ratios printed when this table was made are 0.955 to 1.016 for the bottom heater and 0.996 to 1.17 for the inner layer
# (the 1.16 and 1.17 are the 0.1 Hz points, where the planes and the finite board matter; they are on the safe side).
REFERENCE_SWINGS = {
    (4, 1, 10, 0.1): (6.6436, 1.18), (4, 1, 10, 0.3): (4.8839, 1.03), (4, 1, 10, 1.0): (3.0107, 1.03), (4, 1, 10, 10.0): (0.7953, 1.02), (4, 1, 10, 100.0): (0.1307, 1.02),
    (4, 1, 10, 1000.0): (0.0159, 1.02),
    (4, 1, 5, 0.1): (12.4344, 1.18), (4, 1, 5, 1.0): (7.6894, 1.03), (4, 1, 5, 10.0): (2.9620, 1.03), (4, 1, 5, 100.0): (0.5249, 1.02),
    (2, 1, 10, 0.1): (9.7190, 1.03), (2, 1, 10, 1.0): (4.6470, 1.03), (2, 1, 10, 20.0): (0.6375, 1.02), (2, 1, 10, 100.0): (0.1510, 1.02), (2, 1, 10, 1000.0): (0.0169, 1.02),
}


@pytest.mark.parametrize("key", sorted(REFERENCE_SWINGS))
def test_against_the_cartesian_reference(key):
    layers, layer, side, f = key
    p = Problem.new(60, 40, layers, 1.6, h_top=10.0, h_bottom=10.0, h_side=0.0).add_full_copper()
    p.add_heater(layer + 1, 3.0, rect=(30 - side / 2, 20 - side / 2, 30 + side / 2, 20 + side / 2), name="x")
    col, _ = S.column_for_heater(p, 0)
    ref, hi = REFERENCE_SWINGS[key]
    ratio = col.swing(1.0 / f, 0.3) / ref
    assert 0.97 < ratio < hi, ratio


# ------------------------------------------------------------------ where it applies

def test_status_of_a_part_bare_laminate_and_metal_block():
    p = two_layer()
    assert S.column_for_heater(p, 0)[1] == "ok"
    bare = Problem.new(60, 40, 2, 1.6, h_top=10.0, h_bottom=10.0, h_side=0.0)
    bare.add_zone(2, rect=(0, 0, 60, 40))                                   # copper on the other layer only
    bare.add_heater(1, 3.0, rect=(25, 15, 35, 25), name="bare")
    col, status = S.column_for_heater(bare, 0)
    assert col is None and status == "bare"
    half = Problem.new(60, 40, 2, 1.6, h_top=10.0, h_bottom=10.0, h_side=0.0)
    half.add_zone(1, rect=(0, 0, 60, 20))                                   # copper under half of the part: the fill is 0.5
    half.add_heater(1, 3.0, rect=(25, 15, 35, 25), name="half")
    assert S.column_for_heater(half, 0)[1] == "bare"
    blk = two_layer()
    blk.add_heatsink(1, 0.0, rect=(0, 0, 20, 20), thickness_mm=3.0)
    assert S.column_for_heater(blk, 0) == (None, "block")


def test_a_hatched_zone_and_the_other_layers_copper_enter_the_column():
    full = two_layer()
    hatched = Problem.new(60, 40, 2, 1.6, h_top=10.0, h_bottom=10.0, h_side=0.0)
    hatched.add_zone(1, rect=(0, 0, 60, 40), fill=0.95)
    hatched.add_zone(2, rect=(0, 0, 60, 40))
    hatched.add_heater(1, 3.0, rect=(25, 15, 35, 25), name="h")
    c_full, _ = S.column_for_heater(full, 0)
    c_hatch, status = S.column_for_heater(hatched, 0)
    assert status == "ok" and c_hatch.sheet == pytest.approx(0.95 * c_full.sheet, rel=1e-6)
    # No copper on the other layer: its slab is laminate, so the column below is different and the swing too
    one_side = Problem.new(60, 40, 2, 1.6, h_top=10.0, h_bottom=10.0, h_side=0.0)
    one_side.add_zone(1, rect=(0, 0, 60, 40))
    one_side.add_heater(1, 3.0, rect=(25, 15, 35, 25), name="o")
    c_one, _ = S.column_for_heater(one_side, 0)
    assert c_one.swing(20.0, 0.3) != pytest.approx(c_full.swing(20.0, 0.3), rel=1e-3)      # at 20 Hz only the top is felt; at 0.05 Hz the layer below matters


def test_advanced_stackup_with_equal_gaps_is_the_simple_one_and_a_one_layer_board_works():
    simple = two_layer(wave=SquareWave(p_on=10.0, period=0.05, duty=0.3))
    adv = two_layer(wave=SquareWave(p_on=10.0, period=0.05, duty=0.3))
    gap = adv.board.dielectric_thickness()
    adv.board.make_advanced()
    assert S.column_for_heater(adv, 0)[0].swing(0.05, 0.3) == pytest.approx(S.column_for_heater(simple, 0)[0].swing(0.05, 0.3), rel=1e-9)
    # A thicker gap with a better conductor changes it
    adv.board.dielectrics[0] = Dielectric(gap * 2, "x", 1.0, 1.0, 1850.0, 900.0)
    assert S.column_for_heater(adv, 0)[0].swing(0.05, 0.3) != pytest.approx(S.column_for_heater(simple, 0)[0].swing(0.05, 0.3), rel=1e-3)
    one = Problem.new(60, 40, 1, 1.6, h_top=10.0, h_bottom=10.0, h_side=0.0).add_full_copper()
    one.add_heater(1, 3.0, rect=(25, 15, 35, 25), name="one")
    col, status = S.column_for_heater(one, 0)
    assert status == "ok" and col.up == [] and len(col.down) == 1 and col.swing(0.05, 0.3) > 0.0


def test_the_bottom_heater_and_an_inner_one_use_the_two_sided_form():
    p = Problem.new(60, 40, 4, 1.6, h_top=10.0, h_bottom=10.0, h_side=0.0).add_full_copper()
    for layer in (1, 2, 3, 4):
        p.add_heater(layer, 1.0, rect=(25, 15, 35, 25), name=f"L{layer}")
    cols = [S.column_for_heater(p, k)[0] for k in range(4)]
    assert [len(c.up) for c in cols] == [0, 2, 4, 6] and [len(c.down) for c in cols] == [6, 4, 2, 0]
    sw = [c.swing(0.01, 0.3) for c in cols]
    # The stack is symmetric (equal h on both faces): the layers 2 and 3 are mirror images of each other, as are 1 and 4
    assert all(x > 0.0 for x in sw) and sw[1] == pytest.approx(sw[2], rel=1e-9) and sw[0] == pytest.approx(sw[3], rel=1e-9)


# ------------------------------------------------------------------ the decision, the run and the warnings

def test_the_floor_never_lowers_the_oscillation_and_the_gate_uses_the_shortest_stretch():
    # 0.5 Hz, 10 % duty: the period is 2 s but the shortest stretch is 0.2 s, below the 4 s gate: ripple. 20 s, 25 %: stretch 5 s: time-stepped
    p = two_layer()
    p.add_heater(1, 1.0, rect=(5, 5, 10, 10), name="slow", profile=SquareWave(p_on=4.0, period=20.0, duty=0.25))
    p.heaters[0].set_profile(SquareWave(p_on=10.0, period=10.0, duty=0.1))
    resp = profiles.step_response_fvm(p, 2.0)
    d = profiles.decide(p, resp, 1.0)
    node = profiles.wave_response(resp, 0, p.heaters[0].profile)
    assert d[0].oscillation >= node[0] - node[1] - 1e-9 and d[0].regime == profiles.REGIME_RIPPLE
    assert d[1].regime == "resolved"
    assert profiles.fast_stretch_limit(2) == 4.0 and profiles.fast_stretch_limit(4) == 2.0


def test_a_part_on_bare_laminate_keeps_the_old_decision():
    bare = Problem.new(60, 40, 2, 1.6, h_top=10.0, h_bottom=10.0, h_side=0.0)
    bare.add_zone(2, rect=(0, 0, 60, 40))
    bare.add_heater(1, 3.0, rect=(25, 15, 35, 25), name="bare", profile=SquareWave(p_on=10.0, period=0.05, duty=0.3))
    resp = profiles.step_response_fvm(bare, 2.0)
    d = profiles.decide(bare, resp, 1.0)
    assert d[0].ripple_swing == 0.0 and d[0].regime != profiles.REGIME_RIPPLE


def test_a_ripple_only_run_has_the_wave_in_the_curve_the_peak_and_not_in_the_map():
    p = two_layer(wave=SquareWave(p_on=10.0, period=0.05, duty=0.3))
    sim = api.simulate(p, api.SolverOptions(models=("fvm",), cell_mm=2.0))
    r = sim.profile_results["fvm"]
    assert sim.decisions[0].regime == profiles.REGIME_RIPPLE
    assert r.resolved and r.steps == 0 and r.converged                       # nothing time-stepped, a result that the views can show
    assert r.ripple[0]["swing_c"] == pytest.approx(6.351, abs=0.005)
    # The peak is the steady average maximum plus the top of the wave; the minimum the bottom of it; the map is the average field
    assert r.peak == pytest.approx(r.steady_average_max + r.ripple[0]["plus_c"], abs=1e-6)
    assert r.minimum == pytest.approx(r.steady_average_max + r.ripple[0]["minus_c"], abs=1e-6)
    assert r.oscillation == pytest.approx(6.351, abs=0.005)
    assert float(r.peak_map.max()) == pytest.approx(r.steady_average_max, abs=0.01)      # the ripple is not in the maps
    assert r.frames.shape[0] == 1 and r.frames.max() == pytest.approx(r.steady_average_max, abs=0.01)
    assert any("faster than the board model can follow" in w for w in r.warnings)
    assert "average + ripple" in sim.report() and "average + ripple" in sim.to_markdown() and "peak to peak at the heater" in sim.report()


def test_response_cell_of_a_small_part_is_finer_and_respects_the_floor():
    small = two_layer(part_mm=2.0, wave=SquareWave(p_on=10.0, period=10.0, duty=0.3))
    o = api.SolverOptions(models=("fvm",), cell_mm=1.0)
    assert api.response_cell_mm(small, "fvm", o) == pytest.approx(0.5)       # a quarter of the 2 mm side, below the old 2 mm
    tiny = two_layer(part_mm=0.5, wave=SquareWave(p_on=10.0, period=10.0, duty=0.3))
    assert api.response_cell_mm(tiny, "fvm", o) == pytest.approx(api.RESPONSE_CELL_FLOOR_MM)
    big = two_layer(part_mm=20.0, wave=SquareWave(p_on=10.0, period=10.0, duty=0.3))
    assert api.response_cell_mm(big, "fvm", o) == 2.0                        # a large part keeps the old cell
    coarse = api.SolverOptions(models=("fvm",), cell_mm=3.0)
    assert api.response_cell_mm(small, "fvm", coarse) == pytest.approx(0.5)
    assert api.response_cell_mm(two_layer(), "fvm", o) == 2.0                # no profile: unchanged


def test_the_small_part_decision_is_no_longer_averaged_at_the_coarse_cell():
    # The 2 mm part at 0.1 Hz: the response at 2 mm was 0.67 of the truth (research/fast-wave-oscillation 8.3); the finer response lifts the decision
    p = two_layer(part_mm=2.0, wave=SquareWave(p_on=1.0, period=10.0, duty=0.3))
    o = api.SolverOptions(models=("fvm",), cell_mm=2.0)
    coarse = profiles.step_response_fvm(p, 2.0)
    fine = api.step_response(p, "fvm", o)
    wc = profiles.wave_response(coarse, 0, p.heaters[0].profile)
    wf = profiles.wave_response(fine, 0, p.heaters[0].profile)
    assert (wf[0] - wf[1]) > 1.25 * (wc[0] - wc[1])


def test_warnings_for_bare_laminate_and_for_a_slow_wave_near_a_side():
    bare = Problem.new(60, 40, 2, 1.6, h_top=10.0, h_bottom=10.0, h_side=0.0)
    bare.add_zone(2, rect=(0, 0, 60, 40))
    bare.add_heater(1, 3.0, rect=(25, 15, 35, 25), name="B1", profile=SquareWave(p_on=10.0, period=0.1, duty=0.3))
    w = checks.check_fast_wave(bare)
    assert len(w) == 1 and "no copper under it" in w[0] and "2.2 times too small" in w[0] and "2.4 times at 1 kHz" in w[0] and w[0].kind == "heater"
    slow_bare = Problem.new(60, 40, 2, 1.6, h_top=10.0, h_bottom=10.0, h_side=0.0)
    slow_bare.add_zone(2, rect=(0, 0, 60, 40))
    slow_bare.add_heater(1, 3.0, rect=(25, 15, 35, 25), name="B2", profile=SquareWave(p_on=10.0, period=2.0, duty=0.3))
    assert checks.check_fast_wave(slow_bare) == []                            # below 3 Hz the bare part is the old, accepted case
    edge = Problem.new(60, 40, 2, 1.6, h_top=10.0, h_bottom=10.0, h_side=0.0).add_full_copper()
    edge.add_heater(1, 3.0, rect=(1, 1, 6, 6), name="E1", profile=SquareWave(p_on=10.0, period=10.0, duty=0.3))
    w = checks.check_fast_wave(edge)
    assert len(w) == 1 and "from a side of the board" in w[0] and "0.61" in w[0]
    fast_edge = Problem.new(60, 40, 2, 1.6, h_top=10.0, h_bottom=10.0, h_side=0.0).add_full_copper()
    fast_edge.add_heater(1, 3.0, rect=(1, 1, 6, 6), name="E2", profile=SquareWave(p_on=10.0, period=0.01, duty=0.3))
    assert checks.check_fast_wave(fast_edge) == []                            # a fast wave near a side: the closed form holds (1.38 at 20 Hz, on the safe side)
    assert checks.check_fast_wave(two_layer(wave=SquareWave(p_on=10.0, period=10.0, duty=0.3))) == []      # centred, full copper: silent
    assert checks.check_fast_wave(two_layer()) == []                          # no profile
    assert any("no copper under it" in x for x in checks.check_input(bare, ("fvm",), 1.0))      # part of the live list
