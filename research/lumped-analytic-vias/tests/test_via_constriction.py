#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_via_constriction.py
@brief Tests of the constriction library and of the in-memory patches of the Lumped and Analytic models.
@details Closed forms against numerical integration and limits; the Kron reduction against a series circuit; the patches with mode "off" against the program bit by bit; the
         patched models restore the program on exit; the unit-cell error of the patched models is small. Run: .venv/bin/python -m pytest research/lumped-analytic-vias/tests
"""

import copy
import math
import os
import sys

import numpy as np
import pytest
from scipy.integrate import quad

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import analytic_patch as ap                                                  # noqa: E402
import cases                                                                 # noqa: E402
import constriction as cr                                                    # noqa: E402
import harness as hz                                                         # noqa: E402
import lumped_patch as lp                                                    # noqa: E402
import program_cases as pc                                                   # noqa: E402


def test_krogh_matches_integration():
    """!
    @brief The Krogh mean-to-wall resistance equals the numerical area mean of the exact profile.
    @return None.
    """
    S, a, R = 0.0135, 0.1e-3, 1.7e-3

    def T(r):
        # temperature above the wall per watt: (1 / (2 pi S (R^2 - a^2))) (R^2 ln(r/a) - (r^2 - a^2)/2)
        return (R * R * math.log(r / a) - (r * r - a * a) / 2) / (2 * math.pi * S * (R * R - a * a))
    mean = quad(lambda r: T(r) * 2 * r, a, R)[0] / (R * R - a * a)
    assert cr.krogh(S, R, a) == pytest.approx(mean, rel=1e-8)


def test_krogh_asymptote():
    """!
    @brief For R >> a the resistance tends to (ln(R/a) - 3/4) / (2 pi S).
    @return None.
    """
    S, a = 0.02, 1e-4
    R = 1e3 * a
    assert cr.krogh(S, R, a) == pytest.approx((math.log(R / a) - 0.75) / (2 * math.pi * S), rel=1e-5)


def test_cell_with_loss_limits():
    """!
    @brief Without loss the cell with loss tends to Krogh; a big cell tends to the infinite sheet (the heat taken by the via).
    @return None.
    """
    S, a, R = 0.0135, 0.1e-3, 2e-3
    tiny = cr.cell_with_loss(S, 1e-4, a, R, 1.0)
    assert tiny["R_c"] == pytest.approx(cr.krogh(S, R, a), rel=1e-3)
    h, q = 200.0, 1.0
    big = cr.cell_with_loss(S, h, a, 60 * math.sqrt(S / h), q)
    inf = cr.sheet_with_loss(S, h, a, q)
    # the cell collects q pi R^2 in total; the via takes I; per area the infinite-sheet result is I / (pi R^2) = q' ... compare the heat taken by the via
    assert big["I"] == pytest.approx(inf["I"], rel=2e-3)


def test_kron_series_circuit():
    """!
    @brief Two sheets joined by a barrel with a well in each: the reduced conductance is the series circuit.
    @return None.
    """
    G = cr.kron_barrel([0.02], [0.05, 0.08])
    assert G[0, 1] == pytest.approx(1.0 / (1 / 0.05 + 1 / 0.02 + 1 / 0.08), rel=1e-12)
    G3 = cr.kron_barrel([0.02, 0.03], [np.inf, np.inf, np.inf])
    assert G3[0, 1] == pytest.approx(0.02, rel=1e-6) and G3[1, 2] == pytest.approx(0.03, rel=1e-6)


def test_peak_excess_formula():
    """!
    @brief The rim of a uniformly heated disc with a central uniform-flux sink of relative radius rho is hotter than the disc mean by (1 - rho^2) / 4 (units I / (2 pi S)).
    @return None.
    """
    rho = 0.4

    def Tp(r):
        return r * (1 / rho ** 2 - 1) if r < rho else (1 - r * r) / r

    def T(r):
        return quad(Tp, 0, r, points=[rho] if r > rho else None)[0]
    mean = quad(lambda r: T(r) * 2 * r, 0, 1, points=[rho])[0]
    assert T(1.0) - mean == pytest.approx((1 - rho ** 2) / 4, rel=1e-6)


@pytest.fixture(scope="module")
def libs():
    """!
    @brief Load the program's libraries once.
    @return None.
    """
    pc.load_libraries()


def test_lumped_off_is_the_program(libs):
    """!
    @brief The patched Lumped with mode "off" gives the program's result to the last digit, on a lattice cell and on the via array.
    @param libs Fixture.
    @return None.
    """
    for prob in (cases.unit_cell(4, 0.3, 385.0), cases.array(4, 3, 3.5, 0.3, 385.0)):
        a = pc.max_rise(prob, "lumped", 0.5)
        with lp.patched("off"):
            b = pc.max_rise(prob, "lumped", 0.5)
        assert a == pytest.approx(b, rel=1e-12)


def test_analytic_off_is_the_program(libs):
    """!
    @brief The patched Analytic with mode "off" gives the program's result to the last digit.
    @param libs Fixture.
    @return None.
    """
    prob = cases.array(4, 3, 3.5, 0.3, 385.0)
    a = pc.max_rise(prob, "analytic", 0.5)
    with ap.patched("off"):
        b = pc.max_rise(prob, "analytic", 0.5)
    assert a == pytest.approx(b, rel=1e-12)


def test_patches_restore_the_program(libs):
    """!
    @brief After the context ends the original functions are back.
    @param libs Fixture.
    @return None.
    """
    from pcbthermal import analytic, lumped
    n1, s1 = lumped._heater_network, analytic.solve_steady
    with lp.patched("krogh"), ap.patched("on"):
        assert lumped._heater_network is not n1 and analytic.solve_steady is not s1
    assert lumped._heater_network is n1 and analytic.solve_steady is s1
    assert not hasattr(lumped, "_via_couplings") and not hasattr(analytic, "_self_terms")


def test_unit_cell_error_is_small(libs):
    """!
    @brief On the periodic unit cell (4 mm, 0.3 mm copper fill, 2 layers) the program overstates the via effect by 10 % or more and the patches by less than 6 %.
    @param libs Fixture.
    @return None.
    """
    prob = cases.unit_cell(4, 0.3, 385.0)
    e_ref, _, _ = hz.reference_uniform(prob, 1.0 / 16)
    err = hz.errors(prob, e_ref, 0.5, ["L_prog", "L_ring", "A_bil"])
    assert err["L_prog"] > 10.0
    assert abs(err["L_ring"]) < 6.0 and abs(err["A_bil"]) < 6.0


def test_cluster_group_improves_the_row(libs):
    """!
    @brief A row of five vias beside a source: the cluster treatment is much closer to the reference than the cell of the ring alone.
    @param libs Fixture.
    @return None.
    """
    prob = cases.row(5, 1.0, 0.3, 385.0, 16.0, 2, 3.0, 1.0)
    e_ref, _, _ = hz.reference_uniform(prob, 1.0 / 8)
    err = hz.errors(prob, e_ref, 0.5, ["L_ring", "L_grp"])
    assert abs(err["L_grp"]) < 0.5 * abs(err["L_ring"])


def test_copper_fill_gain_of_the_example_board(libs):
    """!
    @brief The roadmap symptom A6: the copper-fill gain of the example board is 6.3 to 6.8 K in the program (the corrected FVM puts it at 4.2 K); the patches bring both models within 0.5 K of 4.2 K.
    @param libs Fixture.
    @return None.
    """
    from pcbthermal.examples import example_board

    def gain(model, ctx):
        out = []
        for fill in (0.0, 385.0):
            prob = example_board()
            for v in prob.vias:
                v.fill_k = fill
            with ctx():
                out.append(pc.max_rise(prob, model, 0.5))
        return out[0] - out[1]
    null = hz.VARIANTS["L_prog"][1]
    assert gain("lumped", null) > 6.0 and gain("analytic", null) > 5.8
    assert abs(gain("lumped", hz.VARIANTS["L_grp0"][1]) - 4.2) < 0.5
    assert abs(gain("analytic", hz.VARIANTS["A_fin"][1]) - 4.2) < 0.5


def test_analytic_fine_tiles_resolve_a_dense_array(libs):
    """!
    @brief 5 x 5 vias at 1.2 mm under a 6 mm source: the patched Analytic model with 1 mm tiles is within 3 % of the fine-grid reference and closer than the program.
    @param libs Fixture.
    @return None.
    """
    prob = cases.pad(4, 5, 1.2, 0.3, 385.0, 20.0, 6.0)
    e_ref, _, _ = hz.reference_uniform(prob, 1.0 / 16)
    err = hz.errors(prob, e_ref, 0.5, ["A_prog", "A_fin"])
    assert abs(err["A_fin"]) < 3.0
    assert abs(err["A_prog"]) > abs(err["A_fin"])
