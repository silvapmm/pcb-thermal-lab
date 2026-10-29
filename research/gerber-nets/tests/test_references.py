#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_references.py
@brief The prototypes against references that do not share their assumptions (study_references.py, README section "Review"): the corner of an L bend, a ring sector, an exact
       series network, a current split of known answer and the closed form of the electro-thermal loop.
"""

import math

import numpy as np
import pytest

import joule
import study_references as sr


def test_l_bend_corner_counts_0_559_squares():
    """!@brief An L bend 20 pixels wide has the squares of its legs plus 0.559 for the corner, within 0.1 %. @return None."""
    strip, measured, expected = sr.strip_and_bend(20)
    assert strip == pytest.approx(1.0, rel=1e-9)
    assert measured == pytest.approx(expected, rel=1e-3)


def test_ring_sector_converges_to_its_closed_form():
    """!@brief A ring sector (current round it) converges to Rs theta / ln(ro / ri) at first order: about 4 % high at 40 pixels across, 2 % at 80. @return None."""
    coarse, fine = sr.ring_sector(0.05, "4"), sr.ring_sector(0.025, "4")
    assert 1.0 < fine < coarse < 1.05
    assert 2 * fine - coarse == pytest.approx(1.0, abs=0.01)                 # Richardson extrapolation at first order


def test_pdn_equals_the_series_circuit_of_its_pieces():
    """!@brief The load voltage of the link scenario equals 5 - I (R_A + R_link + R_B) with R_A and R_B solved alone by joule.py, within 1 uV. @return None."""
    import study_pdn_links as spl
    mask, r, t = spl.scenario()
    ra = joule.solve_net(mask, spl.RS, t["vin"], t["out_pad"], 1.0)[0]
    rb = joule.solve_net(mask, spl.RS, t["rect_a"], t["load"], 1.0)[0]
    assert float(np.nanmean(r["V"][t["load"]])) == pytest.approx(5.0 - 1.5 * (ra + 0.1 + rb), abs=1e-6)
    assert r["p_copper"] == pytest.approx(2.25 * (ra + rb), rel=1e-6)


def test_current_divides_as_the_conductances():
    """!@brief Two strips 4 and 8 pixels wide between common terminals carry 1 and 2 A of 3 A. @return None."""
    import pdn
    m = np.zeros((14, 40), bool)
    m[0:4, :] = True
    m[6:14, :] = True
    a = np.zeros_like(m); b = np.zeros_like(m)
    a[:, 0] = True; b[:, -1] = True
    q = pdn.solve(m, 0.01, {"a": a, "b": b}, [("vsource", "a", 1.0), ("isink", "b", 3.0)])["q"]
    assert math.sqrt(q[0:4].sum() / (0.01 * 39 / 4)) == pytest.approx(1.0, rel=1e-6)
    assert math.sqrt(q[6:14].sum() / (0.01 * 39 / 8)) == pytest.approx(2.0, rel=1e-6)


def test_electro_thermal_loop_meets_its_closed_form_and_detects_runaway():
    """!@brief The fixed point T = Ta + Rth I^2 R(T) through joule.py equals the closed form below runaway and finds no solution above it (alpha Rth I^2 R20 >= 1). @return None."""
    slope, exact, got, _ = sr.electro_thermal(50.0, 5.0)
    assert slope < 1 and got == pytest.approx(exact, abs=1e-6)
    slope, exact, got, _ = sr.electro_thermal(100.0, 7.5)
    assert slope > 1 and exact is None and got is None
