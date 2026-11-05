#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file layered3d_side.py
@brief Independent steady 3D finite-volume solver of a laminated plate with film coefficients on both faces AND on the four side faces (imports nothing from pcbthermal).

@details Rebuilt in the library from the scratch solver of research/models-comparison/scripts/study_analytic_edge_transfer.py (the reviewer's reference): every copper layer and
         every dielectric sub-slab is a slab, FR-4 in plane / through conductivity as given, the film behind half a cell on every face, the side film behind half a
         cell of the slab on the outer cells of every slab. The tests check it against a series circuit through the thickness and an energy balance.
"""

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla


def solve_3d(dx, nx, ny, slabs, source, power, h_face, h_side, h_top=None):
    """!
    @brief Independent steady 3D finite volumes of a laminated plate with films on both faces and on the four sides.
    @param dx Cell size in the plane in m (square cells).
    @param nx Cells along x.
    @param ny Cells along y.
    @param slabs List of (thickness m, k in plane W/mK, k through W/mK, sub-slabs) from the top down.
    @param source (x0, y0, x1, y1) of the heated rectangle of the top face in m, on cell edges.
    @param power Power in W, spread uniformly over the source cells.
    @param h_face Film coefficient of the bottom face (and of the top face when h_top is None) in W/m2K (on the whole top face, also under the source).
    @param h_side Film coefficient of the side faces in W/m2K.
    @param h_top Film coefficient of the top face when it differs from h_face (0 = adiabatic top outside the source, as in the flux channel of the papers).
    @return Tuple (top-slab field in K, heat out by faces and sides in W).
    """
    h_top = h_face if h_top is None else h_top
    dz, kin, kth = [], [], []
    for t, ki, kt, n in slabs:
        dz += [t / n] * n
        kin += [ki] * n
        kth += [kt] * n
    dz, kin, kth = np.array(dz), np.array(kin), np.array(kth)
    nz = len(dz)
    n = nz * ny * nx
    idx = np.arange(n).reshape(nz, ny, nx)
    rows, cols, vals = [], [], []
    diag = np.zeros(n)

    def link(a, b, g):
        """!
        @brief Add the conductance g between the node arrays a and b (symmetric).
        @param a Node indices.
        @param b Node indices.
        @param g Conductance in W/K (scalar or array).
        @return None.
        """
        g = np.broadcast_to(g, a.shape)
        rows.extend([a.ravel(), b.ravel()])
        cols.extend([b.ravel(), a.ravel()])
        vals.extend([-g.ravel(), -g.ravel()])
        np.add.at(diag, a.ravel(), g.ravel())
        np.add.at(diag, b.ravel(), g.ravel())

    area = dx * dx
    for k in range(nz):                                   # in-plane links: k dz dy / dx with dy = dx
        link(idx[k, :, :-1], idx[k, :, 1:], kin[k] * dz[k])
        link(idx[k, :-1, :], idx[k, 1:, :], kin[k] * dz[k])
    for k in range(nz - 1):                               # vertical links: two half cells in series
        link(idx[k], idx[k + 1], 1.0 / (dz[k] / (2 * kth[k] * area) + dz[k + 1] / (2 * kth[k + 1] * area)))
    g_top = 1.0 / (dz[0] / (2 * kth[0] * area) + 1.0 / (max(h_top, 1e-300) * area)) if h_top > 0 else 0.0     # film behind half a cell
    g_bot = 1.0 / (dz[-1] / (2 * kth[-1] * area) + 1.0 / (h_face * area))
    diag[idx[0].ravel()] += g_top
    diag[idx[-1].ravel()] += g_bot
    g_side = np.zeros((nz, ny, nx))
    for k in range(nz):                                   # side film behind half a cell of the slab, on the outer cells of every slab
        g = 1.0 / (dx / (2 * kin[k] * dz[k] * dx) + 1.0 / (h_side * dz[k] * dx)) if h_side > 0 else 0.0
        g_side[k, :, 0] += g
        g_side[k, :, -1] += g
        g_side[k, 0, :] += g
        g_side[k, -1, :] += g
    diag += g_side.ravel()
    xs = (np.arange(nx) + 0.5) * dx
    ys = (np.arange(ny) + 0.5) * dx
    m = (xs[None, :] > source[0]) & (xs[None, :] < source[2]) & (ys[:, None] > source[1]) & (ys[:, None] < source[3])
    q = np.zeros(n)
    q[idx[0][m]] = power / m.sum()
    K = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsr() + sp.diags(diag)
    T = spla.spsolve(K.tocsc(), q).reshape(nz, ny, nx)
    out = g_top * T[0].sum() + g_bot * T[-1].sum() + float((g_side * T).sum())
    return T[0], out
