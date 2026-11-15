#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_fem_assembly_speed.py
@brief The faster element assembly of `pcbthermal/femcore.py` (closed-form 3 x 3 determinant and inverse, batched matrix products) gives the same matrix, load, volumes and
       solution as the general `numpy.linalg` / `einsum` routine it replaced, which is kept here only as the reference.
"""

import numpy as np
import pytest

from pcbthermal import femcore


def _reference_elements(model, chunk=20000):
    """!
    @brief The element assembly as it was before the speed-up (per-chunk `numpy.linalg.det/inv` and `einsum`), kept as the reference.
    @param model femcore.Model.
    @param chunk Elements per chunk.
    @return Tuple (rows, cols, vals, rhs) as `Model._assemble_elements`.
    """
    E, N = model.elems.shape[0], model.nodes.shape[0]
    rows, cols, vals = [], [], []
    rhs = np.zeros(N)
    gps = [(gx, gy, gz) for gx in (-femcore.G1, femcore.G1) for gy in (-femcore.G1, femcore.G1) for gz in (-femcore.G1, femcore.G1)]
    for a in range(0, E, chunk):
        el = model.elems[a:a + chunk]
        X = model.nodes[el]
        k = model.k[a:a + chunk]
        ke = np.zeros((el.shape[0], 8, 8))
        fe = np.zeros((el.shape[0], 8))
        for gx, gy, gz in gps:
            n, dn = femcore.shape(gx, gy, gz)
            J = np.einsum("eai,aj->eij", X, dn)
            det = np.abs(np.linalg.det(J))
            Jinv = np.linalg.inv(J)
            B = np.einsum("aj,eji->eai", dn, Jinv)
            ke += np.einsum("eai,ei,ebi->eab", B, k, B) * det[:, None, None]
            fe += (model.q[a:a + chunk] * det)[:, None] * n[None, :]
        rows.append(np.repeat(el, 8, axis=1).ravel())
        cols.append(np.tile(el, (1, 8)).ravel())
        vals.append(ke.ravel())
        np.add.at(rhs, el.ravel(), fe.ravel())
    return rows, cols, vals, rhs


def _distorted_model(seed=3):
    """!
    @brief A small mesh with randomly moved nodes (general mapped bricks), orthotropic conductivities and sources, and films on all outer sides.
    @param seed Seed of the random generator.
    @return femcore.Model.
    """
    rng = np.random.default_rng(seed)
    xn, yn, zn = np.linspace(0, 6e-3, 7), np.linspace(0, 5e-3, 6), np.array([0, 0.2e-3, 0.5e-3, 1.5e-3, 1.7e-3])
    m = femcore.structured_model(xn, yn, zn, k=rng.uniform(0.3, 300.0, (4, 5, 6, 3)), q=rng.uniform(0, 1e6, (4, 5, 6)),
                                 films={"top": 10.0, "bottom": 15.0}, t_amb=25.0)
    m.nodes = m.nodes + rng.uniform(-0.2e-4, 0.2e-4, m.nodes.shape)         # small enough to keep every mapping valid
    return m


def test_closed_form_det_and_inverse_match_numpy_on_random_matrices():
    """!
    @brief The cofactor determinant and inverse equal numpy.linalg to 1e-12 relative on random and on a nearly singular batch, and a singular matrix gives det 0, not an error.
    @return None.
    """
    rng = np.random.default_rng(1)
    J = rng.normal(size=(5000, 3, 3))
    det, inv = femcore.det_inv3(J)
    assert np.allclose(det, np.linalg.det(J), rtol=1e-12, atol=0)
    assert np.allclose(inv, np.linalg.inv(J), rtol=1e-10, atol=1e-10)
    det0, _ = femcore.det_inv3(np.zeros((1, 3, 3)))
    assert det0[0] == 0.0


def test_new_assembly_equals_the_reference_on_one_hexahedron():
    """!
    @brief One skewed brick: the element matrix and load of the new assembly equal the reference to 1e-12 relative.
    @return None.
    """
    nodes = np.array([[0, 0, 0], [1, 0.1, 0], [1.2, 1, 0.05], [0.1, 0.9, 0], [0, 0.1, 1], [1.1, 0, 1.1], [1, 1, 0.9], [0, 1, 1.2]], float) * 1e-3
    m = femcore.Model(nodes, np.arange(8)[None, :])
    m.k[:] = [3.0, 7.0, 0.4]
    m.q[:] = 5e5
    r1, c1, v1, f1 = m._assemble_elements()
    r0, c0, v0, f0 = _reference_elements(m)
    assert np.array_equal(r1[0], r0[0]) and np.array_equal(c1[0], c0[0])
    assert np.allclose(v1[0], v0[0], rtol=1e-12, atol=1e-12 * np.abs(v0[0]).max())
    assert np.allclose(f1, f0, rtol=1e-12, atol=1e-12 * np.abs(f0).max())


def test_new_assembly_equals_the_reference_on_a_distorted_board_and_the_solution_agrees():
    """!
    @brief A small mesh of mapped bricks with a 1000-fold conductivity contrast: matrix values, load, volumes and the solution (direct) agree with the reference to 1e-11.
    @return None.
    """
    m = _distorted_model()
    r1, c1, v1, f1 = m._assemble_elements(chunk=37)                      # a chunk that does not divide the element count
    r0, c0, v0, f0 = _reference_elements(m, chunk=37)
    vn, vo = np.concatenate(v1), np.concatenate(v0)
    assert np.allclose(vn, vo, rtol=1e-11, atol=1e-12 * np.abs(vo).max())
    assert np.allclose(f1, f0, rtol=1e-11, atol=1e-12 * np.abs(f0).max())
    vol_ref = sum(np.abs(np.linalg.det(np.einsum("eai,aj->eij", m.nodes[m.elems], femcore.shape(gx, gy, gz)[1])))
                  for gx in (-femcore.G1, femcore.G1) for gy in (-femcore.G1, femcore.G1) for gz in (-femcore.G1, femcore.G1))
    assert np.allclose(m.element_volumes(), vol_ref, rtol=1e-12)
    sol = m.solve(force="direct")
    assert abs(sol["balance"] - 1.0) < 1e-9


def test_a_degenerate_element_is_still_refused_and_cg_agrees_with_direct():
    """!
    @brief `validate` still refuses a flat element (zero determinant) with ValueError, and the CG at the new tolerance (1e-10) is within 1e-8 K of the direct solution.
    @return None.
    """
    nodes = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]], float) * 1e-3
    bad = femcore.Model(nodes, np.arange(8)[None, :])
    bad.add_faces(np.array([[0, 1, 2, 3]]), h=10.0, t_amb=25.0)
    with pytest.raises(ValueError, match="degenerate"):
        bad.validate()
    if not femcore.available():
        pytest.skip("pyamg is not installed")
    m = _distorted_model(5)
    td = m.solve(force="direct")["T"]
    sol = m.solve(force="cg")
    assert np.nanmax(np.abs(sol["T"] - td)) < 1e-8
    assert sol["residual"] < 1e-8
