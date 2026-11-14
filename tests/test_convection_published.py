#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_convection_published.py
@brief The convection correlations against the printed examples and tables of Lienhard and Lienhard, A Heat Transfer Textbook (audit of 2.8.0, REVIEW_L1L5.md section 5, items T1 to T6).
@details Each test says which printed number it holds and what a failure would mean. Air properties are the program's own fits (Sutherland-type), so the examples
         agree with the printed values by a stated small offset (the air fit), not exactly; the coded formulas with the book's own properties agree to the printed digits.
"""

import math

import pytest

from pcbthermal import convection as cv


def test_t1_lienhard_example_8_1_vertical_plate():
    """!
    @brief Lienhard and Lienhard, Example 8.1 (pp 419 to 421): a vertical plate 0.30 m high at 50 degC in air at 20 degC; printed Nu 47.33 and h 4.22 W/m2K.
    @details The program's laminar form (Churchill and Chu eq. 8.13a) with its own air fit gives 4.2327 W/m2K, +0.3 % of the printed 4.22 (a 0.67 % air-k offset and a
             -0.26 % Nu offset); tolerance 0.5 %. The coded formula with the book's properties (Pr 0.710, Ra 6.78e7) gives Nu 47.34 (printed 47.33, tolerance 0.02): the formula itself is exact.
             The general form (eq. 8.13b) reads 4.861 W/m2K (+15 % of the laminar; no printed value, the number pins the documented +15 %), tolerance 0.01.
             A failure of the first means the air fit or the laminar form moved; of the second, that the constants of eq. 8.13a were changed.
    @return None.
    """
    h, ra = cv.h_natural_vertical(50.0, 20.0, 0.30, "laminar")
    assert h == pytest.approx(4.22, rel=0.005)
    assert h == pytest.approx(4.2327, abs=0.001)
    pr = 0.710
    nu = 0.68 + 0.670 * 6.78e7 ** 0.25 / (1.0 + (0.492 / pr) ** (9.0 / 16.0)) ** (4.0 / 9.0)   # the coded formula with the book's Pr and Ra
    assert nu == pytest.approx(47.33, abs=0.02)   # 47.34 with the rounded Ra 6.78e7
    hg, _ = cv.h_natural_vertical(50.0, 20.0, 0.30, "general")
    assert hg == pytest.approx(4.86, abs=0.01)


def test_t2_lienhard_example_6_5_forced_flat_plate():
    """!
    @brief Lienhard and Lienhard, Example 6.5 (pp 310 to 311): a flat plate 0.5 m long at 110 degC in air at 20 degC and 15 m/s; printed Re 384 600, Nu 366.2, h 21.4 W/m2K.
    @details The program (laminar mean Nu = 0.664 Re^(1/2) Pr^(1/3)) gives 21.388 W/m2K, within 0.5 % of the printed 21.4. The coded formula with the book's Re 384 600, Pr 0.703
             reproduces Nu 366.2 +- 0.1. A failure means the laminar form or the air fit moved.
    @return None.
    """
    assert cv.h_forced(110.0, 20.0, 15.0, 0.5) == pytest.approx(21.4, rel=0.005)
    assert cv.h_forced(110.0, 20.0, 15.0, 0.5) == pytest.approx(21.388, abs=0.01)
    assert 0.664 * math.sqrt(384600.0) * 0.703 ** (1.0 / 3.0) == pytest.approx(366.2, abs=0.1)


def test_t3_face_down_constant_and_fujii_imura():
    """!
    @brief The face turned down: Nu = 0.475 Ra^(1/5) on L = A/P (Goldstein-Lau average, Yovanovich and Jafarpur 1993 p 8; the 1/5 exponent of Lienhard eq. 8.38).
    @details DOWN_COEFFICIENT is exactly 0.475 and the exponent exactly 1/5 (the maintainer's decision of 2026-11-12 keeps both). The Fujii-Imura form on A/P,
             0.58/2 * 8^(1/5) = 0.4396, lies within 8 % below 0.475 (the documented relation). A failure means the decided law was changed without a decision.
    @return None.
    """
    assert cv.DOWN_COEFFICIENT == 0.475 and cv.DOWN_EXPONENT == 0.2
    fujii = 0.58 / 2.0 * 8.0 ** 0.2
    assert fujii == pytest.approx(0.4396, abs=1e-4)
    assert 0.92 * cv.DOWN_COEFFICIENT <= fujii <= cv.DOWN_COEFFICIENT


def test_t4_forced_transition_is_continuous():
    """!
    @brief The laminar-to-mixed switch of h_forced at Re = 5e5: Nu = (0.037 Re^0.8 - 871) Pr^(1/3) against 0.664 Re^(1/2) Pr^(1/3) (Lienhard Example 6.11, p 334).
    @details The constant 871 equals 0.037 Re_t^0.8 - 0.664 Re_t^(1/2) at Re_t = 5e5 to 0.5 (871.32). h_forced just below and above Re 5e5 agrees within 0.1 %. A failure
             means a step in the coefficient of a fast-air board at the transition.
    @return None.
    """
    assert 0.037 * (5e5) ** 0.8 - 0.664 * (5e5) ** 0.5 == pytest.approx(871.0, abs=0.5)
    ta, ts, length = 20.0, 60.0, 1.0
    nu_air = cv.air_properties(0.5 * (ts + ta))["nu"]
    below = cv.h_forced(ts, ta, 5e5 * (1 - 1e-6) * nu_air / length, length)
    above = cv.h_forced(ts, ta, 5e5 * (1 + 1e-6) * nu_air / length, length)
    assert above == pytest.approx(below, rel=1e-3)


# Lienhard, Table A.6 (air at 1 atm, printed p 755): T in K, k in W/mK, nu in m2/s, Pr (the 250 K row was not transcribed in the study scripts)
LIENHARD_A6 = [(300.0, 0.0264, 1.575e-5, 0.707), (350.0, 0.0300, 2.069e-5, 0.702), (400.0, 0.0335, 2.613e-5, 0.699)]


@pytest.mark.parametrize("row", LIENHARD_A6)
def test_t5_air_properties_against_table_a6(row):
    """!
    @brief The program's air fits against Lienhard Table A.6 (p 755), 300, 350 and 400 K: k, nu and Pr each within 2.5 % of the printed row.
    @details Measured: k -0.5 to +0.5 %, nu -0.4 to -0.9 %, Pr +0.1 to -2.2 %. Replaces the Incropera values from memory. A failure means an air fit constant moved.
    @param row Tuple (T in K, k in W/mK, nu in m2/s, Pr).
    @return None.
    """
    t_k, k, nu, pr = row
    p = cv.air_properties(t_k - 273.15)
    assert p["k"] == pytest.approx(k, rel=0.025)
    assert p["nu"] == pytest.approx(nu, rel=0.025)
    assert p["pr"] == pytest.approx(pr, rel=0.025)
    assert p["beta"] == pytest.approx(1.0 / t_k, rel=1e-9)


def test_t6_radiation_linearisation_limit():
    """!
    @brief Lienhard eq. 2.31: h_r -> 4 eps sigma T_m^3 when the surface temperature approaches the surroundings.
    @details At T_m = 300 K, black, delta T -> 0 (2 mK apart) the coefficient is 4 sigma 300^3 = 6.124 W/m2K within 0.1 %. A failure means the linearisation lost a factor.
    @return None.
    """
    h = cv.h_radiation(300.0 - 273.15 + 1e-3, 300.0 - 273.15 - 1e-3, 1.0)
    assert h == pytest.approx(4.0 * cv.SIGMA * 300.0 ** 3, rel=1e-3)
    assert h == pytest.approx(6.12, rel=2e-3)
