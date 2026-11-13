#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_manufactured.py
@brief Validation (4): manufactured solutions on a box (orthotropic conductivity, Robin on every face with a per-node ambient) and on the O-grid disc
       (a mapped mesh with a curved Robin boundary) converge at second order in the maximum nodal error.
"""

import numpy as np

import board
import fem
import mesh2d

KX, KY, KZ = 3.0, 2.0, 1.0
H = 7.0


def T_exact(x, y, z):
    """!
    @brief The manufactured field.
    @param x Coordinate.
    @param y Coordinate.
    @param z Coordinate.
    @return Value.
    """
    return np.cos(np.pi * x) * np.cos(2 * np.pi * y) * (1 + z) + 0.5 * z * z + 0.3 * x * y


def grad(x, y, z):
    """!
    @brief Gradient of the manufactured field.
    @param x Coordinate.
    @param y Coordinate.
    @param z Coordinate.
    @return Tuple (Tx, Ty, Tz).
    """
    tx = -np.pi * np.sin(np.pi * x) * np.cos(2 * np.pi * y) * (1 + z) + 0.3 * y
    ty = -2 * np.pi * np.cos(np.pi * x) * np.sin(2 * np.pi * y) * (1 + z) + 0.3 * x
    tz = np.cos(np.pi * x) * np.cos(2 * np.pi * y) + z
    return tx, ty, tz


def source(x, y, z):
    """!
    @brief -div(k grad T) of the manufactured field.
    @param x Coordinate.
    @param y Coordinate.
    @param z Coordinate.
    @return Value.
    """
    txx = -np.pi ** 2 * np.cos(np.pi * x) * np.cos(2 * np.pi * y) * (1 + z)
    tyy = -4 * np.pi ** 2 * np.cos(np.pi * x) * np.cos(2 * np.pi * y) * (1 + z)
    tzz = 1.0 + 0 * x
    return -(KX * txx + KY * tyy + KZ * tzz)


def _ambient(nodes, normal, kn):
    """!
    @brief Ambient per node that makes the Robin condition hold for the exact field: T_amb = T + k_n dT/dn / h.
    @param nodes Node coordinates (F, 4, 3).
    @param normal Outward unit normal (F, 4, 3) or (3,).
    @param kn Conductivity along the normal, per node (F, 4) or scalar.
    @return (F, 4) ambient.
    """
    x, y, z = nodes[..., 0], nodes[..., 1], nodes[..., 2]
    g = np.stack(grad(x, y, z), axis=-1)
    dn = (g * normal).sum(axis=-1)
    return T_exact(x, y, z) + kn * dn / H


def _box(n):
    """!
    @brief Solve the manufactured problem on the box [0, 1] x [0, 0.5] x [0, 0.2] with n x n/2 x n/5 elements (uniform).
    @param n Elements along x.
    @return Maximum nodal error.
    """
    xn, yn, zn = np.linspace(0, 1, n + 1), np.linspace(0, 0.5, n // 2 + 1), np.linspace(0, 0.2, max(n // 5, 2) + 1)
    plan = mesh2d.tensor(xn, yn)
    ex = board.extrude(plan, np.diff(zn))
    m = fem.Model(ex["nodes"], ex["elems"])
    m.k[:] = [KX, KY, KZ]
    c = m.nodes[m.elems].mean(axis=1)
    m.q[:] = source(c[:, 0], c[:, 1], c[:, 2])
    Np = ex["n_plan"]
    nz = zn.size - 1
    for faces, normal, kn in ((plan.quads, np.array([0, 0, -1.0]), KZ), (plan.quads + nz * Np, np.array([0, 0, 1.0]), KZ)):
        m.add_faces(faces, h=H, t_amb=_ambient(m.nodes[faces], normal, kn))
    edges, _ = plan.boundary_edges()
    mid = plan.xy[edges].mean(axis=1)
    for s in range(nz):
        f = np.column_stack([edges[:, 0] + s * Np, edges[:, 1] + s * Np, edges[:, 1] + (s + 1) * Np, edges[:, 0] + (s + 1) * Np])
        nrm = np.zeros((f.shape[0], 3))
        nrm[np.isclose(mid[:, 0], 0.0), 0] = -1.0
        nrm[np.isclose(mid[:, 0], 1.0), 0] = 1.0
        nrm[np.isclose(mid[:, 1], 0.0), 1] = -1.0
        nrm[np.isclose(mid[:, 1], 0.5), 1] = 1.0
        kn = np.where(np.abs(nrm[:, 0]) > 0, KX, KY)
        m.add_faces(f, h=H, t_amb=_ambient(m.nodes[f], nrm[:, None, :], kn[:, None]))
    r = m.solve()
    ex_T = T_exact(m.nodes[:, 0], m.nodes[:, 1], m.nodes[:, 2])
    return float(np.abs(r["T"] - ex_T).max())


def test_box_converges_at_second_order():
    """!
    @brief Uniform boxes with 10, 20, 40 elements along x: the maximum nodal error falls as h^2 (rate above 1.9).
    @return None.
    """
    e = [_box(n) for n in (10, 20, 40)]
    r1 = np.log(e[0] / e[1]) / np.log(2)
    r2 = np.log(e[1] / e[2]) / np.log(2)
    assert e[-1] < 5e-3, e
    assert r2 > 1.9, (e, r1, r2)


def _disc(n_side):
    """!
    @brief Solve the manufactured problem (isotropic k = KZ) on the unit disc extruded 0.2 with Robin faces, the curved wall included.
    @param n_side O-grid inner square divisions.
    @return Maximum nodal error.
    """
    k = KZ
    plan = mesh2d.disc(1.0, n_side, n_rings=max(n_side // 2, 2))
    nz = max(n_side // 4, 2)
    ex = board.extrude(plan, np.full(nz, 0.2 / nz))
    m = fem.Model(ex["nodes"], ex["elems"])
    m.k[:] = [k, k, k]
    c = m.nodes[m.elems].mean(axis=1)
    x, y, z = c[:, 0], c[:, 1], c[:, 2]
    txx = -np.pi ** 2 * np.cos(np.pi * x) * np.cos(2 * np.pi * y) * (1 + z)
    tyy = -4 * np.pi ** 2 * np.cos(np.pi * x) * np.cos(2 * np.pi * y) * (1 + z)
    m.q[:] = -k * (txx + tyy + 1.0)
    Np = ex["n_plan"]
    for faces, normal in ((plan.quads, np.array([0, 0, -1.0])), (plan.quads + nz * Np, np.array([0, 0, 1.0]))):
        m.add_faces(faces, h=H, t_amb=_ambient(m.nodes[faces], normal, k))
    edges, _ = plan.boundary_edges()
    for s in range(nz):
        f = np.column_stack([edges[:, 0] + s * Np, edges[:, 1] + s * Np, edges[:, 1] + (s + 1) * Np, edges[:, 0] + (s + 1) * Np])
        X = m.nodes[f]
        nrm = np.zeros_like(X)
        nrm[..., 0] = X[..., 0]                                     # the exact outward normal of the circle at every node
        nrm[..., 1] = X[..., 1]
        m.add_faces(f, h=H, t_amb=_ambient(X, nrm, k))
    r = m.solve()
    ex_T = T_exact(m.nodes[:, 0], m.nodes[:, 1], m.nodes[:, 2])
    return float(np.abs(r["T"] - ex_T).max())


def test_disc_converges_at_second_order():
    """!
    @brief The O-grid disc (mapped bricks, a polygonal wall carrying the Robin condition of the circle) converges at second order too.
    @return None.
    """
    e = [_disc(n) for n in (6, 12, 24)]
    r2 = np.log(e[1] / e[2]) / np.log(2)
    assert e[-1] < 1e-2, e
    assert r2 > 1.8, (e, r2)
