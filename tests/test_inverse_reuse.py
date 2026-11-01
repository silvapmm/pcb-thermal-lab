#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_inverse_reuse.py
@brief The Power Calculator solves one board matrix with several powers: one LU factorisation, bit-identical results, no reuse across a changed matrix.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import contextlib

import scipy.sparse.linalg as spla

from pcbthermal import Problem, SolverOptions, fvm, inverse, simulate


def board(power=2.0):
    """!
    @brief A small four-layer board with one part at a junction resistance and vias under it.
    @param power Power of the part in W.
    @return Problem.
    """
    p = Problem.new(40, 40, 4)
    for layer in (1, 2, 4):
        p.add_zone(layer, rect=(3, 3, 37, 37))
    p.add_heater(1, power, rect=(17, 17, 23, 23), name="Q1", theta=4.0)
    for x in (18.0, 20.0, 22.0):
        p.add_via(x, 20.0, 0.3)
    return p


def count_solves(monkeypatch):
    """!
    @brief Count the LU factorisations (splu) and the plain solves (spsolve) made through scipy by the direct solver of fvm.
    @param monkeypatch pytest monkeypatch fixture.
    @return dict with the counters "splu" and "spsolve", updated as the calls happen.
    """
    n = {"splu": 0, "spsolve": 0}
    real_splu, real_spsolve = spla.splu, spla.spsolve

    def splu(*a, **k):
        n["splu"] += 1
        return real_splu(*a, **k)

    def spsolve(*a, **k):
        n["spsolve"] += 1
        return real_spsolve(*a, **k)

    monkeypatch.setattr(fvm.spla, "splu", splu)
    monkeypatch.setattr(fvm.spla, "spsolve", spsolve)
    return n


def measured(problem):
    """!
    @brief The board-ring temperature the model gives for the part as drawn.
    @param problem Problem.
    @return Temperature in degC.
    """
    return simulate(problem, SolverOptions(models=("fvm",), cell_mm=1.0)).heater_rows()[0]["t_ring"]


def test_manual_h_uses_one_factorisation_for_all_the_runs(monkeypatch):
    prob = board()
    t = measured(prob)
    n = count_solves(monkeypatch)
    out = inverse.power_from_temperature(prob, 0, t, point="ring", cell_mm=1.0)
    # t(0), t(p0), t(p1) and the final state: four solves of the same matrix, one factorisation, no plain spsolve
    assert out["runs"] >= 4
    assert n["splu"] == 1 and n["spsolve"] == 0


def test_results_are_bit_identical_to_the_runs_without_reuse(monkeypatch):
    prob = board()
    t = measured(prob)
    kept = inverse.power_from_temperature(prob, 0, t, point="top", cell_mm=1.0, psi_jt=2.0)
    band_kept = inverse.power_band(prob, 0, t, point="ring", cell_mm=1.0, uncertainty={"design_level": "hand"})
    monkeypatch.setattr(inverse.fvm, "factor_reuse", contextlib.nullcontext)       # every run factorises (spsolve) as before
    plain = inverse.power_from_temperature(prob, 0, t, point="top", cell_mm=1.0, psi_jt=2.0)
    band_plain = inverse.power_band(prob, 0, t, point="ring", cell_mm=1.0, uncertainty={"design_level": "hand"})
    assert kept == plain
    assert band_kept == band_plain


def test_a_changed_matrix_is_factorised_again(monkeypatch):
    prob = board()
    t = measured(prob)
    n = count_solves(monkeypatch)
    inverse.power_band(prob, 0, t, point="ring", cell_mm=1.0, uncertainty={"design_level": "hand"})
    # Every one-at-a-time end that changes the matrix (copper, h, coverage, weight, planes, vias) has its own factorisation:
    # far more than one, and never a plain spsolve
    assert n["splu"] > 4 and n["spsolve"] == 0
