#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_sources.py
@brief Tests of research/fin-channel-sources/lib/sources.py: limits and closed forms of the source formulas and the reproduced published numbers.
@details Run: .venv/bin/python -m pytest -q research/fin-channel-sources/tests
"""

import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import sources as S                                       # noqa: E402
import channel as ch                                      # noqa: E402


def test_ytm_limits():
    """!
    @brief Equation 29 of YTM tends to Ra_b/24 (within 2 %) for a closing channel and to 0.60 Ra_b^(1/4) for wide plates; it stays within 2 % of equation 21 of the review.
    @return None.
    """
    assert abs(S.ytm_parallel_plates_nu(1e-3) * 24.0 / 1e-3 - 1.0) < 0.02
    assert abs(S.ytm_parallel_plates_nu(1e8) / 1e8 ** 0.25 - 0.60) < 1e-6
    for r in np.logspace(-2, 6, 50):
        assert abs(S.ytm_parallel_plates_nu(r) / ch.nu_bcr(r) - 1.0) < 0.02


def test_elenbaas_boundary_layer_limit_is_060():
    """!
    @brief The Elenbaas formula (equation 8 of the review) has the limit 35^(3/4) / 24 = 0.600 at large Ra_b, as printed in YTM equation 26 (0.6).
    @return None.
    """
    assert abs(ch.nu_elenbaas(1e9) / 1e9 ** 0.25 - 35.0 ** 0.75 / 24.0) < 1e-3
    assert abs(35.0 ** 0.75 / 24.0 - 0.6) < 0.001


def test_fig11_conversion():
    """!
    @brief The plot values of Figure 11 convert to the Ra_b range of Elenbaas (0.1 to 1e5) and follow the correlations to within 15 % rms.
    @return None.
    """
    ra, nu = S.elenbaas_data_from_fig11()
    assert len(ra) == 26 and ra.min() > 0.1 and ra.max() < 1e5
    pred = np.array([ch.nu_bcr(r) for r in ra])
    assert math.sqrt(np.mean(((pred - nu) / nu) ** 2)) < 0.15


def test_bik_equation_13_is_equation_21():
    """!
    @brief Equation 13 of Bar-Cohen, Iyengar and Kraus equals equation 21 of the review (576 = 24^2, 2.873 = 0.59^-2 to 4 digits).
    @return None.
    """
    for r in np.logspace(-1, 5, 40):
        assert abs(S.bik_nu_fin(r) / ch.nu_bcr(r) - 1.0) < 1e-4


def test_bik_published_numbers():
    """!
    @brief The published h_a of Figure 2 (52.4 W/m2K near 8 mm) and Figure 4 (198 W/m2K) are reproduced with a 45 degC ambient (within 1 % and 2 %).
    @return None.
    """
    so, ha = S.optimum_of_ha(25.0, 1e-3, 0.045, 0.1, 0.1, 200.0, 45.0)
    assert abs(so * 1e3 - 8.0) < 0.5 and abs(ha / 52.4 - 1.0) < 0.01
    lm = S.bik_least_material(25.0, 9e-3, 0.1, 0.1, 200.0, 45.0)
    assert abs(lm["ha"] / 198.0 - 1.0) < 0.02 and abs(lm["eta"] - 0.6267) < 1e-3


def test_bik_array_energy_and_limits():
    """!
    @brief The array heat grows with the spacing at first and h_a of a very wide spacing tends to the base coefficient of the wide-spacing limit.
    @return None.
    """
    a = [S.bik_array(25.0, s * 1e-3, 1e-3, 0.045, 0.1, 0.1, 200.0, 45.0)["ha"] for s in (2, 4, 6, 8)]
    assert a == sorted(a)
    wide = S.bik_array(25.0, 0.5, 1e-3, 0.045, 0.1, 0.1, 200.0, 45.0)["ha"]
    assert wide < 12.0


def test_optimum_constant_is_derived_not_remembered():
    """!
    @brief Maximising Nu_b / b^2 of equation 13 gives 2.7156 (the number of equation 17 of the paper, 2.66, is a different one).
    @return None.
    """
    k, ra, nu = ch.optimum_spacing_constants(ch.nu_bcr)
    assert abs(k - 2.7156) < 1e-3 and abs(nu - 1.308) < 1e-3
    assert abs(k - 2.66) > 0.04


def test_ostrach_table_and_second_method():
    """!
    @brief The similarity solution reproduces Table I of NACA 1111 for Pr 0.72, 1, 2, 10, 100 (0.02 %) and the shooting method agrees with the collocation.
    @return None.
    """
    for pr in (0.72, 1.0, 2.0, 10.0, 100.0):
        assert abs(S.ostrach_h0(pr) / S.OSTRACH_TABLE_I[pr] - 1.0) < 2e-4
    fpp, h = S.ostrach_h0_shooting(1.0)
    assert abs(h - S.ostrach_h0(1.0)) < 1e-6 and abs(fpp - 0.6422) < 1e-3


def test_ostrach_prandtl_001_row_differs_from_the_table():
    """!
    @brief Regression note: for Pr 0.01 two independent methods give 0.0806, the table value (0.0812) is 0.75 % higher.
    @return None.
    """
    assert abs(S.ostrach_h0(0.01) - 0.08059) < 2e-4
    assert abs(S.ostrach_h0_shooting(0.01)[1] - S.ostrach_h0(0.01)) < 1e-5


def test_churchill_chu_prandtl_function_matches_similarity_solution():
    """!
    @brief 0.670 / [1 + (0.492/Pr)^(9/16)]^(4/9) agrees with (4/3) (-H'(0)) 2^(-1/2) Pr^(-1/4) within 0.5 % for Pr 0.01 to 100.
    @return None.
    """
    for pr in (0.01, 0.72, 1.0, 10.0, 100.0):
        assert abs(S.churchill_prandtl_function(pr) / S.ostrach_prandtl_function(pr) - 1.0) < 0.005


def test_horizontal_array_geometry_and_uniform_h():
    """!
    @brief Areas of array 5 (14 fins, S 5.55, H 14, L 100 mm), a plausible uniform coefficient and a fin efficiency close to 1 for aluminium.
    @return None.
    """
    a = S.ENCIT_ARRAYS[5]
    g = S.array_geometry(a)
    assert abs(g["sides"] - 2 * 14 * 0.014 * 0.1) < 1e-12
    u = S.uniform_h_array(a, 40.0)
    assert 5.0 < u["h_mean"] < 12.0 and u["eta"] > 0.97


def test_phi_form_lowers_the_uniform_coefficient():
    """!
    @brief The channel fraction can only lower the coefficient, and the narrow gap more than the wide one.
    @return None.
    """
    n = S.ENCIT_ARRAYS[5]
    w = S.ENCIT_ARRAYS[2]
    un, pn = S.uniform_h_array(n, 40.0), S.uniform_h_array(n, 40.0, channel_length=0.1)
    uw, pw = S.uniform_h_array(w, 40.0), S.uniform_h_array(w, 40.0, channel_length=0.1)
    assert pn["h_mean"] < un["h_mean"] and pw["h_mean"] <= uw["h_mean"] + 1e-12
    assert pn["phi"] < pw["phi"]


def test_program_fin_count_is_the_fin_ratio_of_the_block():
    """!
    @brief Regression of the review: the "program" coefficient of the horizontal arrays is the heat of `pcbthermal.blocks.fin_ratio` (W/p fins), not the real fins.
    @details The first version put the program's coefficient on the 7 or 14 real fins while the program's block carries W/p = 6.12 or 13.2; the 14.35 mm gap read 0.92
             instead of 1.02 (measured over predicted against predicted over measured, mean).
    @return None.
    """
    from pcbthermal import convection
    a = S.ENCIT_ARRAYS[2]
    u = S.uniform_h_array(a, 40.0)
    act = S.uniform_h_array(a, 40.0, fins="actual")
    g = S.array_geometry(a)
    # Independent route: the program's own face coefficient (A/P of the 100 x 100 mm base is 25 mm) and its fin ratio
    h = convection.h_natural_horizontal(60.0, 20.0, 0.025, True)[0]
    p = (a["s"] + a["t"]) * 1e-3
    hc = (a["h"] + 0.5 * a["t"]) * 1e-3
    m = math.sqrt(2.0 * h / (200.0 * a["t"] * 1e-3))
    ratio = (1.0 - a["t"] * 1e-3 / p) + 2.0 * hc * math.tanh(m * hc) / (m * hc) / p
    q = h * ratio * g["w"] * g["l"] * 40.0
    assert abs(u["h_mean"] / (q / (g["total"] * 40.0)) - 1.0) < 1e-3
    assert act["h_mean"] > u["h_mean"] * 1.05          # the real array has 7 fins, the block 6.12
    try:
        S.uniform_h_array(a, 40.0, fins="other")
        raise AssertionError("an unknown fins value must raise")
    except ValueError:
        pass
