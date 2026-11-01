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
        h.polygon = [(x + shift, y) for x, y in h.polygon]
    for v in m.vias:
        v.x = w - (v.x + shift)
    for h in m.heaters:
        h.polygon = [(w - (x + shift), y) for x, y in h.polygon]
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
