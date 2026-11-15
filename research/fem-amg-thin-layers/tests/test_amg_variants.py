#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_amg_variants.py
@brief Tests of the measurement tools of research/fem-amg-thin-layers on tiny systems (a thin-layer structured model of a few thousand unknowns): every variant that pyamg accepts converges to the direct solution, CG counts
       its iterations, and the hierarchy of one matrix preconditions another right-hand side. Written, NOT RUN when written; run only this folder: `.venv/bin/python -m pytest -q research/fem-amg-thin-layers/tests`.
"""

import os
import sys

import numpy as np
import pytest
import scipy.sparse.linalg as spla

pytest.importorskip("pyamg")
LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")
sys.path.insert(0, LIB)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))

import variants                                                    # noqa: E402
from pcbthermal import femcore                                      # noqa: E402


def thin_system():
    """!
    @brief A 24 x 24 x 6 cell tensor mesh with two thin high-conductivity slabs (35 um) between 1 mm gaps and a film on the bottom: strongly anisotropic in the element sense, SPD after the film.
    @return (A, rhs, n).
    """
    xn = np.linspace(0, 24e-3, 25)
    yn = np.linspace(0, 24e-3, 25)
    zn = np.cumsum([0, 35e-6, 0.25e-3, 0.25e-3, 35e-6, 0.25e-3, 0.25e-3])
    k = np.full((6, 24, 24), 0.3)
    k[0], k[3] = 385.0, 385.0                                       # the copper slabs
    q = np.zeros((6, 24, 24))
    q[0, 10:14, 10:14] = 4.0 / (16 * 1e-6 * 35e-6)
    m = femcore.structured_model(xn, yn, zn, k=k, q=q, films={"bottom": 10.0, "top": 10.0})
    a = m.assemble()
    return a["A"].tocsr(), np.asarray(a["rhs"], float), a["rhs"].size


@pytest.mark.parametrize("name", sorted(variants.VARIANTS))
def test_every_accepted_variant_reaches_the_direct_solution(name):
    A, rhs, _ = thin_system()
    M, info = variants.make_preconditioner(A, name)
    if M is None:
        pytest.skip(f"pyamg refuses {name}: {info['refused']}")        # recorded as a finding by the study, not a failure of the tool
    x, cg = variants.timed_cg(A, rhs, M)
    ref = spla.spsolve(A.tocsc(), rhs)
    assert cg["converged"] and cg["iterations"] > 0
    assert np.max(np.abs(x - ref)) < 1e-8 * max(1.0, np.max(np.abs(ref)))


def test_a_hierarchy_preconditions_another_right_hand_side():
    A, rhs, n = thin_system()
    M, _ = variants.make_preconditioner(A, "base")
    rng = np.random.default_rng(1)
    b2 = np.abs(rng.standard_normal(n))
    x, cg = variants.timed_cg(A, b2, M)
    assert cg["converged"]
    assert np.linalg.norm(A @ x - b2) / np.linalg.norm(b2) < 1e-8


def test_the_iteration_count_is_counted_once_per_cg_step():
    A, rhs, _ = thin_system()
    M, _ = variants.make_preconditioner(A, "base")
    _, cg = variants.timed_cg(A, rhs, M, tol=1e-4)
    _, tight = variants.timed_cg(A, rhs, M, tol=1e-10)
    assert 0 < cg["iterations"] < tight["iterations"]
