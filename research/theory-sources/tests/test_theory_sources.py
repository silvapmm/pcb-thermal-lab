#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_theory_sources.py
@brief Tests of the libraries of research/theory-sources: each reproduces a number printed in a source that was read (named in the test), or a closed form.
@details Run: .venv/bin/python -m pytest -q research/theory-sources/tests (from the repository root).
"""

import math
import sys
from pathlib import Path

import numpy as np

LIB = Path(__file__).resolve().parents[1] / "lib"
sys.path.insert(0, str(LIB))
import cond2d  # noqa: E402
import correlations as cr  # noqa: E402
import cosine_stack as cs  # noqa: E402
import gci  # noqa: E402
import mg2d  # noqa: E402
import rc_ladder as rl  # noqa: E402
import strip2d  # noqa: E402


def test_gci_reproduces_table_1_of_celik_2008():
    """!@brief The three columns of Table 1 of Celik et al. (2008): p, extrapolated value and GCI."""
    for args, p, ext, g in (((6.063, 5.972, 5.863, 1.5, 1.333), 1.53, 6.1685, 0.022), ((10.7880, 10.7250, 10.6050, 2.0, 2.143), 0.75, 10.8801, 0.011),
                            ((6.0042, 5.9624, 6.0909, 2.0, 2.143), 1.51, 6.0269, 0.005)):
        out = gci.gci(*args)
        assert abs(out["p"] - p) < 0.02 and abs(out["phi_ext21"] - ext) < 2e-3 and abs(out["gci_fine21"] - g) < 1.5e-3


def test_lienhard_example_8_1():
    """!@brief Lienhard Example 8.1: Nu 47.33 (laminar Churchill-Chu, Pr 0.71, Ra 6.78e7)."""
    assert abs(cr.churchill_chu_laminar(6.78e7, 0.71) - 47.33) < 0.05


def test_hollands_code_form_matches_iso15099_at_air():
    """!@brief The `ht` code form (cube root) agrees with the ISO 15099 form of the ASHRAE preprint within 0.3 % for Ra 2e3 to 1e7; the documented form (fifth root inside the logarithm) is 2 to 4 % low at 1e7."""
    for ra in (2e3, 3e3, 1e4, 1e5, 3e5, 1e6, 1e7):
        assert abs(cr.hollands_ht(0.71, ra) / cr.hollands_iso15099(ra) - 1) < 3e-3
    assert 0.02 < 1 - cr.hollands_ht(0.71, 1e7, root=5.0) / cr.hollands_iso15099(1e7) < 0.04


def test_hollands_documented_form_is_the_ht_docstring():
    """!@brief Regression (review): the documented variant changes the root only inside the logarithm, `2 (Ra^(1/3)/k2)^(1 - ln(Ra^(1/5)/k2))`, as the `ht` 1.2.0 docstring prints it."""
    pr, ra = 0.71, 1e7
    k1 = 1.44 / (1.0 + 0.018 / pr + 0.00136 / pr ** 2)
    k2 = 75.0 * math.exp(1.5 / math.sqrt(pr))
    doc = 1.0 + (1.0 - 1708.0 / ra) * (k1 + 2.0 * (ra ** (1 / 3) / k2) ** (1.0 - math.log(ra ** 0.2 / k2))) + ((ra / 5803.0) ** (1 / 3) - 1.0)
    assert abs(cr.hollands_ht(pr, ra, root=5.0) / doc - 1) < 1e-12
    assert abs(doc - 13.510) < 1e-3


def test_fujii_imura_is_evaluated_on_the_plate_width():
    """!@brief Regression (review): the down-face comparison of the convection study evaluates Lienhard 8.38 on a plate width (2 A/P and the shorter side), not on A/P."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    import study_natural_convection_sources as snc
    from pcbthermal import convection as cv
    row = [r for r in snc.part3() if (r[0], r[1], r[2]) == (300.0, 200.0, 60.0)][0]
    props = cv.air_properties(50.0)
    for width, value in ((2 * 0.06 / 1.0, row[8]), (0.2, row[9])):
        assert abs(cr.fujii_imura_down(cv.rayleigh(60.0, width, props)) * props["k"] / width / value - 1) < 1e-12
    assert row[9] < row[8] < row[7]                              # on its own length the 2D correlation is below the program here


def test_lemczyk_case_c_with_a_residual_bottom_film():
    """!@brief Review: with a bottom film Bi1 = 0.001 the 1D limit of case c is 1/(Bi2 + 1/(t/L1 + 1/Bi1)), which is the paper's 90.91 at Bi2 0.01 (0 gives 100)."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    import study_lemczyk_1992 as slm
    exact = 1.0 / (0.01 + 1.0 / (0.01 + 1.0 / 1e-3))
    assert abs(slm.psi(0.01, 0.01, 1.0, "c", n=40, bi_off=1e-3) / exact - 1) < 1e-6
    assert abs(exact - 90.91) < 0.02


def test_hashin_shtrikman_and_bruggeman_2d():
    """!@brief Milton eq. 7.10 for d = 2 gives 13/7 and 28/13; the Bruggeman root solves its equation and is sqrt(ab) at one half."""
    lo, up = cond2d.hs_bounds(0.5, 4.0, 1.0, 2)
    assert abs(lo - 13 / 7) < 1e-12 and abs(up - 28 / 13) < 1e-12
    assert abs(cond2d.bruggeman(0.5, 10.0, 1.0, 2) - math.sqrt(10.0)) < 1e-12


def test_periodic_solver_uniform_and_laminate():
    """!@brief A uniform cell returns its conductivity; a two-layer laminate along x returns the arithmetic mean (layers parallel to the field)."""
    assert abs(cond2d.effective_conductivity(np.full((8, 8), 3.0)) - 3.0) < 1e-9
    cell = np.where(np.arange(16)[:, None] < 8, 10.0, 1.0) * np.ones((16, 16))
    assert abs(cond2d.effective_conductivity(cell) - 5.5) < 1e-6


def test_checkerboard_approaches_sqrt():
    """!@brief Milton eq. 3.11: the checkerboard tends to sqrt(s1 s2) (within 5 % at 64 cells per square)."""
    k = cond2d.effective_conductivity(cond2d.checkerboard(64, 10.0, 1.0))
    assert abs(k / math.sqrt(10.0) - 1) < 0.05


def test_lemczyk_table_1_rows():
    """!@brief Q_a of Table 1 of Lemczyk et al. (1992): 0.179 W and 0.436 W within 0.5 %."""
    for (w, t, l1, k), qa in (((50, 100, 100, 0.2), 0.179), ((50, 50, 250, 0.2), 0.436)):
        q = strip2d.trace_heat_flow(w * 1e-6, t * 1e-6, l1 * 1e-6, k, 10.0, 10.0, nx=200, nz=200)
        assert abs(q / qa - 1) < 5e-3


def test_strip_one_dimensional_limit():
    """!@brief A trace as wide as the cell with the film h on both faces: Q = h L1 Tc plus the series path of the solid and the bottom film."""
    q = strip2d.trace_heat_flow(1.0, 0.01, 1.0, 1.0, 5.0, 5.0, tc=1.0, nx=40, nz=40)
    assert abs(q - (5.0 + 1.0 / (1.0 / 5.0 + 0.01))) < 1e-6


def test_cosine_series_converges_and_one_dimensional():
    """!@brief The series result converges with the number of modes (0.1 % between 100 and 200) and for a source as large as the block the heat splits between the two films (R = half the series resistance)."""
    layers = [(0.5263e-3, 0.4), (0.0356e-3, 400.0), (0.5263e-3, 0.4), (0.0356e-3, 400.0), (0.5263e-3, 0.4)]
    r100 = cs.solve(0.05, 0.05, 0.025, layers, 5.0, 5.0, 2.5, 100)[2]
    r200 = cs.solve(0.05, 0.05, 0.025, layers, 5.0, 5.0, 2.5, 200)[2]
    assert abs(r200 / r100 - 1) < 1e-3
    full = cs.solve(0.05, 0.05, 0.0499999, [(1e-3, 1.0)], 100.0, 100.0, 1.0, 3)[2]
    # Exact one-dimensional result: the fraction of the heat going down is (1/h) / (2/h + t/k), and it makes a drop t/k over the area A
    frac = (1.0 / 100.0) / (2.0 / 100.0 + 1e-3)
    assert abs(full - frac * 1e-3 / 0.0025) / full < 1e-4


def test_cauer_foster_equivalence_and_published_numbers():
    """!@brief Nexperia AN11261: the ladder sums to 0.4 K/W, Zth(4 ms) is 0.26 K/W (Fig. 12) and the Foster form equals the ladder."""
    r = np.array([0.00272144, 0.0220255, 0.00713124, 0.185679, 0.182443])
    c = np.array([9.29451e-05, 0.000514739, 0.00195047, 0.00305028, 0.0279554])
    assert abs(r.sum() - 0.4) < 1e-4
    t = np.array([1e-4, 1e-3, 4e-3, 1e-1])
    rf, tau = rl.foster(r, c)
    assert np.abs(rl.zth_cauer(t, r, c) - rl.zth_foster(t, rf, tau)).max() < 1e-10
    assert abs(rl.zth_cauer([4e-3], r, c)[0] - 0.26) < 0.01
    assert abs(rf.sum() - r.sum()) < 1e-12 and (rf > 0).all() and (tau > 0).all()


def test_multigrid_factor_is_independent_of_h():
    """!@brief The V(2,1) cycle reduces the residual by about the same factor (below 0.15) from 15 to 127 points per side."""
    factors = [np.mean(mg2d.convergence_factors(n, 6)[-3:]) for n in (15, 31, 63, 127)]
    assert max(factors) < 0.15 and max(factors) - min(factors) < 0.05
