#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file halfgap_fd.py
@brief Independent 2D finite-volume solution of the laminate half-gap at a board edge (imports nothing from pcbthermal): the check of the closed-form efficiency of edge_rules.eta_laminate and the
       picture of the temperature field in the laminate.
@details Domain: x from the edge (x = 0, film h) into the board, z from the copper layer (z = 0, held at theta = 1) to the middle of the gap (z = d / 2, symmetry). The far end (x = length)
         is held at theta = 1. Cells are graded in x, fine at the edge. The film sits behind half a cell of conduction. Tests: tests/test_edge_rules.py.
"""

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla


def solve(h, d, kxy, kz, nz=60, nx=400, length=None):
    """!
    @brief Solve the half-gap.
    @param h Edge coefficient in W/m2K.
    @param d Gap thickness in m.
    @param kxy In-plane conductivity in W/mK.
    @param kz Through conductivity in W/mK.
    @param nz Cells through the half gap.
    @param nx Cells along x.
    @param length Domain length in m (default 12 d).
    @return Tuple (x cell centres in m, z cell centres in m, theta (nz, nx), efficiency = edge loss over h d / 2).
    """
    H = d / 2.0
    length = 12.0 * d if length is None else length
    dz = H / nz
    xe = np.concatenate([[0.0], np.cumsum(np.geomspace(dz / 4, length / 20, nx))])
    xe = xe / xe[-1] * length
    dx = np.diff(xe)
    xc = 0.5 * (xe[:-1] + xe[1:])
    n = nz * nx
    idx = np.arange(n).reshape(nz, nx)
    rows, cols, vals, b, diag = [], [], [], np.zeros(n), np.zeros(n)
    for i in range(nz):
        for j in range(nx):
            k = idx[i, j]
            if j + 1 < nx:
                g = kxy * dz / ((dx[j] + dx[j + 1]) / 2.0)
                rows += [k, idx[i, j + 1]]
                cols += [idx[i, j + 1], k]
                vals += [-g, -g]
                diag[k] += g
                diag[idx[i, j + 1]] += g
            if i + 1 < nz:
                g = kz * dx[j] / dz
                rows += [k, idx[i + 1, j]]
                cols += [idx[i + 1, j], k]
                vals += [-g, -g]
                diag[k] += g
                diag[idx[i + 1, j]] += g
    for j in range(nx):                                    # copper face (theta = 1) through half a cell
        g = kz * dx[j] / (dz / 2.0)
        diag[idx[0, j]] += g
        b[idx[0, j]] += g
    gf = 1.0 / (1.0 / (h * dz) + (dx[0] / 2.0) / (kxy * dz))
    for i in range(nz):
        g = kxy * dz / (dx[-1] / 2.0)                      # far field (theta = 1)
        diag[idx[i, -1]] += g
        b[idx[i, -1]] += g
        diag[idx[i, 0]] += gf                              # edge film
    A = sp.coo_matrix((vals, (rows, cols)), shape=(n, n)).tocsr() + sp.diags(diag)
    th = spla.spsolve(A.tocsc(), b).reshape(nz, nx)
    eta = float(gf * th[:, 0].sum() / (h * H))
    zc = (np.arange(nz) + 0.5) * dz
    return xc, zc, th, eta
