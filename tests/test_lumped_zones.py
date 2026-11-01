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

from pcbthermal import viaconstriction
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
