#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file axisym_cell.py
@brief Independent axisymmetric finite-volume solver of a via unit cell (a cylinder of via material in a substrate), written for the reproduction of the microspreading case of Fish (2017).
@details The cell is the equal-area disc of the square unit cell of pitch P: radius R = P / sqrt(pi). Cylindrical coordinates (r, z), z = 0 the isothermal bottom, z = L the top,
         the lateral side insulated (periodic array). Material k_v for r < a and k_s outside. The top face carries either a convection condition h (T_a - T) or a uniform flux. The solver is
         cell-centred finite volumes on graded grids (fine at the via wall and at the top face), harmonic means of the conductivities, direct sparse solution; nothing of the program is used.
         `unit_cell_resistance` returns the total resistance of the cell R_T = (mean top temperature - bottom temperature) / heat, from which the microspreading resistance follows by
         subtracting the one-dimensional resistance of the rule of mixtures.
"""

import math

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla


def graded(n, length, first):
    """!
    @brief A grid of n cells on [0, length] with geometric growth from a first cell size.
    @param n Number of cells.
    @param length Length in m.
    @param first Size of the first cell in m.
    @return numpy.ndarray of n + 1 edges.
    """
    # growth ratio q solves first * (q^n - 1) / (q - 1) = length
    lo, hi = 1.0 + 1e-9, 1.5
    if first * n >= length:
        return np.linspace(0.0, length, n + 1)
    for _ in range(200):
        q = 0.5 * (lo + hi)
        if first * (q ** n - 1.0) / (q - 1.0) > length:
            hi = q
        else:
            lo = q
    sizes = first * q ** np.arange(n)
    return np.concatenate([[0.0], np.cumsum(sizes)]) * (length / sizes.sum())


def two_sided(n, length, first):
    """!
    @brief A grid on [0, length] refined at both ends.
    @param n Number of cells (even).
    @param length Length in m.
    @param first Size of the end cells in m.
    @return numpy.ndarray of n + 1 edges.
    """
    h = graded(n // 2, length / 2, first)
    return np.concatenate([h, length - h[::-1][1:]])


def unit_cell_resistance(a, pitch, length, k_v, k_s, h_top=None, nr=160, nz=160):
    """!
    @brief Total resistance of a via unit cell with an isothermal bottom.
    @param a Via radius in m.
    @param pitch Pitch of the square unit cell in m.
    @param length Cell thickness in m.
    @param k_v Conductivity of the via in W/mK.
    @param k_s Conductivity of the substrate in W/mK.
    @param h_top Convection coefficient of the top face in W/m2K (None: uniform flux; inf-like values approach an isothermal top).
    @param nr Radial cells.
    @param nz Axial cells.
    @return float R_T = (area mean of the top temperature - bottom temperature) / total heat, in K/W (cell area pitch^2).
    @note The cell is the equal-area disc of radius pitch / sqrt(pi) and the heat is that of the disc scaled to the square area, so that R_T refers to the square cell.
    """
    rc = pitch / math.sqrt(math.pi)
    # radial grid: fine around the via wall (two-sided refinement inside and outside it)
    n_in = nr // 3
    r_in = a * (1.0 - graded(n_in, a, a / 60.0)[::-1] / a)
    r_out = a + graded(nr - n_in, rc - a, a / 60.0)
    re = np.concatenate([r_in[:-1], r_out]) if r_in[-1] == a else np.concatenate([r_in, r_out[1:]])
    re[0] = 0.0
    ze = length - graded(nz, length, min(length / 200.0, pitch / 40.0))[::-1]      # fine at the top face, where the flux enters
    ze[0] = 0.0
    ze[-1] = length
    rcen = 0.5 * (re[1:] + re[:-1])
    zcen = 0.5 * (ze[1:] + ze[:-1])
    dr = np.diff(re)
    dz = np.diff(ze)
    nrr, nzz = len(rcen), len(zcen)
    kk = np.where(rcen[None, :] < a, k_v, k_s) * np.ones((nzz, 1))                     # (nz, nr)
    idx = np.arange(nzz * nrr).reshape(nzz, nrr)
    rows, cols, vals = [], [], []
    diag = np.zeros(nzz * nrr)
    # radial conductances between cells (i, j) and (i, j+1): 2 pi r_face dz / (dr_a / (2 k_a) + dr_b / (2 k_b))
    rf = re[1:-1]
    gr = 2 * math.pi * rf[None, :] * dz[:, None] / (dr[None, :-1] / (2 * kk[:, :-1]) + dr[None, 1:] / (2 * kk[:, 1:]))
    # axial conductances between (i, j) and (i+1, j): area / (dz_a / (2 k_a) + dz_b / (2 k_b))
    area = math.pi * (re[1:] ** 2 - re[:-1] ** 2)
    gz = area[None, :] / (dz[:-1, None] / (2 * kk[:-1, :]) + dz[1:, None] / (2 * kk[1:, :]))
    for g, a_idx, b_idx in ((gr, idx[:, :-1], idx[:, 1:]), (gz, idx[:-1, :], idx[1:, :])):
        ai, bi, gv = a_idx.ravel(), b_idx.ravel(), g.ravel()
        rows += [ai, bi]
        cols += [bi, ai]
        vals += [-gv, -gv]
        np.add.at(diag, ai, gv)
        np.add.at(diag, bi, gv)
    # bottom: isothermal (T = 0) through half a cell
    gb = area / (dz[0] / (2 * kk[0, :]))
    np.add.at(diag, idx[0, :], gb)
    rhs = np.zeros(nzz * nrr)
    top = idx[-1, :]
    if h_top is None:
        rhs[top] += area / area.sum()                                                  # unit total heat, uniform flux
    else:
        # convection to a fluid at 1 K: G = 1 / (dz / (2 k A) + 1 / (h A))
        gt = 1.0 / (dz[-1] / (2 * kk[-1, :] * area) + 1.0 / (h_top * area))
        np.add.at(diag, top, gt)
        rhs[top] += gt
    m = sp.csc_matrix((np.concatenate(vals + [diag]), (np.concatenate(rows + [np.arange(nzz * nrr)]), np.concatenate(cols + [np.arange(nzz * nrr)]))), shape=(nzz * nrr,) * 2)
    t = spla.spsolve(m, rhs).reshape(nzz, nrr)
    q_total = float((gb * t[0, :]).sum())                                              # heat leaving through the bottom
    # mean temperature of the top face: the cell value corrected to the face by the half-cell drop of the heat that crosses it
    t_top_cell = t[-1, :]
    flux_top = (rhs[top] - (gt * t_top_cell if h_top is not None else 0.0))
    t_face = t_top_cell + flux_top * dz[-1] / (2 * kk[-1, :] * area)
    t_mean = float((t_face * area).sum() / area.sum())
    return t_mean / q_total
