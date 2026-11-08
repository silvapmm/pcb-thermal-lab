#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file cart_cell.py
@brief A Cartesian three-dimensional finite-volume model of the SQUARE via unit of Shen and others (anisotropic FR-4, plated barrel, copper layers, uniform top flux, isothermal bottom, insulated sides): the reference that does not use the equal-area disc.
@details The axisymmetric unit cell replaces the square cell of side `pitch` by the disc of the same area. This solver keeps the square: cells of `dx` in the plane (partial-volume conductivity from an 8 x 8 sampling of every cell: copper
         barrel, filler, FR-4), the copper layers as slabs at the faces and at one third and two thirds of the thickness (the layer stack of `shen_case.layer_stack`), conductivity per cell in the plane (kxy) and
         through the thickness (kz), harmonic means between cells. Same two switches as `via_cell.unit_cell` (planes continuous over the drill, heat over the whole top). Imports nothing of the program.
"""

import sys
from pathlib import Path

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lumped-zones-adoption" / "lib"))
import shen_case as SC  # noqa: E402


def unit_cell(pitch, phi, k_fill, dx=None, nz_cu=4, dz_gap=40e-6, k_fr4_z=SC.K_FR4_THROUGH, k_fr4_r=SC.K_FR4_INPLANE, t_pth=SC.T_PTH, planes_over_hole=False, flux_over_hole=False, sub=8):
    """!
    @brief Resistance of one square via unit cell.
    @param pitch Side of the square cell in m.
    @param phi Drill diameter in m.
    @param k_fill Filler conductivity in W/mK.
    @param dx Cell in the plane in m (default: pitch / 36).
    @param nz_cu Cells per copper layer.
    @param dz_gap Target cell across the FR-4 gaps in m.
    @param k_fr4_z Through-plane FR-4 conductivity in W/mK.
    @param k_fr4_r In-plane FR-4 conductivity in W/mK.
    @param t_pth Plating thickness in m.
    @param planes_over_hole True: the copper planes continue across the drill.
    @param flux_over_hole True: the top flux is uniform over the whole cell.
    @param sub Sub-samples per cell side for the partial volumes.
    @return float Resistance of the cell in K/W (mean top temperature over the heat of the cell).
    """
    n = 36 if dx is None else int(round(pitch / dx))
    dx = pitch / n
    stack = SC.layer_stack()
    dz, is_cu = [], []
    for th, cu in stack:
        m = nz_cu if cu else max(int(round(th / dz_gap)), 2)
        dz += [th / m] * m
        is_cu += [cu] * m
    dz, is_cu = np.array(dz), np.array(is_cu)
    nz = len(dz)
    # fractions of the three materials in every plan cell, by sampling (centre of the cell on the axis of the via)
    s = (np.arange(n * sub) + 0.5) * dx / sub - pitch / 2
    xx, yy = np.meshgrid(s, s)
    r = np.hypot(xx, yy)
    f_hole = (r < phi / 2 - t_pth).astype(float)
    f_bar = ((r >= phi / 2 - t_pth) & (r < phi / 2)).astype(float)
    blk = lambda a: a.reshape(n, sub, n, sub).mean(axis=(1, 3))
    f_hole, f_bar = blk(f_hole), blk(f_bar)
    f_sol = 1.0 - f_hole - f_bar
    kxy = np.empty((nz, n, n))
    kzz = np.empty((nz, n, n))
    for j in range(nz):
        if is_cu[j]:
            fill = SC.K_CU if planes_over_hole else k_fill
            kxy[j] = kzz[j] = SC.K_CU * (f_sol + f_bar) + fill * f_hole
        else:
            kxy[j] = SC.K_CU * f_bar + k_fill * f_hole + k_fr4_r * f_sol
            kzz[j] = SC.K_CU * f_bar + k_fill * f_hole + k_fr4_z * f_sol
    idx = np.arange(nz * n * n).reshape(nz, n, n)
    rows, cols, vals = [], [], []
    diag = np.zeros(nz * n * n)

    def link(a, b, g):
        """!
        @brief Add a symmetric conductance.
        @param a Node indices.
        @param b Node indices.
        @param g Conductances in W/K.
        @return None.
        """
        a, b, g = a.ravel(), b.ravel(), np.asarray(g).ravel()
        rows.extend([a, b]); cols.extend([b, a]); vals.extend([-g, -g])
        np.add.at(diag, a, g); np.add.at(diag, b, g)

    for j in range(nz):                                                          # in-plane links: harmonic mean of the two cells, face dz dx, length dx
        for axis in (1, 2):
            sl_a = (slice(None), slice(0, -1)) if axis == 2 else (slice(0, -1), slice(None))
            sl_b = (slice(None), slice(1, None)) if axis == 2 else (slice(1, None), slice(None))
            ka, kb = kxy[j][sl_a], kxy[j][sl_b]
            link(idx[j][sl_a], idx[j][sl_b], dz[j] * dx / dx * 2.0 * ka * kb / (ka + kb))
    for j in range(nz - 1):                                                      # vertical links: half cells in series
        rr = dz[j] / (2 * kzz[j] * dx * dx) + dz[j + 1] / (2 * kzz[j + 1] * dx * dx)
        link(idx[j], idx[j + 1], 1.0 / rr)
    diag[idx[-1].ravel()] += (kzz[-1] * dx * dx / (0.5 * dz[-1])).ravel()        # bottom isothermal through half a cell
    mat = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(nz * n * n,) * 2).tocsr() + sp.diags(diag)
    load = np.ones((n, n)) if flux_over_hole else (1.0 - f_hole)
    q = np.zeros(nz * n * n)
    q[idx[0].ravel()] = (load / load.sum()).ravel()
    t = spla.spsolve(mat.tocsc(), q).reshape(nz, n, n)
    t_face = t[0] + (1.0 / (load.sum() * dx * dx)) * 0.5 * dz[0] / kzz[0]
    return float((t_face * load).sum() / load.sum())
