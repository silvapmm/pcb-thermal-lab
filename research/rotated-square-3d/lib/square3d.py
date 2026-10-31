#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file square3d.py
@brief An independent reference for the square board of the investigation: a quarter of a square laminate with real slabs, solved on cells that
       the edge never cuts, so that the continuum answer of the shifted and turned squares (which is the answer of the aligned one) can be
       extrapolated from a ladder of fine cells.
@details Written for the review of the investigation; imports nothing of the program (the slab list is passed in, for example from
         `axisym3d.slabs_of`). The board is a square of side `2 a` with a part centred on it; by symmetry only the quarter `0 < x, y < a` is solved,
         with insulated symmetry planes at `x = 0` and `y = 0`. Every slab is one layer of cells with its own in-plane and through conductivity
         (anisotropic FR-4), the films on the two faces act everywhere (also under the part, as the program does) in series with half a slab,
         the film on the outer sides acts on every slab in series with half a cell of in-plane conduction, and the power enters the top slab
         over the footprint of the part (an aligned square, or a square turned by 45 degrees, a diamond, which is also symmetric about both
         planes). The cells are square and the outer sides lie on cell faces at every cell size, so no cell is cut: the answer converges as the
         square of the cell, and a Richardson step over two cells gives the continuum value.
"""

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla


def solve_quarter(side, part, power, slabs, h_top, h_bottom, h_side, n, diamond=False, samples=16):
    """!
    @brief Steady rise of a square laminate with a centred part, solved on its quarter.
    @param side Side of the board in m.
    @param part Side of the square part in m.
    @param power Power of the part in W (the whole part; the quarter carries a quarter).
    @param slabs List of (dz in m, in-plane k, through k in W/mK) from the top face down.
    @param h_top Film coefficient on the top face in W/m2K (> 0).
    @param h_bottom Film coefficient on the bottom face in W/m2K (> 0).
    @param h_side Film coefficient on the sides in W/m2K (0 = insulated sides).
    @param n Cells along the half side.
    @param diamond True: the part is the square turned by 45 degrees (|x| + |y| <= part / sqrt(2)), sampled on samples x samples points per cell.
    @param samples Sample points per cell side for the diamond.
    @return dict with t_centre (rise of the top-slab cell at the centre, K), balance (heat to the air over the power), cell (m).
    """
    a = side / 2.0
    d = a / n
    ns = len(slabs)
    idx = np.arange(ns * n * n).reshape(ns, n, n)
    rows, cols, vals = [], [], []
    diag = np.zeros(ns * n * n)

    def couple(i, j, g):
        # Symmetric conductance between the node arrays i and j
        g = np.broadcast_to(g, i.shape)
        rows.append(i.ravel())
        cols.append(j.ravel())
        vals.append(-g.ravel())
        np.add.at(diag, i.ravel(), g.ravel())
        np.add.at(diag, j.ravel(), g.ravel())

    for s, (dz, kr, kz) in enumerate(slabs):
        # Square cells: the in-plane conductance is k dz (face d dz over distance d)
        couple(idx[s, :, :-1], idx[s, :, 1:], kr * dz)
        couple(idx[s, :-1, :], idx[s, 1:, :], kr * dz)
        if s < ns - 1:
            dz2, _, kz2 = slabs[s + 1]
            couple(idx[s], idx[s + 1], d * d / (dz / (2.0 * kz) + dz2 / (2.0 * kz2)))
    g_top = d * d / (1.0 / h_top + slabs[0][0] / (2.0 * slabs[0][2]))
    g_bot = d * d / (1.0 / h_bottom + slabs[-1][0] / (2.0 * slabs[-1][2]))
    diag[idx[0].ravel()] += g_top
    diag[idx[-1].ravel()] += g_bot
    g_side = np.zeros((ns, n, n))
    if h_side > 0:
        for s, (dz, kr, _) in enumerate(slabs):
            # The outer sides x = a and y = a lie on cell faces: film in series with half a cell of the slab's in-plane conductivity
            g = 1.0 / (1.0 / (h_side * d * dz) + (0.5 * d) / (kr * d * dz))
            g_side[s, :, -1] += g
            g_side[s, -1, :] += g
    diag += g_side.ravel()
    K = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(diag.size, diag.size)).tocsr()
    K = (K + K.T + sp.diags(diag)).tocsc()
    # Footprint of the part on the quarter: exact cover of an aligned square, sampled cover of the diamond
    q = np.zeros((ns, n, n))
    if diamond:
        xs = (np.arange(n * samples) + 0.5) * d / samples
        X, Y = np.meshgrid(xs, xs)
        q[0] = (X + Y <= part / np.sqrt(2.0)).reshape(n, samples, n, samples).mean(axis=(1, 3))
    else:
        xc = (np.arange(n) + 0.5) * d
        w = np.clip(np.minimum(xc + d / 2.0, part / 2.0) - (xc - d / 2.0), 0.0, d) / d
        q[0] = np.outer(w, w)
    q[0] *= (power / 4.0) / q[0].sum()
    th = spla.spsolve(K, q.ravel()).reshape(ns, n, n)
    out = g_top * th[0].sum() + g_bot * th[-1].sum() + float((g_side * th).sum())
    return {"t_centre": float(th[0, 0, 0]), "balance": float(out / (power / 4.0)), "cell": d}


def richardson(coarse, fine, order=2.0):
    """!
    @brief Richardson extrapolation of two values on cells in the ratio 2.
    @param coarse Value on the coarser cell.
    @param fine Value on the cell half as large.
    @param order Order of convergence.
    @return Extrapolated value.
    """
    return fine + (fine - coarse) / (2.0 ** order - 1.0)
