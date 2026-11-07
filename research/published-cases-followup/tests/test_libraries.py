#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_libraries.py
@brief The independent references of this investigation against closed forms, an energy balance and the published tables: the series of Yovanovich, Muzychka and Culham (1999), the 2D strip solver, the thin-plate cosine series and the trace cells of Lemczyk and others (1992).
"""

import numpy as np
import pytest

import lemczyk as LZ
import layered3d as L3
import plate_series as PS
import series as S
import strip2d as F


def test_table2_of_the_paper_is_reproduced_to_the_printed_digits():
    eps = (0.02, 0.04, 0.06, 0.08, 0.10, 0.20, 0.40, 0.60, 0.80)
    iso = (1.1377, 0.9172, 0.7883, 0.6970, 0.6263, 0.4083, 0.1984, 0.0882, 0.0255)
    par = (1.1545, 0.9340, 0.8051, 0.7138, 0.6430, 0.4247, 0.2134, 0.1007, 0.0338)
    tc = (1.1015, 0.8811, 0.7523, 0.6611, 0.5905, 0.3738, 0.1691, 0.0675, 0.0160)
    for e, a, b, c in zip(eps, iso, par, tc):
        assert S.psi_isoflux(e) == pytest.approx(a, abs=1.0e-4)
        assert S.psi_parabolic(e) == pytest.approx(b, abs=1.0e-4)
        assert S.psi_true_isothermal(e) == pytest.approx(c, abs=1.0e-4)


def test_equation_26_row_is_a_truncated_sum_at_small_strips():
    # the printed 1.1011 at eps 0.02 is what a sum cut at a few hundred terms gives; the converged sum is 1.10154
    assert S.psi_equivalent_isothermal(0.02) == pytest.approx(1.10154, abs=2e-5)
    assert abs(S.psi_equivalent_isothermal(0.02, 300) - 1.1011) < 5e-4


def test_table3_row_is_the_mean_of_equations_24_and_27_not_26():
    for e, printed in ((0.4, 0.1838), (0.6, 0.0779), (0.8, 0.0208)):
        m27 = 0.5 * (S.psi_isoflux(e) + S.psi_true_isothermal(e))
        m26 = 0.5 * (S.psi_isoflux(e) + S.psi_equivalent_isothermal(e))
        assert abs(m27 - printed) <= 1.1e-4
        assert abs(m26 - printed) > 1e-3
    assert S.psi_step(0.2) == pytest.approx(0.3936, abs=1e-4)


def test_strip_solver_against_equations_24_and_23():
    k, c = 1.0, 1.0
    a, t = 0.2, 3.0
    xe = F.graded_edges(c, 0.004 * a, a, 1.12)
    ze = F.graded_edges(t, 0.004 * a, 0.0, 1.12)
    r = F.solve(xe, ze, k, a, "flux", 1.0, 0.0, None)
    psi = k * (r["t_face_mean"] / r["q_strip"] - t / (k * c)) / 2.0
    assert psi == pytest.approx(S.psi_isoflux(0.2), rel=5e-3)
    ze2 = F.graded_edges(0.5, 0.004 * a, 0.0, 1.12)
    r2 = F.solve(xe, ze2, k, a, "flux", 1.0, 0.0, 2.0)
    psi2 = k * (r2["t_face_mean"] / r2["q_strip"] - 0.5 / (k * c) - 1.0 / (2.0 * c)) / 2.0
    assert psi2 == pytest.approx(S.psi_finite(0.2, 0.5, 2.0), rel=5e-3)


def test_strip_solver_energy_balance_with_films():
    xe = F.graded_edges(1.0, 0.01, 0.3, 1.2)
    ze = F.graded_edges(0.5, 0.01, 0.0, 1.2)
    r = F.solve(xe, ze, 1.0, 0.3, "temp", 1.0, 3.0, 2.0, film_under_strip=True)
    dx, dz = r["dx"], r["dz"]
    out = float((2.0 * r["T"][-1] * dx / (1 + 2.0 * dz[-1] / (2 * 1.0))).sum())          # bottom film: h * face temperature (face from the half cell)
    top = float((3.0 * (r["T"][0] / (1 + 3.0 * dz[0] / 2.0)) * dx)[r["x"] > 0.3].sum()) + r["film_strip"]
    assert out + top == pytest.approx(r["q_total"], rel=2e-2)


def test_one_dimensional_limits_of_the_trace_cells():
    # a trace over the whole width (w = L1): the cells are one-dimensional
    bi, tau = 1.0, 1.0
    assert LZ.psi_case("a", bi, tau, 1.0) == pytest.approx(1.0 / (1.0 / bi + 1.0 / (tau + 1.0 / bi)), rel=2e-3)   # film on the face in parallel with the conduction to the cooled base
    assert LZ.psi_case("b", bi, tau, 1.0) == pytest.approx((tau / 2 + 1.0 / bi) / 2.0, rel=2e-3)
    assert LZ.psi_case("d", bi, tau, 1.0) == pytest.approx(tau + 1.0 / bi, rel=2e-3)
    assert LZ.psi_case("c", bi, tau, 1.0) == pytest.approx(1.0 / bi, rel=2e-3)


def test_case_c_of_table_1_needs_bi1_of_0_001():
    k, w, t, l1 = 0.2, 10e-6, 10e-6, 50e-6
    q0 = LZ.q_case("c", k, t, l1, w, 10.0, 90.0)
    q1 = LZ.q_case("c", k, t, l1, w, 10.0, 90.0, bi1=0.001)
    assert q0 == pytest.approx(0.0449, abs=2e-4)
    assert q1 == pytest.approx(0.063, abs=1e-3)           # printed 0.063


def test_trace_cell_rows_of_table_1():
    rows = [r for r in LZ.TABLE1 if r[1:4] in ((10, 10, 20), (50, 50, 100), (250, 1000, 500))]
    for k, w, t, l1, qa, qb, qc, qd in rows:
        args = (k, t * 1e-6, l1 * 1e-6, w * 1e-6, 10.0, 90.0)
        assert LZ.q_case("a", *args) == pytest.approx(qa, rel=1.5e-2)
        assert LZ.q_case("d", *args) == pytest.approx(qd, rel=3e-2)


def test_plate_series_against_the_finite_volume_solver_and_an_energy_balance():
    side, k, t, h = 0.1, 200.0, 1.3e-3, 100.0
    # the mean temperature of the plate is P / (h L^2)
    o = PS.source_rise(side, k * t, h, (0.0, 0.0, 0.025, 0.025), 1.0, 300)
    assert o["t_film"] == pytest.approx(1.0 / (h * side ** 2), rel=1e-12)
    # thin plate equals a one-slab 3D solve (isotropic, the gradient across 1.3 mm of aluminium is negligible) within 0.5 %
    dx, n = 1e-3, 100
    res = L3.solve(dx, n, n, [(t, k, 3)], (0.0, 0.0, 0.025, 0.025), 1.0, 0.0, h)
    rc3 = res["max_source"] - res["mean_wall"]
    assert o["rc"] == pytest.approx(rc3, rel=6e-3)
    assert 0.6 < PS.source_rise(side, k * t, h, (0.0375, 0.0375, 0.0625, 0.0625), 1.0, 300)["rc"] < 0.7


def test_plate_series_symmetry_and_convergence():
    # a source and its mirror image about the centre of the plate have the same rise; the sum is converged at 300 terms
    side, g, h = 0.05, 0.3, 60.0
    a = PS.source_rise(side, g, h, (0.0, 0.0, 0.01, 0.02), 1.0, 300)["rc"]
    b = PS.source_rise(side, g, h, (0.04, 0.03, 0.05, 0.05), 1.0, 300)["rc"]
    c = PS.source_rise(side, g, h, (0.0, 0.0, 0.01, 0.02), 1.0, 700)["rc"]
    assert a == pytest.approx(b, rel=1e-9)
    assert a == pytest.approx(c, rel=2e-3)
