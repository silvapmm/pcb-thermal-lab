#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_convection_published.py
@brief The convection correlations against the printed examples and tables of Lienhard and Lienhard, A Heat Transfer Textbook (audit of 2.8.0, REVIEW_L1L5.md section 5, items T1 to T6).
@details Each test says which printed number it holds and what a failure would mean. Air properties are the program's own fits (Sutherland-type), so the examples
         agree with the printed values by a stated small offset (the air fit), not exactly; the coded formulas with the book's own properties agree to the printed digits.
"""

import pytest

from pcbthermal import convection as cv


def test_t1_lienhard_example_8_1_vertical_plate(monkeypatch):
    """!
    @brief Lienhard and Lienhard, Example 8.1 (printed p 421, PDF p 435): a vertical plate 0.30 m high at 50 degC in air at 20 degC; printed Ra 6.78e7, Nu 47.33 and h 4.22 W/m2K.
    @details The program's laminar form (Churchill and Chu eq. 8.13a) with its own air fit gives 4.2327 W/m2K, +0.3 % of the printed 4.22 (a 0.67 % air-k offset and a
             -0.26 % Nu offset); tolerance 0.5 % against the print and 0.001 W/m2K on the program's value. With the book's own properties put in place of the air fit
             (Pr 0.710, nu 1.643e-5, alpha 2.315e-5, k 0.02672, beta 0.00325, as printed), the program's h_natural_vertical gives Nu 47.36 and h 4.218 (printed 47.33 and 4.22;
             the 0.05 % is the program's g 9.80665 against the book's 9.8): the coded formula itself is checked, not a copy of it.
             The general form (eq. 8.13b) reads 4.861 W/m2K (+15 % of the laminar; no printed value, the number pins the documented +15 %), tolerance 0.01.
             A failure of the first means the air fit or the laminar form moved; of the book-property check, that the constants of eq. 8.13a were changed.
    @param monkeypatch pytest fixture (the book's air properties).
    @return None.
    """
    h, ra = cv.h_natural_vertical(50.0, 20.0, 0.30, "laminar")
    assert h == pytest.approx(4.22, rel=0.005)
    assert h == pytest.approx(4.2327, abs=0.001)
    hg, _ = cv.h_natural_vertical(50.0, 20.0, 0.30, "general")
    assert hg == pytest.approx(4.86, abs=0.01)
    book = {"k": 0.02672, "nu": 1.643e-5, "alpha": 2.315e-5, "pr": 0.710, "beta": 0.00325}
    monkeypatch.setattr(cv, "air_properties", lambda t_film_c: dict(book))
    hb, rab = cv.h_natural_vertical(50.0, 20.0, 0.30, "laminar")
    assert rab == pytest.approx(6.78e7, rel=0.002)
    assert hb * 0.30 / book["k"] == pytest.approx(47.33, abs=0.05)
    assert hb == pytest.approx(4.22, abs=0.005)


def test_t2_lienhard_example_6_5_forced_flat_plate(monkeypatch):
    """!
    @brief Lienhard and Lienhard, Example 6.5 (printed pp 310 to 311, PDF pp 324 to 325): a flat plate 0.5 m long at 110 degC in air at 20 degC and 15 m/s; printed Re 384 600, Nu 366.2, h 21.4 W/m2K.
    @details The program (laminar mean Nu = 0.664 Re^(1/2) Pr^(1/3)) gives 21.388 W/m2K, within 0.5 % of the printed 21.4 (and 0.01 W/m2K of its own value). With the book's
             properties put in place of the air fit (Pr 0.703, nu 1.95e-5, k 0.0292) the program's h_forced gives Nu 366.16 (printed 366.2, tolerance 0.1) and h 21.38.
             A failure means the laminar form or the air fit moved.
    @param monkeypatch pytest fixture (the book's air properties).
    @return None.
    """
    assert cv.h_forced(110.0, 20.0, 15.0, 0.5) == pytest.approx(21.4, rel=0.005)
    assert cv.h_forced(110.0, 20.0, 15.0, 0.5) == pytest.approx(21.388, abs=0.01)
    book = {"k": 0.0292, "nu": 1.95e-5, "alpha": 1.95e-5 / 0.703, "pr": 0.703, "beta": 1.0 / 338.15}
    monkeypatch.setattr(cv, "air_properties", lambda t_film_c: dict(book))
    hb = cv.h_forced(110.0, 20.0, 15.0, 0.5)
    assert hb * 0.5 / book["k"] == pytest.approx(366.2, abs=0.1)
    assert hb == pytest.approx(21.4, abs=0.05)


def test_t3_face_down_constant_and_fujii_imura():
    """!
    @brief The face turned down: Nu = 0.475 Ra^(1/5) on L = A/P (Goldstein-Lau average of the Pr 0.71 results, printed in Yovanovich and Jafarpur 1993 p 8; the 1/5 exponent of
           Lienhard eq. 8.38, printed p 437, PDF p 451).
    @details DOWN_COEFFICIENT is exactly 0.475 and the exponent exactly 1/5 (the maintainer's decision of 2026-11-12 keeps both), and h_natural_horizontal uses them: for a
             25 mm A/P face at 60 degC in air at 20 degC it returns 0.475 Ra^(1/5) k / L with the program's own Ra and k (a code path that ignored the constants would fail here).
             Fujii and Imura (eq. 8.38) give 0.58 Ra^(1/5) on the WIDTH W of a two-dimensional strip (end effects suppressed), whose A/P is W/2; on A/P that is
             0.58/2 * 8^(1/5) = 0.4396, 7.4 % below 0.475 (the documented relation, bound 8 %). A failure means the decided law was changed without a decision.
    @return None.
    """
    assert cv.DOWN_COEFFICIENT == 0.475 and cv.DOWN_EXPONENT == 0.2
    fujii = 0.58 / 2.0 * 8.0 ** 0.2
    assert fujii == pytest.approx(0.4396, abs=1e-4)
    assert 0.92 * cv.DOWN_COEFFICIENT <= fujii <= cv.DOWN_COEFFICIENT
    ts, ta, length = 60.0, 20.0, 0.025
    h, ra = cv.h_natural_horizontal(ts, ta, length, False)
    props = cv.air_properties(0.5 * (ts + ta))
    assert ra == pytest.approx(cv.rayleigh(ts - ta, length, props), rel=1e-12)
    assert h == pytest.approx(0.475 * ra ** 0.2 * props["k"] / length, rel=1e-12)
    t_cold = ta - (ts - ta)                                                         # a face 40 K colder than the air, turned up: the stable layer too
    h_cold_up, ra_cold = cv.h_natural_horizontal(t_cold, ta, length, True)
    assert h_cold_up == pytest.approx(0.475 * ra_cold ** 0.2 * cv.air_properties(0.5 * (t_cold + ta))["k"] / length, rel=1e-12)


def test_t4_forced_transition_is_continuous():
    """!
    @brief The laminar-to-mixed switch of h_forced at Re = 5e5: Nu = (0.037 Re^0.8 - 871) Pr^(1/3) against 0.664 Re^(1/2) Pr^(1/3).
    @details The mixed form with 871 is the textbook form of Incropera and DeWitt (from memory, status M; it is not printed in any source of the local library). Lienhard
             Example 6.11 (printed p 336, PDF p 350, eqn. 6.120) prints the same abrupt-switch construction with a Pr^0.6 turbulent term, so it is the idea and not the
             constant that has a printed source. The first assertion is arithmetic only (871 equals 0.037 Re_t^0.8 - 0.664 Re_t^(1/2) at Re_t = 5e5 to 0.5, 871.32) and
             cannot fail on a program change; the program check is the second: h_forced just below and above Re 5e5 agrees within 0.1 %. A failure means a step in the
             coefficient of a fast-air board at the transition (a changed 871, 0.037 or exponent).
    @return None.
    """
    assert 0.037 * (5e5) ** 0.8 - 0.664 * (5e5) ** 0.5 == pytest.approx(871.0, abs=0.5)
    ta, ts, length = 20.0, 60.0, 1.0
    nu_air = cv.air_properties(0.5 * (ts + ta))["nu"]
    below = cv.h_forced(ts, ta, 5e5 * (1 - 1e-6) * nu_air / length, length)
    above = cv.h_forced(ts, ta, 5e5 * (1 + 1e-6) * nu_air / length, length)
    assert above == pytest.approx(below, rel=1e-3)


# Lienhard, Table A.6 (air at 1 atm, printed p 755, PDF p 769, checked on the page image): T in K, k in W/mK, nu in m2/s, Pr; then the program's own k, nu, Pr at that T
LIENHARD_A6 = [(250.0, 0.0226, 1.135e-5, 0.715, 0.022284, 1.13257e-5, 0.72265), (300.0, 0.0264, 1.575e-5, 0.707, 0.026268, 1.56890e-5, 0.70767),
               (350.0, 0.0300, 2.069e-5, 0.702, 0.030062, 2.05605e-5, 0.69460), (400.0, 0.0335, 2.613e-5, 0.699, 0.033678, 2.58963e-5, 0.68332)]


@pytest.mark.parametrize("row", LIENHARD_A6)
def test_t5_air_properties_against_table_a6(row):
    """!
    @brief The program's air fits against Lienhard Table A.6 (p 755), 250, 300, 350 and 400 K: k, nu and Pr each within 2.5 % of the printed row, and pinned to their own values.
    @details Measured against the print: k -1.4 to +0.5 %, nu -0.2 to -0.9 %, Pr +1.1 to -2.2 % (the 400 K Pr is the closest to the 2.5 % bound). Replaces the Incropera values
             from memory. The 2.5 % band states the documented agreement but would hide a 1 to 2 % change of a fit constant, so each value is also pinned to the program's
             own number within 0.1 %. A failure of the band means the fit left the table; of the pin, that an air fit constant moved (re-baseline with the reason).
    @param row Tuple (T in K, printed k in W/mK, printed nu in m2/s, printed Pr, program k, program nu, program Pr).
    @return None.
    """
    t_k, k, nu, pr, k_p, nu_p, pr_p = row
    p = cv.air_properties(t_k - 273.15)
    assert p["k"] == pytest.approx(k, rel=0.025)
    assert p["nu"] == pytest.approx(nu, rel=0.025)
    assert p["pr"] == pytest.approx(pr, rel=0.025)
    assert (p["k"], p["nu"], p["pr"]) == pytest.approx((k_p, nu_p, pr_p), rel=1e-3)
    assert p["beta"] == pytest.approx(1.0 / t_k, rel=1e-9)


def test_t6_radiation_linearisation_limit():
    """!
    @brief Lienhard eq. 2.31 (printed p 72, PDF p 86): h_r -> 4 eps sigma T_m^3 when the surface temperature approaches the surroundings.
    @details At T_m = 300 K, black, delta T -> 0 (2 mK apart) the coefficient is 4 sigma 300^3 = 6.124 W/m2K within 0.1 %. A failure means the linearisation lost a factor.
    @return None.
    """
    h = cv.h_radiation(300.0 - 273.15 + 1e-3, 300.0 - 273.15 - 1e-3, 1.0)
    assert h == pytest.approx(4.0 * cv.SIGMA * 300.0 ** 3, rel=1e-3)
    assert h == pytest.approx(6.12, rel=2e-3)
