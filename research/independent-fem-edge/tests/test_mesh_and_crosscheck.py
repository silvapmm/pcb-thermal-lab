#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_mesh_and_crosscheck.py
@brief Mesh checks (O-grid conformity, disc area, rigid rotation leaves the solution unchanged) and an optional cross-check of the assembly against
       scikit-fem (BSD-3) on the same box mesh (skipped when scikit-fem is not importable: it lives only in the scratch venv `research/independent-fem-edge/.venv-research`).
"""

import numpy as np
import pytest

import board
import fem
import mesh2d


def _edge_counts(q):
    """!
    @brief How many quads share each edge.
    @param q Quad2D.
    @return numpy.ndarray of counts per unique edge.
    """
    e = np.stack([q.quads, np.roll(q.quads, -1, axis=1)], axis=2).reshape(-1, 2)
    _, cnt = np.unique(np.sort(e, axis=1), axis=0, return_counts=True)
    return cnt


def test_ogrid_patch_is_conforming_and_the_disc_area_converges_to_pi_r2():
    """!
    @brief Every interior edge of an embedded O-grid is shared by two quads; the disc polygon area tends to pi R^2 at second order.
    @return None.
    """
    base = mesh2d.tensor(mesh2d.uniform_window(np.linspace(0, 10e-3, 21), 7e-3, 9e-3, 8), mesh2d.uniform_window(np.linspace(0, 5e-3, 11), 3e-3, 5e-3, 8))
    emb = mesh2d.embed_ogrid(base, 8e-3, 4e-3, 1e-3, 8, [0.15e-3, 0.4e-3], n_inner=1)
    cnt = _edge_counts(emb)
    assert cnt.max() == 2
    e, _ = emb.boundary_edges()
    mid = emb.xy[e].mean(axis=1)
    inner = (mid[:, 0] > 1e-9) & (mid[:, 0] < 10e-3 - 1e-9) & (mid[:, 1] > 1e-9) & (mid[:, 1] < 5e-3 - 1e-9)
    assert inner.sum() == 0
    assert (emb.areas() > 0).all()
    # the barrel ring is an exact annulus up to the chord error: tag 101 + 1 = ring between the first and second circle
    errs = []
    for n in (6, 12, 24):
        d = mesh2d.disc(1.0, n)
        errs.append(abs(d.areas().sum() - np.pi))
    assert errs[2] < errs[1] / 3.5 < errs[0] / 12


def test_rotating_the_board_does_not_change_the_solution():
    """!
    @brief A quarter board turned by 30 degrees about its corner (symmetry lines turned with it) gives the same temperatures to round-off: the FEM has no grid direction.
    @return None.
    """
    xn = mesh2d.grid1d(10e-3, [2e-3], [(0, 2.4e-3), (9e-3, 10e-3)], 0.2e-3, 1.3, 0.8e-3)
    plan = mesh2d.tensor(xn, xn)
    poly = np.array([[0, 0], [2e-3, 0], [2e-3, 2e-3], [0, 2e-3]])
    kw = dict(layers=2, h_top=10.0, h_bottom=10.0, h_side=200.0, n_gap=3, heaters=[(poly, 0.25)])
    b0 = board.Board(plan, symmetry=[("x", 0.0), ("y", 0.0)], copper=None, **kw)
    r0 = b0.solve()
    rot = plan.rotate(30.0)
    ang = np.radians(30.0)

    def wall(mid):
        """!
        @brief Edges that are not on the two turned symmetry lines.
        @param mid Edge midpoints.
        @return bool.
        """
        n1 = np.array([-np.sin(ang), np.cos(ang)])                   # normal of the turned x axis
        n2 = np.array([np.cos(ang), np.sin(ang)])                    # normal of the turned y axis
        return (np.abs(mid @ n1) > 1e-9) & (np.abs(mid @ n2) > 1e-9)
    polyr = np.column_stack([np.cos(ang) * poly[:, 0] - np.sin(ang) * poly[:, 1], np.sin(ang) * poly[:, 0] + np.cos(ang) * poly[:, 1]])
    kw["heaters"] = [(polyr, 0.25)]
    b1 = board.Board(rot, outline_wall=wall, copper=None, **kw)
    r1 = b1.solve()
    assert abs(r1["tmax"] - r0["tmax"]) < 1e-9 * r0["tmax"]
    assert abs(r1["heater_mean"] - r0["heater_mean"]) < 1e-9 * r0["heater_mean"]
    assert abs(r1["balance"] - 1) < 1e-9


def test_assembly_agrees_with_scikit_fem_on_the_same_mesh():
    """!
    @brief The Q1 stiffness, the Robin face mass and the source load of this solver reproduce scikit-fem's on an identical box mesh to 1e-10 (nodal temperatures).
    @return None.
    """
    skfem = pytest.importorskip("skfem")
    from skfem import MeshHex, ElementHex1, Basis, FacetBasis, BilinearForm, LinearForm, asm, solve
    from skfem.helpers import dot, grad
    xn, yn, zn = np.linspace(0, 2.0, 5), np.linspace(0, 1.0, 4), np.linspace(0, 0.5, 3)
    kx, ky, kz, h, q = 3.0, 2.0, 1.0, 4.0, 5.0
    # this solver
    plan = mesh2d.tensor(xn, yn)
    ex = board.extrude(plan, np.diff(zn))
    m = fem.Model(ex["nodes"], ex["elems"])
    m.k[:] = [kx, ky, kz]
    m.q[:] = q
    Np = ex["n_plan"]
    nz = zn.size - 1
    m.add_faces(plan.quads, h=h)
    m.add_faces(plan.quads + nz * Np, h=h)
    edges, _ = plan.boundary_edges()
    for s in range(nz):
        m.add_faces(np.column_stack([edges[:, 0] + s * Np, edges[:, 1] + s * Np, edges[:, 1] + (s + 1) * Np, edges[:, 0] + (s + 1) * Np]), h=h)
    r = m.solve()
    # scikit-fem
    mesh = MeshHex.init_tensor(xn, yn, zn)
    basis = Basis(mesh, ElementHex1())
    fb = FacetBasis(mesh, ElementHex1())

    @BilinearForm
    def stiff(u, v, w):
        """!
        @brief Orthotropic stiffness form.
        @param u Trial.
        @param v Test.
        @param w Context.
        @return Integrand.
        """
        return kx * grad(u)[0] * grad(v)[0] + ky * grad(u)[1] * grad(v)[1] + kz * grad(u)[2] * grad(v)[2]

    @BilinearForm
    def robin(u, v, w):
        """!
        @brief Robin face form.
        @param u Trial.
        @param v Test.
        @param w Context.
        @return Integrand.
        """
        return h * u * v

    @LinearForm
    def load(v, w):
        """!
        @brief Source form.
        @param v Test.
        @param w Context.
        @return Integrand.
        """
        return q * v
    A = asm(stiff, basis) + asm(robin, fb)
    t = solve(A, asm(load, basis))
    # match nodes by coordinates
    P = mesh.p.T
    key_s = np.round(P / 1e-9).astype(np.int64)
    key_m = np.round(m.nodes / 1e-9).astype(np.int64)
    ds = {tuple(k): i for i, k in enumerate(key_s)}
    order = np.array([ds[tuple(k)] for k in key_m])
    assert np.abs(r["T"] - t[order]).max() < 1e-10 * np.abs(t).max()
