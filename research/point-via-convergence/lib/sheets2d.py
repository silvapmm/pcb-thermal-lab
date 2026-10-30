#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file sheets2d.py
@brief Independent solver of the layered model (conducting sheets coupled by vertical conductances) with a via resolved on a fine grid, and the exact solutions it is checked against.
@details This is the model of the program (one node per layer and cell, the sheet conductance S between neighbours, a vertical conductance per cell between neighbouring
         layers, films to the ambient) written again without importing the program, so that the via can be drawn at its real size on a grid much finer than the via:
         the barrel conductance of every gap is distributed over the cells in proportion to the area of the disc of the via inside each cell (`disc_fraction`), which
         converges to the continuum as the cell shrinks. Used as the reference for the discretisation of the via (not for the idealisation of the layers: that is the job of
         the 3D solver `layered3d.py`).
         `lone_via_exact` is the closed form of an equipotential via of radius a in an infinite sheet with a uniform loss h and a uniform source q:
         T(r) = (q / h)(1 - K0(r / lam) / K0(a / lam)), lam = sqrt(S / h), the heat taken by the via I = 2 pi S (a / lam) (q / h) K1(a / lam) / K0(a / lam).
"""

import math

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from scipy.special import k0, k1


def disc_fraction(cx, cy, radius, dx, nx, ny, sub=24, origin=0.0):
    """!
    @brief Share of every cell that lies inside a disc.
    @param cx Centre x in m.
    @param cy Centre y in m.
    @param radius Radius in m.
    @param dx Cell size in m.
    @param nx Cells along x.
    @param ny Cells along y.
    @param sub Samples per cell side.
    @param origin Position of the lower edge of cell 0 in m.
    @return numpy.ndarray (ny, nx) of fractions in [0, 1].
    """
    out = np.zeros((ny, nx))
    j0, j1 = max(int(math.floor((cx - radius - origin) / dx)), 0), min(int(math.floor((cx + radius - origin) / dx)), nx - 1)
    i0, i1 = max(int(math.floor((cy - radius - origin) / dx)), 0), min(int(math.floor((cy + radius - origin) / dx)), ny - 1)
    s = (np.arange(sub) + 0.5) / sub
    for j in range(j0, j1 + 1):
        for i in range(i0, i1 + 1):
            X, Y = np.meshgrid(origin + (j + s) * dx, origin + (i + s) * dx)
            out[i, j] = np.mean((X - cx) ** 2 + (Y - cy) ** 2 <= radius ** 2)
    return out


def solve(S, gz, g_amb, Q, dx, fixed=None):
    """!
    @brief Steady state of L sheets on a square grid.
    @param S Sheet conductance (L, ny, nx) in W/K (the conductance between two neighbouring cells of a square grid is S; the harmonic mean joins different cells).
    @param gz Vertical conductance between layer l and l+1 of every cell (L-1, ny, nx) in W/K.
    @param g_amb Conductance of every node to the ambient (L, ny, nx) in W/K.
    @param Q Heat injected at every node (L, ny, nx) in W.
    @param dx Cell size in m (unused by the equations, kept for the record).
    @param fixed Optional boolean array (L, ny, nx) of nodes held at the ambient (rise 0).
    @return numpy.ndarray (L, ny, nx) of rises in K.
    @note Insulated border. A fixed node is treated by a conductance of 1e9 times the largest one to the ambient.
    """
    L, ny, nx = S.shape
    n = L * ny * nx
    idx = np.arange(n).reshape(L, ny, nx)
    rows, cols, vals = [], [], []
    diag = np.array(g_amb, dtype=float).ravel()

    def link(a, b, g):
        a, b, g = a.ravel(), b.ravel(), np.broadcast_to(g, a.shape).ravel()
        rows.extend([a, b])
        cols.extend([b, a])
        vals.extend([-g, -g])
        np.add.at(diag, a, g)
        np.add.at(diag, b, g)

    def harm(a, b):
        s = a + b
        return np.where(s > 0, 2.0 * a * b / np.where(s > 0, s, 1.0), 0.0)

    link(idx[:, :, :-1], idx[:, :, 1:], harm(S[:, :, :-1], S[:, :, 1:]))
    link(idx[:, :-1, :], idx[:, 1:, :], harm(S[:, :-1, :], S[:, 1:, :]))
    for l in range(L - 1):
        link(idx[l], idx[l + 1], gz[l])
    if fixed is not None:
        diag[fixed.ravel()] += 1e9 * float(max(S.max(), 1e-30))
    K = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsr() + sp.diags(diag)
    T = spla.spsolve(K.tocsc(), np.asarray(Q, float).ravel(), permc_spec="MMD_AT_PLUS_A")
    return T.reshape(L, ny, nx)


def lone_via_exact(s_sheet, h, a, q):
    """!
    @brief Closed form of an equipotential (fixed temperature) via of radius a in an infinite sheet with a uniform loss and a uniform source.
    @param s_sheet Sheet conductance S in W/K.
    @param h Loss per area to the ambient in W/m2K.
    @param a Via radius in m.
    @param q Uniform source in W/m2.
    @return dict with 'lam' (m), 'I' (heat taken by the via in W) and 'T' (a function of r giving the rise).
    """
    lam = math.sqrt(s_sheet / h)
    i_via = 2.0 * math.pi * s_sheet * (a / lam) * (q / h) * k1(a / lam) / k0(a / lam)
    return {"lam": lam, "I": i_via, "T": lambda r: (q / h) * (1.0 - k0(r / lam) / k0(a / lam))}
