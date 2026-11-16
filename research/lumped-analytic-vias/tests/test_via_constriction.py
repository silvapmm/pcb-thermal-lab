#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_via_constriction.py
@brief Tests of the constriction library and of the in-memory patches of the Lumped and Analytic models.
@details Closed forms against numerical integration and limits; the Kron reduction against a series circuit; the adopted claims (unit cell, row, copper-fill gain of the
         example board) on the program as it ships; the Analytic tile patch. The tests that certified the source-text patches and the values frozen from f2d5c03 were removed
         in the 2.8.0 reproduction pass (README, section on 2.8.0). Run: .venv/bin/python -m pytest research/lumped-analytic-vias/tests
"""

import contextlib
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



def test_unit_cell_error_is_small(libs):
    """!
    @brief The claim adopted by fix/via-constriction (2.4.5), on the program as it ships: on the periodic unit cell (4 mm, 0.3 mm copper fill, 2 layers) the Lumped and the
           Analytic via effect within 2 % of the fine-grid reference (1/16 mm). Measured on development 232ba648: reference 235.670 K, Lumped +0.89 %, Analytic -0.64 %
           (the program before the constriction overstated it by 10 % or more and the patches of this folder read within 6 %: README, the record).
    @param libs Fixture.
    @return None.
    """
    prob = cases.unit_cell(4, 0.3, 385.0)
    e_ref, _, _ = hz.reference_uniform(prob, 1.0 / 16)
    q0 = hz.no_vias(prob)
    for model in ("lumped", "analytic"):
        assert abs(hz.effect(prob, model, contextlib.nullcontext, 0.5, q0) / e_ref - 1.0) < 0.02


def test_row_beside_a_source(libs):
    """!
    @brief The row of five vias beside a source, on the program as it ships (the cluster treatment adopted): the Lumped via effect within 8 % and the Analytic within 2 % of
           the fine-grid reference (1/8 mm). Measured on development 232ba648: reference 3.0091 K, Lumped +5.96 %, Analytic -0.81 % (the record of the patches: the cluster
           treatment at less than half the error of the ring cell alone, README).
    @param libs Fixture.
    @return None.
    """
    prob = cases.row(5, 1.0, 0.3, 385.0, 16.0, 2, 3.0, 1.0)
    e_ref, _, _ = hz.reference_uniform(prob, 1.0 / 8)
    q0 = hz.no_vias(prob)
    assert abs(hz.effect(prob, "lumped", contextlib.nullcontext, 0.5, q0) / e_ref - 1.0) < 0.08
    assert abs(hz.effect(prob, "analytic", contextlib.nullcontext, 0.5, q0) / e_ref - 1.0) < 0.02


def test_copper_fill_gain_of_the_example_board(libs):
    """!
    @brief The roadmap symptom A6, on the program as it ships: the copper-fill gain of the example board (fill 0 against 385 W/mK in the nine vias, 0.5 mm) in the Lumped
           and the Analytic within 0.5 K of the FVM's. Measured on development 232ba648: FVM 4.245 K, Lumped 4.666 K, Analytic 4.324 K (6.3 to 6.8 K before the constriction;
           README, the record).
    @param libs Fixture.
    @return None.
    """
    from pcbthermal.examples import example_board

    def gain(model):
        """!
        @brief Copper-fill gain of the example board in one model.
        @param model Model key.
        @return float Gain in K (rise with empty vias minus rise with filled vias).
        """
        out = []
        for fill in (0.0, 385.0):
            prob = example_board()
            for v in prob.vias:
                v.fill_k = fill
            out.append(pc.max_rise(prob, model, 0.5))
        return out[0] - out[1]
    g_fvm = gain("fvm")
    assert g_fvm == pytest.approx(4.245, abs=0.01)
    assert abs(gain("lumped") - g_fvm) < 0.5 and abs(gain("analytic") - g_fvm) < 0.5


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


def test_nearest_neighbour_cache_follows_the_problem(libs):
    """!
    @brief The nearest-neighbour cache of the Analytic patch follows the content of the problem, not its id (review regression).
    @details The first version keyed the cache by id(problem): a via moved on the same object kept its old distances, and a new problem that
             reused the id of a freed one raised a KeyError (tests/test_stackup.py with the patches installed).
    @return None.
    """
    p = cases.array(4, 3, 3.5, 0.3, 0.0)
    d0 = ap._nn_distances(p)[ap.vkey(p.vias[0])]
    assert d0 == pytest.approx(3.5e-3)
    for v in p.vias:                                                         # the same object, the array squeezed to 1 mm
        v.x = 10.5e-3 + (v.x - 10.5e-3) / 3.5
        v.y = 10.5e-3 + (v.y - 10.5e-3) / 3.5
    assert ap._nn_distances(p)[ap.vkey(p.vias[0])] == pytest.approx(1.0e-3)
    q = cases.array(4, 3, 2.0, 0.3, 0.0)                                     # another problem: no KeyError, its own distances
    assert ap._nn_distances(q)[ap.vkey(q.vias[4])] == pytest.approx(2.0e-3)
