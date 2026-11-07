#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_s0_discrepancy_numbers.py
@brief Tests of study S0: every number that README sections 8 and 9 quote from the second reading pass is produced by a script of the folder and fails here if it moves.
@details Run: .venv/bin/python -m pytest -q research/theory-sources/tests/test_s0_discrepancy_numbers.py (from the repository root; about 5 s).
"""

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import study_forced_and_air_sources as fa  # noqa: E402
import study_horizontal_face_limits as hf  # noqa: E402
import study_strip_table_and_sor_omega as st  # noqa: E402
import study_via_formulas_checks as vf  # noqa: E402


def test_up_face_against_yovanovich_jafarpur_bounds():
    """!@brief README 9.1: 3 to 12 % below the upper bound on 40 x 30 mm, +4, +13, +20, +24 % on 60 x 40, 100 x 80, 160 x 100 (40 K) and 300 x 200; Ra on A/P below 2.2e4 up to 100 x 80 at 20 K."""
    rows = {r["plate"]: r for r in hf.face_limits()}
    for plate, pct in (((40, 30, 5), -12), ((40, 30, 20), -3), ((60, 40, 20), 4), ((100, 80, 20), 13), ((160, 100, 40), 20), ((300, 200, 20), 24)):
        assert abs(100 * rows[plate]["ratio_upper"] - pct) < 0.6, plate
    assert not rows[(100, 80, 20)]["inside"] and not rows[(60, 40, 20)]["inside"] and rows[(160, 100, 40)]["inside"]
    assert 2.8e2 < rows[(40, 30, 5)]["ra_ap"] < 3.0e2 and 1.7e4 < rows[(100, 80, 20)]["ra_ap"] < 1.9e4


def test_board_impact_of_the_yj_bound(monkeypatch):
    """!@brief README 9.1: board maximum -1.1, +0.6, +1.0, +0.7 % and mean -2.0, +1.8, +4.0, +3.9 % on the four canonical boards (FVM 2 mm).
    @param monkeypatch pytest fixture. The README numbers were taken with the 2.5.x lower-face law (0.27 Ra^(1/4)); 2.6.0 (fix/face-down-convection) uses 0.475 Ra^(1/5), which moves
           the baseline of the comparison: with the 2.5.x law restored the README numbers are reproduced; with the 2.6.0 law the bound's effect is +0.35, +1.04, +1.09, +0.68 % on
           the maximum and +0.55, +3.16, +4.65, +4.06 % on the mean (asserted below)."""
    original = hf.cv.h_natural_horizontal
    with monkeypatch.context() as m:
        m.setattr(hf.cv, "DOWN_COEFFICIENT", 0.27)
        m.setattr(hf.cv, "DOWN_EXPONENT", 0.25)
        rows = hf.board_impact()
        for r, dmax, dmean in zip(rows, (-1.1, 0.6, 1.0, 0.7), (-2.0, 1.8, 4.0, 3.9)):
            assert abs(100 * r["d_max"] - dmax) < 0.06 and abs(100 * r["d_mean"] - dmean) < 0.06, r["board"]
    rows = hf.board_impact()
    for r, dmax, dmean in zip(rows, (0.35, 1.04, 1.09, 0.68), (0.55, 3.16, 4.65, 4.06)):
        assert abs(100 * r["d_max"] - dmax) < 0.06 and abs(100 * r["d_mean"] - dmean) < 0.06, r["board"]
    # The in-memory replacement must be undone, or every later test would run on the substitute
    assert hf.cv.h_natural_horizontal is original


def test_air_properties_against_lienhard_a6():
    """!@brief README 9.1: k -0.5..+0.5 %, nu -0.4..-0.9 %, Pr +0.1, -1.1, -2.2 % at 300, 350, 400 K."""
    r = fa.air_vs_table()
    assert [round(100 * x["dk"], 1) for x in r] == [-0.5, 0.2, 0.5]
    assert [round(100 * x["dnu"], 1) for x in r] == [-0.4, -0.6, -0.9]
    assert [round(100 * x["dpr"], 1) for x in r] == [0.1, -1.1, -2.2]


def test_forced_against_yovanovich_teertstra():
    """!@brief README 9.1: 1 to 4 % below eq 18 with C = 0.664 and 11 to 14 % below it with C = 0.742."""
    for r in fa.forced_vs_yt():
        assert -0.045 < r["d_664"] < -0.005, r["case"]
        assert -0.145 < r["d_742"] < -0.105, r["case"]


def test_yovanovich_teertstra_exponent_signs():
    """!@brief Review: eqs 24 and 25 (p 208) give n = 1.42 for a square, 0.97 for flow along the long side at L/W = 10 and 1.70 along the short side (the paper's range 0.97 to 1.68 of the fitted values); the first version had the logarithm of eq 24 reversed (1.14)."""
    assert abs(fa.yt_exponent(1.0, 1.0) - 1.42) < 1e-12
    assert abs(fa.yt_exponent(10.0, 1.0) - 0.97) < 1e-12
    assert abs(fa.yt_exponent(1.0, 10.0) - 1.70) < 1e-12


def test_ti_via_261():
    """!@brief README 9.4: 261.16 C/W against the 261 of TI AN-2020 (+0.06 %); plating outside the drill 232.8."""
    t = vf.ti_via()
    assert abs(t["r_prog"] - 261.16) < 0.01 and abs(100 * t["d_prog"] - 0.06) < 0.005 and abs(t["r_outside"] - 232.8) < 0.05


def test_krogh_and_lattice_radius():
    """!@brief README 9.4: the Krogh cell equals a numerical integration and the point-sink radius is the lattice value, both to 1e-12; Peaceman's 0.2079 differs."""
    assert all(r["rel"] < 1e-12 for r in vf.krogh_check())
    lr = vf.lattice_radius()
    assert lr["rel"] < 1e-12 and abs(lr["r_prog"] - 0.1985) < 5e-5 and abs(lr["r_peaceman"] - 0.2079) < 5e-5


def test_yovanovich_muzychka_culham_table_2():
    """!@brief README 9.2: eq 24 and eq 27 reproduce all nine columns of Table 2 (p 5) to the four printed digits."""
    for (e, a, b), pa, pb in zip(st.table2(), st.FULL_EQ24, st.FULL_EQ27):
        assert abs(a - pa) < 5.1e-5 and abs(b - pb) < 5.1e-5, e


def test_sor_omega_is_below_saad_optimum():
    """!@brief README 9.5: the Rayleigh-quotient omega is below the optimum of Saad's eq 4.47, which is the minimum of the SOR radius (scan 1.50 on 8 x 8)."""
    s = st.sor_check()
    assert s["rho_prog"] < s["rho_exact"] and s["omega_prog"] < s["omega_saad"]
    assert abs(s["omega_saad"] - s["omega_scan"]) < 0.02 and s["rad_saad"] < s["rad_prog"] < 1.0
    # Review: the price of the safe side on this worst case of the trial vector, quoted in README 9.5 (2.4 times the sweeps of the optimum)
    assert 2.3 < s["sweep_ratio"] < 2.5
