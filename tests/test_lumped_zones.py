#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_lumped_zones.py
@brief The zone model of the Lumped heater network (a footprint cut into the rest A and the core C of a dense via group): closed forms, the branch decision, bit-identity of the
       one-node network, the steady state, the profile adapter, the raster rule and the warnings.
@details Design: research/lumped-zones-adoption/INTEGRATION.md 11 as corrected by the second review (README 10). References that do not use the program: radial integrals of the
         Krogh cell and of the annulus, and the layered 3D solver of tests/helpers is not needed here (the research folder holds those comparisons).
"""

import math

import numpy as np
import pytest
from scipy.integrate import quad

from pcbthermal import SolverOptions, lumped, simulate, viaconstriction
from pcbthermal.fvm import Network

from test_via_constriction import array


# ------------------------------------------------------------------------------------------------ closed forms

def test_annulus_out_resistance_against_the_radial_integral_and_the_disc_limit():
    """!
    @brief The mean-to-outer-wall resistance of an annulus with a uniform source and an insulated inner side equals the radial integral, and tends to 1 / (8 pi S) as the inner radius goes to 0.
    @return None.
    """
    s, r_in, r_out = 0.37, 1.3e-3, 4.1e-3
    # T(r) - T(r_out) = q / (2 S) integral_r^r_out [ (r_out^2 - u^2) - ... ] du: the flux through radius u is q pi (u^2 - r_in^2), so dT/du = -q (u^2 - r_in^2) / (2 S u)
    def rise(r):
        return quad(lambda u: (u * u - r_in * r_in) / (2.0 * s * u), r, r_out)[0]
    area = math.pi * (r_out ** 2 - r_in ** 2)
    mean = quad(lambda r: rise(r) * 2.0 * math.pi * r, r_in, r_out)[0] / area
    # per watt generated: divide by q * area (the rise above was per unit q)
    assert viaconstriction.annulus_out_resistance(s, r_in, r_out) == pytest.approx(mean / area, rel=1e-6)
    assert viaconstriction.annulus_out_resistance(s, 1e-9, r_out) == pytest.approx(1.0 / (8.0 * math.pi * s), rel=1e-6)
    assert viaconstriction.annulus_out_resistance(s, r_out, r_out) == 0.0


def test_rim_minus_mean_against_the_radial_integral():
    """!
    @brief The rim of a Krogh cell above its area mean, per watt taken by the via, equals the radial integral of the profile T(r) - T(a) = q integral (R^2 - u^2) / (2 S u) du.
    @return None.
    """
    s, big_r, a = 0.52, 1.7e-3, 0.11e-3
    def rise(r):
        return quad(lambda u: (big_r ** 2 - u * u) / (2.0 * s * u), a, r)[0]
    area = math.pi * (big_r ** 2 - a * a)
    mean = quad(lambda r: rise(r) * 2.0 * math.pi * r, a, big_r)[0] / area
    expected = (rise(big_r) - mean) / area                       # per watt: q * area watts enter the via
    assert viaconstriction.rim_minus_mean(s, big_r, a) == pytest.approx(expected, rel=1e-6)
    assert viaconstriction.rim_minus_mean(s, a, a) == 0.0


# ------------------------------------------------------------------------------------------------ ring_couplings

def _ring_inputs():
    """!
    @brief The inputs of ring_couplings for a 3 x 3 array under a source: the Lumped network pieces of the first heater at 0.5 mm.
    @return Tuple (ViaSet, net, idx, R, cnt, S, g_top, g_bot, gz_diel, nb).
    """
    p = array(3, 3.5)
    net = Network(p, 42, 42, assemble=False, with_blocks=True, ladder=False)
    nb = net.n_board
    idx = np.zeros((net.ny, net.nx), dtype=int)
    idx[:, net.nx // 2:] = 1                                     # two "rings": left and right halves
    R = 2
    flat = idx.ravel()
    ring_sum = lambda a: np.bincount(flat, weights=a.ravel(), minlength=R)
    cnt = np.bincount(flat, minlength=R)
    S = np.array([ring_sum(net.S[l]) / cnt for l in range(net.nl)])
    g_top = np.array([ring_sum(net.g_top[l]) for l in range(net.nl)])
    g_bot = np.array([ring_sum(net.g_bottom[l]) for l in range(net.nl)])
    gz_diel = np.array([ring_sum(net.gz[l]) for l in range(nb - 1)])
    return viaconstriction.ViaSet(p), net, idx, R, cnt, S, g_top, g_bot, gz_diel, nb


def test_ring_couplings_want_barrel_keeps_the_result_bit_for_bit():
    """!
    @brief ring_couplings with want_barrel returns the same couplings as the default call (equal with ==), plus the barrel-only couplings and the vias of every node.
    @return None.
    """
    vs, net, idx, R, cnt, S, g_top, g_bot, gz_diel, nb = _ring_inputs()
    plain = viaconstriction.ring_couplings(vs, net, idx, R, cnt, S, g_top, g_bot, gz_diel, nb)
    gz, via_gz, seen = viaconstriction.ring_couplings(vs, net, idx, R, cnt, S, g_top, g_bot, gz_diel, nb, want_barrel=True)
    assert plain.keys() == gz.keys()
    for key in plain:
        assert np.array_equal(plain[key], gz[key])
    assert sum(s["n"] for s in seen) == len(vs)
    for key, g in via_gz.items():
        assert np.all(g >= 0.0) and np.all(gz[key] >= g - 1e-15)       # the barrel is part of the coupling, never more than it
    assert all(s["r_cell"] > 0 and s["a"] > 0 for s in seen)


def test_ring_couplings_without_vias_returns_the_dict_or_empty_extras():
    """!
    @brief With no vias the function returns the dielectric couplings alone, and with want_barrel two empty extras.
    @return None.
    """
    vs, net, idx, R, cnt, S, g_top, g_bot, gz_diel, nb = _ring_inputs()

    class NoVias:
        def __len__(self):
            return 0
    out = viaconstriction.ring_couplings(NoVias(), net, idx, R, cnt, S, g_top, g_bot, gz_diel, nb)
    assert all(np.array_equal(out[(l, l + 1)], gz_diel[l]) for l in range(nb - 1))
    gz, via_gz, seen = viaconstriction.ring_couplings(NoVias(), net, idx, R, cnt, S, g_top, g_bot, gz_diel, nb, want_barrel=True)
    assert via_gz == {} and seen == [] and gz.keys() == out.keys()


# ------------------------------------------------------------------------------------------------ the zone branch (steady state)

ZONED = [(3, 2.0, 24.0, 12.0), (5, 1.5, 24.0, 14.0), (4, 2.5, 24.0, 16.0)]      # (vias a side, pitch mm, board side mm, source side mm): core 25 to 45 % of the footprint


def _network(p, cell_mm=0.5):
    """!
    @brief The Lumped network of the first heater of a problem, built as solve_steady builds it.
    @param p A Problem.
    @param cell_mm Lumped raster in mm.
    @return Tuple (net, cov, system dict).
    """
    b = p.board
    nx, ny = max(int(round(b.width * 1000.0 / cell_mm)), 8), max(int(round(b.height * 1000.0 / cell_mm)), 8)
    net = Network(p, nx, ny, assemble=False, with_blocks=True, ladder=False)
    cov = lumped._footprint_coverage(net, p.heaters[0])
    vias = viaconstriction.ViaSet(p) if p.vias else None
    return net, cov, lumped._heater_network(net, cov, p.heaters[0].layer, p.heaters[0].power, 10, vias)


@pytest.mark.parametrize("spec", ZONED)
def test_a_dense_group_under_a_larger_footprint_is_zoned(spec):
    """!
    @brief A group of vias that covers part of a larger footprint gives the two-node footprint: energy balance, symmetric positive definite matrix, capacities that add to the one-node footprint.
    @param spec (vias a side, pitch, board side, source side) of the board.
    @return None.
    """
    n, pitch, side, src = spec
    p = array(n, pitch, side=side, source=src)
    net, cov, rn = _network(p)
    assert rn["nz"] == 2 and "core" in rn and 0 < rn["core"].sum() < (cov > 0).sum()
    assert rn["residual"] < 1e-10
    k = rn["K"]
    assert np.allclose(k, k.T) and np.all(np.linalg.eigvalsh(k) > 0)
    th, R = rn["theta"], rn["R"]
    out = sum(rn["out"].values())
    assert out == pytest.approx(p.heaters[0].power, rel=1e-9)                     # all the heat leaves by the faces and the sides
    assert rn["source"].sum() == pytest.approx(1.0, abs=1e-12)
    # The capacity of the two footprint nodes is the capacity of the footprint cells: the same machinery as the one-node network
    one = lumped._one_node_network(net, cov, 0, 2.0, 10, viaconstriction.ViaSet(p))
    cap2, cap1 = rn["C"].reshape(net.nl, R), one["C"].reshape(net.nl, one["R"])
    assert np.allclose(cap2[:, :2].sum(axis=1), cap1[:, 0], rtol=1e-12)
    assert th.shape == (net.nl, one["R"] + 1)


@pytest.mark.parametrize("spec", ZONED)
def test_zones_read_the_hottest_temperature_nearer_the_fvm_than_one_node(spec):
    """!
    @brief Against the FVM at 0.25 mm the zoned Lumped hottest temperature is within 4 % of the rise and not more than 2 % too cool (the criterion of the research folder), and closer than one node.
    @param spec (vias a side, pitch, board side, source side) of the board.
    @return None.
    """
    n, pitch, side, src = spec
    p = array(n, pitch, side=side, source=src)
    ref = simulate(p, SolverOptions(models=("fvm",), cell_mm=0.25)).results["fvm"]
    z = lumped.solve_steady(p, 10, 0.5)
    lumped.ZONES = False
    try:
        one = lumped.solve_steady(p, 10, 0.5)
    finally:
        lumped.ZONES = True
    rise = ref.t_max - ref.ambient
    assert (z.t_max - ref.t_max) / rise > -0.02
    assert abs(z.t_max - ref.t_max) / rise < 0.04
    assert abs(z.t_max - ref.t_max) < abs(one.t_max - ref.t_max)


def test_boards_where_no_zone_applies_are_bit_identical_to_the_one_node_network():
    """!
    @brief No vias, vias outside every footprint, one via under the footprint, a core above 92 % of the footprint and ZONES off give the one-node network line for line (==).
    @return None.
    """
    cases = [array(3, 3.5)]                                                    # core covers all the 10 mm part: 98 to 100 %
    plain = array(3, 3.5)
    plain.vias = []
    cases.append(plain)
    away = array(3, 3.5)
    for v in away.vias:
        v.x, v.y = v.x * 0.2, v.y * 0.2                                         # moved to a corner, outside the footprint
    cases.append(away)
    lone = array(3, 3.5)
    lone.vias = lone.vias[:1]
    cases.append(lone)
    for p in cases:
        net, cov, rn = _network(p)
        one = lumped._one_node_network(net, cov, 0, p.heaters[0].power, 10, viaconstriction.ViaSet(p) if p.vias else None)
        assert "core" not in rn and rn.keys() == one.keys()
        for key in ("theta", "rho", "K", "C", "dist"):
            assert np.array_equal(rn[key], one[key])
        assert rn["peak_extra"] == one["peak_extra"] and rn["residual"] == one["residual"]
    p = array(3, 2.0, side=24.0, source=12.0)                                  # a zoned board with the switch off
    lumped.ZONES = False
    try:
        net, cov, rn = _network(p)
    finally:
        lumped.ZONES = True
    assert "core" not in rn


def test_the_fallback_threshold_is_two_sided():
    """!
    @brief A core that covers more than 92 % of the footprint on the fine grid falls back to one node.
    @return None.
    """
    p = array(3, 3.5, source=10.0)
    net, cov, rn = _network(p, 0.5)
    assert "core" not in rn
    assert lumped._fine_core_share(net, cov, viaconstriction.ViaSet(p)) > lumped.MAX_CORE
    assert not lumped.will_be_zoned(p, p.heaters[0])
    z = array(3, 2.0, side=24.0, source=12.0)
    assert lumped.will_be_zoned(z, z.heaters[0])


def test_the_fine_share_does_not_depend_on_the_raster_and_drops_vias_outside_the_footprint():
    """!
    @brief The share of the core counted on the fine grid moves by less than 0.03 between rasters and equals a whole-board count at 0.1 mm (1e-9) when vias lie outside the footprint box.
    @return None.
    """
    from types import SimpleNamespace
    p = array(5, 1.5, side=21.0, source=14.0)
    shares = []
    for cell in (1.0, 0.75, 0.5):
        b = p.board
        nx, ny = int(round(b.width * 1000.0 / cell)), int(round(b.height * 1000.0 / cell))
        net = SimpleNamespace(nx=nx, ny=ny, dx=b.width / nx, dy=b.height / ny)
        shares.append(lumped._fine_core_share(net, lumped._footprint_coverage(net, p.heaters[0]), viaconstriction.ViaSet(p)))
    assert max(shares) - min(shares) < 0.03
    # A 6 mm footprint under a 5 x 5 array of 1.5 mm pitch: vias lie outside the footprint box
    q = array(5, 1.5, side=21.0, source=6.0)
    b = q.board
    nx = int(round(b.width * 1000.0 / 0.5))
    net = SimpleNamespace(nx=nx, ny=nx, dx=b.width / nx, dy=b.height / nx)
    cov = lumped._footprint_coverage(net, q.heaters[0])
    fine = SimpleNamespace(nx=nx * 5, ny=nx * 5, dx=net.dx / 5, dy=net.dy / 5)
    cov_f = lumped.coverage_fraction(q.heaters[0].polygon, fine.nx, fine.ny, fine.dx, fine.dy, 4)
    core = lumped._core_mask(fine, cov_f, viaconstriction.ViaSet(q))
    assert lumped._fine_core_share(net, cov, viaconstriction.ViaSet(q)) == pytest.approx(float((core * cov_f).sum() / cov_f.sum()), abs=1e-9)


def test_dead_vias_move_the_maximum_by_less_than_6_5_percent_of_the_rise():
    """!
    @brief Vias that conduct nothing (no plating, no fill) change the hottest temperature of a zoned part by less than 6.5 % of its rise (the unsafe-side bound measured on 62 boards, README 8.2).
    @return None.
    """
    for n, pitch, side, src in ZONED:
        p = array(n, pitch, side=side, source=src, fill_k=0.0)
        p.board.via_plating = 0.0
        bare = array(n, pitch, side=side, source=src)
        bare.vias = []
        dead = lumped.solve_steady(p, 10, 0.5)
        none = lumped.solve_steady(bare, 10, 0.5)
        assert (dead.t_max - none.t_max) / (none.t_max - none.ambient) > -0.065


def test_mirror_symmetry_of_a_zoned_part():
    """!
    @brief A zoned board and its mirror image (x -> width - x) give the same Lumped maximum and heat paths.
    @return None.
    """
    shift = 3.1e-3
    p = array(4, 2.0, side=30.0, source=14.0)
    m = array(4, 2.0, side=30.0, source=14.0)
    w = p.board.width
    for v in p.vias:
        v.x += shift
    for h in p.heaters:
        h.polygon = np.array([(x + shift, y) for x, y in h.polygon])
    for v in m.vias:
        v.x = w - (v.x + shift)
    for h in m.heaters:
        h.polygon = np.array([(w - (x + shift), y) for x, y in h.polygon])
    a, b = lumped.solve_steady(p, 10, 0.5), lumped.solve_steady(m, 10, 0.5)
    assert a.arrays["zoned_heaters"][0, 0] == 1.0
    assert a.t_max == pytest.approx(b.t_max, abs=1e-6)
    assert a.power_out["top"] == pytest.approx(b.power_out["top"], rel=1e-6)


def test_the_map_paints_the_core_with_its_own_node():
    """!
    @brief The temperature map shows node C in the core cells and node A in the rest of the footprint; the area mean of the painted footprint is the coverage-weighted mean of A and C.
    @return None.
    """
    p = array(3, 2.0, side=24.0, source=12.0)
    net, cov, rn = _network(p)
    res = lumped.solve_steady(p, 10, 0.5)
    layer0 = res.T[0] - p.board.ambient
    core, foot = rn["core"], cov > 0
    assert np.allclose(layer0[core], rn["theta"][0, 1])
    assert np.allclose(layer0[foot & ~core], rn["theta"][0, 0])
    a_part, c_part = float(cov[foot & ~core].sum()), float(cov[core].sum())
    mean_painted = float((layer0 * cov).sum() / cov.sum())
    assert mean_painted == pytest.approx((a_part * rn["theta"][0, 0] + c_part * rn["theta"][0, 1]) / (a_part + c_part), rel=1e-12)
    assert res.arrays["zoned_heaters"].tolist() == [[1.0, float(rn["core_across"])]]


# ------------------------------------------------------------------------------------------------ the transient and the profile runner

from pcbthermal import fvm, profiles                                  # noqa: E402
from pcbthermal.model import SquareWave, TableProfile                 # noqa: E402


def _constant_power_end(p, n_steps=60, dt=1.0e4):
    """!
    @brief Run the Lumped adapter at constant power (implicit Euler, long steps, from the ambient) and return the end rise and the steady rise of the hottest point.
    @param p A Problem with one heater.
    @param n_steps Number of steps.
    @param dt Step in s (long: the end state is the steady state).
    @return Tuple (rise at the end of the run, steady rise) in K.
    """
    ad = lumped._LumpedAdapter(p, 10, 0.5)
    ad.steppers = [lumped._Stepper(s, 1.0) for s in ad.systems]
    states = [np.zeros(len(s["C"])) for s in ad.systems]
    for _ in range(n_steps):
        states = ad.advance(states, dt, [h.power for h in p.heaters])
    end = ad.observe(states)[0] - p.board.ambient
    s0 = ad.systems[0]
    return end, lumped._own_point(s0, s0["theta"].ravel() * p.heaters[0].power)


@pytest.mark.parametrize("spec", ZONED)
def test_a_constant_power_through_the_adapter_ends_on_the_steady_peak(spec):
    """!
    @brief The profile adapter splits the source between A and C: a constant power ends on the steady peak to 1e-9 (relative); the whole power on A would end 5 to 17 % hot.
    @param spec (vias a side, pitch, board side, source side) of the board.
    @return None.
    """
    n, pitch, side, src = spec
    p = array(n, pitch, side=side, source=src)
    end, steady = _constant_power_end(p)
    assert end == pytest.approx(steady, rel=1e-9)
    # The control: the program's old source (the whole power on node A) fails the same test by a wide margin
    original = lumped._unit_source
    lumped._unit_source = lambda s: np.eye(len(s["C"]))[s["layer"] * s["R"]]
    try:
        hot, steady2 = _constant_power_end(p)
    finally:
        lumped._unit_source = original
    assert hot > 1.03 * steady2


def test_the_step_response_of_a_zoned_part_ends_on_the_steady_rise():
    """!
    @brief lumped.step_responses uses the split source and the zone peak: the last value of the unit step response is the steady rise per watt, and the first values are below it.
    @return None.
    """
    p = array(3, 2.0, side=24.0, source=12.0)
    t, z, rth = lumped.step_responses(p, 10, 0.5)
    assert z[0, -1] == pytest.approx(rth[0], rel=5e-3)
    assert z[0, 0] < 0.2 * rth[0] and np.all(np.diff(z[0]) > -1e-9)


@pytest.mark.parametrize("spec", ZONED)
def test_a_square_wave_with_zones_agrees_with_the_fvm(spec):
    """!
    @brief A 1 s square wave: the peak and the valley of the zoned Lumped model are within 8 % of the FVM's average steady rise (the unpatched source gives 9 to 17 % on the research boards).
    @param spec (vias a side, pitch, board side, source side) of the board.
    @return None.
    """
    n, pitch, side, src = spec
    p = array(n, pitch, side=side, source=src)
    h = p.heaters[0]
    h.profile = SquareWave(p_on=h.power / 0.5, period=1.0, duty=0.5, p_off=0.0)
    opt = profiles.ProfileOptions(threshold_c=0.0, duration="stable", stable_c=0.05, theta=0.5)
    t, z, r = fvm.step_responses(p, cell_mm=0.5)
    dec = profiles.decide(p, profiles.StepResponse("fvm", t, z, r), 0.0)
    ref = profiles.run_fvm(p, dec, opt, 0.5)
    got = lumped.run_profile(p, dec, opt, 10, 0.5)
    avg = ref.steady_average_max - p.board.ambient
    assert abs(np.max(got.t_max) - np.max(ref.t_max)) / avg < 0.08
    assert abs(np.min(got.t_max) - np.min(ref.t_max)) / avg < 0.08


def test_table_and_one_shot_profiles_and_two_parts_with_one_zoned_run():
    """!
    @brief A table profile, a one-shot profile and a board with two parts of which one is zoned run through the adapter and end consistently (steady value at the end of a held power).
    @return None.
    """
    p = array(3, 2.0, side=40.0, source=12.0)
    p.add_heater(1, 1.0, rect=(30.0, 30.0, 34.0, 34.0))                       # a second part away from the vias: one node
    p.heaters[0].profile = TableProfile([0, 2, 5, 9, 20], [6, 1, 3, 0], True)
    p.heaters[1].profile = TableProfile([0, 0.5, 20], [0.0, 2.0], False)      # one-shot: the last power is held
    opt = profiles.ProfileOptions(threshold_c=0.0, duration="stable", stable_c=0.05, theta=0.5)
    t, z, r = fvm.step_responses(p, cell_mm=1.0)
    dec = profiles.decide(p, profiles.StepResponse("fvm", t, z, r), 0.0)
    res = lumped.run_profile(p, dec, opt, 10, 0.5)
    assert np.all(np.isfinite(res.t_max)) and np.max(res.t_max) > p.board.ambient
    ad = lumped._LumpedAdapter(p, 10, 0.5)
    assert [s["nz"] if "nz" in s else 1 for s in ad.systems] == [2, 1]
    ad.steppers = [lumped._Stepper(s, 1.0) for s in ad.systems]
    states = [np.zeros(len(s["C"])) for s in ad.systems]
    for _ in range(60):
        states = ad.advance(states, 1.0e4, [2.0, 1.0])
    steady = lumped.solve_steady(_with_powers(p, [2.0, 1.0]), 10, 0.5)
    assert ad.observe(states)[0] == pytest.approx(steady.t_max, abs=1e-6)


def _with_powers(p, powers):
    """!
    @brief A copy of a problem with constant heater powers (no profiles).
    @param p A Problem.
    @param powers Power of every heater in W.
    @return Problem.
    """
    import copy
    q = copy.deepcopy(p)
    for h, w in zip(q.heaters, powers):
        h.profile = None
        h.power = w
    return q


# ------------------------------------------------------------------------------------------------ the raster and the warnings

from pcbthermal.checks import check_lumped_zones, check_model_limits      # noqa: E402


def test_cell_for_gives_half_a_millimetre_only_to_a_board_with_a_zoned_part():
    """!
    @brief A zoned heater moves the Lumped raster to 0.5 mm whatever the requested cell; a core that fills the footprint (the example board's nine vias), no vias and one via keep the clip of 0.5 to 1.0 mm.
    @return None.
    """
    z = array(3, 2.0, side=24.0, source=12.0)
    assert lumped.cell_for(z, 2.0) == 0.5 and lumped.cell_for(z, 1.0) == 0.5
    full = array(3, 3.5)                                                      # nine vias, the core fills the part: one node
    assert lumped.cell_for(full, 2.0) == 1.0 and lumped.cell_for(full, 0.75) == 0.75 and lumped.cell_for(full, 0.2) == 0.5
    none = array(3, 3.5)
    none.vias = []
    assert lumped.cell_for(none, 3.0) == 1.0
    lone = array(3, 3.5)
    lone.vias = lone.vias[:1]
    assert lumped.cell_for(lone, 3.0) == 1.0


def test_the_run_uses_the_zone_raster_in_steady_state_and_in_the_step_response():
    """!
    @brief simulate() runs the Lumped model of a zoned board at 0.5 mm even when the options ask for 2 mm; a board with a core that fills the footprint stays at 1.0 mm.
    @return None.
    """
    z = array(3, 2.0, side=24.0, source=12.0)
    res = simulate(z, SolverOptions(models=("lumped",), cell_mm=2.0)).results["lumped"]
    assert res.dx == pytest.approx(0.5e-3, rel=1e-6) and res.arrays["zoned_heaters"][0, 0] == 1.0
    full = array(3, 3.5)
    res = simulate(full, SolverOptions(models=("lumped",), cell_mm=2.0)).results["lumped"]
    assert res.dx == pytest.approx(1.0e-3, rel=0.03) and res.arrays["zoned_heaters"][0, 0] == 0.0


def _rect(p, x0, y0, x1, y1):
    """!
    @brief Give the first heater of a problem a rectangular footprint.
    @param p A Problem.
    @param x0 Left in mm.
    @param y0 Bottom in mm.
    @param x1 Right in mm.
    @param y1 Top in mm.
    @return None.
    """
    p.heaters[0].polygon = np.array([(x0 * 1e-3, y0 * 1e-3), (x1 * 1e-3, y0 * 1e-3), (x1 * 1e-3, y1 * 1e-3), (x0 * 1e-3, y1 * 1e-3)])


def _zone_texts(p):
    """!
    @brief The post-run zone warnings of the first heater after a Lumped run at 0.5 mm.
    @param p A Problem.
    @return List of str.
    """
    res = lumped.solve_steady(p, 10, 0.5)
    return [str(w) for w in check_lumped_zones(p, res)]


def test_zone_warnings_name_the_edge_the_offset_the_elongation_and_the_raster():
    """!
    @brief The post-run texts of a zoned part: array across the edge of the footprint (up to 16 % of the rise), off centre, elongated, and a core under ten cells across.
    @return None.
    """
    across = array(5, 1.5, side=24.0, source=12.0)
    for v in across.vias:
        v.x += 5.0e-3                                                         # the array continues past the footprint edge
    texts = _zone_texts(across)
    assert len(texts) == 1 and "past the edge" in texts[0] and "16 %" in texts[0]
    off = array(3, 2.0, side=24.0, source=12.0)
    for v in off.vias:
        v.x += 3.0e-3
    texts = _zone_texts(off)
    assert len(texts) == 1 and "off the centre" in texts[0] and "1 to 5 %" in texts[0]
    elong = array(3, 2.0, side=30.0, source=12.0)
    _rect(elong, 7.0, 11.0, 23.0, 19.0)                                       # 16 x 8 mm, side ratio 2
    texts = _zone_texts(elong)
    assert len(texts) == 1 and "elongated" in texts[0]
    fine = array(3, 0.8, side=24.0, source=12.0)                              # core 2.7 mm: 5 raster cells across at 0.5 mm
    texts = _zone_texts(fine)
    assert len(texts) == 1 and "raster cells across" in texts[0] and "20 % too small" in texts[0]
    assert _zone_texts(array(3, 2.0, side=24.0, source=12.0)) == []           # centred, square, resolved: no zone warning


def test_the_zoned_part_has_no_pre_run_cool_warning_and_the_one_node_part_keeps_it():
    """!
    @brief check_model_limits leaves the group-past-the-edge text out for a part the zone model will split and keeps it for a part that stays one node.
    @return None.
    """
    off = array(3, 2.0, side=24.0, source=12.0)
    for v in off.vias:
        v.x += 3.0e-3
    assert not any("too cool, unsafe" in str(w) for w in check_model_limits(off, ("lumped",), 0.5))
    one_node = array(3, 3.5)                                                  # the core fills the footprint
    _rect(one_node, 5.0, 6.9, 16.0, 14.1)                                     # 11 x 7.2 mm, side ratio 1.53, all nine vias inside
    assert any("too cool, unsafe" in str(w) for w in check_model_limits(one_node, ("lumped",), 0.5))
    assert _zone_texts(one_node) == []                                        # not predicted zoned: the pre-run text stands, nothing is added


def test_a_footprint_covered_by_400_vias_runs_one_node_without_a_zone_warning():
    """!
    @brief A core above 92 % of the footprint (400 vias under a 10 mm part) is the one-node network and raises no zone warning.
    @return None.
    """
    p = array(20, 0.5, side=24.0, source=10.0)
    assert len(p.vias) == 400
    res = lumped.solve_steady(p, 10, 0.5)
    assert res.arrays["zoned_heaters"].tolist() == [[0.0, 0.0]]
    assert check_lumped_zones(p, res) == []
    assert lumped.cell_for(p, 2.0) == 1.0


# ------------------------------------------------------------------------------------------------ the decision is made once, raster-free (review of feature/lumped-zones)

def test_the_decision_does_not_follow_the_raster_of_the_run():
    """!
    @brief The share counted on the fine grid of the user's raster is not raster-free (0.925 at 1.0 mm, 0.916 at 0.75 mm for a 3 x 3 array at 2.35 mm under 8 mm): the
           run must use the decision of will_be_zoned (counted on the fixed 0.5 mm raster), so a part that will_be_zoned keeps one node is one node at every raster.
    @details Before the review the 0.75 mm run zoned this part and its hottest rise stepped from +2.6 % to -1.9 % of the FVM's between 1.0 and 0.75 mm.
    @return None.
    """
    from types import SimpleNamespace
    p = array(3, 2.35, side=24.0, source=8.0)
    assert not lumped.will_be_zoned(p, p.heaters[0])
    b = p.board
    nx = int(round(b.width * 1000.0 / 0.75))
    ns = SimpleNamespace(nx=nx, ny=nx, dx=b.width / nx, dy=b.height / nx)
    assert lumped._fine_core_share(ns, lumped._footprint_coverage(ns, p.heaters[0]), viaconstriction.ViaSet(p)) <= lumped.MAX_CORE   # the raster's own count would zone it
    for cell in (1.0, 0.75, 0.5):
        assert lumped.solve_steady(p, 10, cell).arrays["zoned_heaters"][0, 0] == 0.0
        t, z, r = lumped.step_responses(p, 10, cell, stages=2)
        assert np.isfinite(z).all()
    assert lumped.cell_for(p, 0.75) == 0.75


def test_a_part_predicted_zoned_that_the_raster_keeps_one_node_gets_the_note_after_the_run():
    """!
    @brief A 4 x 4 array at 1.7 mm under an 8 mm part: the fine count says zoned (0.82), the 0.5 mm raster counts 0.94 and keeps one node. The run is at 0.5 mm, one node,
           and the post-run check says that the footprint was kept as one node (the pre-run note announced the split).
    @return None.
    """
    p = array(4, 1.7, side=24.0, source=8.0)
    assert lumped.will_be_zoned(p, p.heaters[0]) and lumped.cell_for(p, 2.0) == 0.5
    pre = [str(w) for w in check_model_limits(p, ("lumped",), 2.0)]
    assert any("splits this footprint into the core of the vias" in w for w in pre)
    res = simulate(p, SolverOptions(models=("lumped",), cell_mm=2.0)).results["lumped"]
    assert res.arrays["zoned_heaters"][0, 0] == 0.0
    post = [str(w) for w in check_lumped_zones(p, res)]
    assert any("kept as one node" in w for w in post)


def test_an_outline_board_is_decided_on_its_equivalent_rectangle():
    """!
    @brief The Lumped model solves the rectangle of the same area of a board with an outline, whose via positions are scaled: will_be_zoned decides on that rectangle, so the
           pre-run warnings, the raster and the network agree.
    @return None.
    """
    p = array(3, 3.0, side=30.0, source=10.0)
    w = p.board.width
    p.board.outline = np.array([(0.0, 0.0), (w, 0.0), (w, w), (0.6 * w, w), (0.0, 0.6 * w)])    # a corner cut off: positions scaled by 0.938, the pitch 3.0 -> 2.81 mm
    eq, s = p.equivalent_rectangle()
    assert s < 1.0
    # Counted on the original box the share is 0.948 (one node); on the rectangle the model solves it is 0.837 (zoned)
    assert lumped.will_be_zoned(eq, eq.heaters[0]) and lumped.will_be_zoned(p, p.heaters[0])
    res = simulate(p, SolverOptions(models=("lumped",), cell_mm=2.0)).results["lumped"]
    assert bool(res.arrays["zoned_heaters"][0, 0]) == lumped.will_be_zoned(p, p.heaters[0])


def test_the_profile_outside_a_zoned_footprint_starts_at_the_rest_not_at_the_core():
    """!
    @brief Outside the footprint the map (and the other heaters' cross-heating) interpolates the radial profile from A, the edge of the footprint, to the rings; the core C is
           inside and is left out (before the review the interval from the footprint to ring 1 was read from C).
    @return None.
    """
    p = array(3, 2.0, side=24.0, source=12.0)
    net, cov, rn = _network(p)
    res = lumped.solve_steady(p, 10, 0.5)
    out = (cov <= 0) & (rn["dist"] > 0)
    keep = np.r_[0, 2:rn["R"]]
    want = np.interp(rn["dist"][out], rn["rho"][keep], rn["theta"][0][keep])
    assert np.allclose(res.T[0][out] - p.board.ambient, want, rtol=0, atol=1e-12)
    wrong = np.interp(rn["dist"][out], rn["rho"], rn["theta"][0])
    assert np.max(np.abs(wrong - want)) > 1e-3                                  # the old reading differs where a cell lies between the footprint and ring 1


def test_the_frames_of_a_profile_paint_the_core_like_the_steady_map():
    """!
    @brief The frames of the profile runner (the peak map of a run with a power profile) paint the core of a zoned footprint with node C, as the steady map does; at the
           steady state of a constant power the frame equals the steady field.
    @return None.
    """
    p = array(3, 2.0, side=24.0, source=12.0)
    ad = lumped._LumpedAdapter(p, 10, 0.5)
    ad.steppers = [lumped._Stepper(s, 1.0) for s in ad.systems]
    states = [np.zeros(len(s["C"])) for s in ad.systems]
    for _ in range(60):
        states = ad.advance(states, 1.0e4, [p.heaters[0].power])
    frame = ad.frame(states)
    steady = lumped.solve_steady(p, 10, 0.5)
    assert np.allclose(frame, steady.T, rtol=0, atol=1e-6)
