#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file via_cell.py
@brief The axisymmetric via unit cell of Shen and others (equal-area disc, uniform top flux, isothermal bottom, insulated side) with two switches that make it the cell of the program's idealisation: the copper planes continuous over the drill and the top flux over the whole cell.
@details A variant of `research/lumped-zones-adoption/lib/shen_case.py::unit_cell` (same grids and discretisation, which it imports for the stack and the edge helper; imports nothing of the program).
         `planes_over_hole=False, flux_over_hole=False` is the cell of the paper (the hole goes through the copper layers and the package heat cannot enter the air of an open hole): the result is identical
         to `shen_case.unit_cell` (tested). `planes_over_hole=True` keeps the copper of the planes across the drill (the layered models count the plane sheet over the drill, and the barrel is only a vertical conductor
         between the planes); `flux_over_hole=True` spreads the heat over the whole top, the drill included, as a heater of the program does.
"""

import math
import sys
from pathlib import Path

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lumped-zones-adoption" / "lib"))
import shen_case as SC  # noqa: E402

K_CU = SC.K_CU


def unit_cell(pitch, phi, k_fill, k_fr4_z=SC.K_FR4_THROUGH, k_fr4_r=SC.K_FR4_INPLANE, t_pth=SC.T_PTH, planes_over_hole=False, flux_over_hole=False, plane_kr_scale=1.0, nr_out=48, nr_barrel=6, nr_hole=6, nz_cu=4, nz_gap=14):
    """!
    @brief Resistance of one via unit cell by an axisymmetric finite-volume solve.
    @param pitch Side of the square unit cell in m (the disc of the same area is solved).
    @param phi Via (drill) diameter in m.
    @param k_fill Filler conductivity in W/mK.
    @param k_fr4_z Through-plane FR-4 conductivity in W/mK.
    @param k_fr4_r In-plane FR-4 conductivity in W/mK.
    @param t_pth Plating thickness in m.
    @param planes_over_hole True: the copper planes are continuous across the drill.
    @param flux_over_hole True: the top flux is uniform over the whole cell, the drill included.
    @param plane_kr_scale Multiplier of the radial conductivity of the copper planes outside the barrel (1: the real plane; a large value makes every plane
           radially isothermal and so removes the convergence of the heat in the planes onto the barrel, the term that the review separates in study_shen_vias.py part D).
    @param nr_out Radial cells from the barrel to the cell wall.
    @param nr_barrel Radial cells across the plating.
    @param nr_hole Radial cells in the hole.
    @param nz_cu Vertical cells per copper layer.
    @param nz_gap Vertical cells per FR-4 gap.
    @return float Resistance of the cell in K/W (mean top temperature over the heat of the cell).
    """
    a = pitch / math.sqrt(math.pi)
    r_hole, r_bar = phi / 2 - t_pth, phi / 2
    ro = r_bar + (a - r_bar) * (np.geomspace(1.0, 20.0, nr_out + 1) - 1.0) / 19.0
    r_e = np.concatenate([np.linspace(0.0, r_hole, nr_hole + 1), np.linspace(r_hole, r_bar, nr_barrel + 1)[1:], ro[1:]])
    stack = SC.layer_stack()
    z_pts, nz_each = [0.0], []
    for th, cu in stack:
        z_pts.append(z_pts[-1] + th)
        nz_each.append(nz_cu if cu else nz_gap)
    z_e = SC._edges(z_pts, nz_each)
    nr, nz = len(r_e) - 1, len(z_e) - 1
    rc, zc = 0.5 * (r_e[1:] + r_e[:-1]), 0.5 * (z_e[1:] + z_e[:-1])
    kr = np.zeros((nz, nr))
    kz = np.zeros((nz, nr))
    is_cu_row = np.zeros(nz, dtype=bool)
    pos = 0.0
    for th, cu in stack:
        is_cu_row |= cu and ((zc > pos) & (zc < pos + th))
        pos += th
    for j in range(nz):
        for i in range(nr):
            if rc[i] < r_hole:
                kr[j, i] = kz[j, i] = K_CU if (planes_over_hole and is_cu_row[j]) else k_fill
            elif rc[i] < r_bar:
                kr[j, i] = kz[j, i] = K_CU
            elif is_cu_row[j]:
                kr[j, i] = K_CU * plane_kr_scale                      # radial: the plane (scaled only for the review's separation of the constriction)
                kz[j, i] = K_CU
            else:
                kr[j, i], kz[j, i] = k_fr4_r, k_fr4_z
    dr, dz = np.diff(r_e), np.diff(z_e)
    n = nr * nz
    idx = np.arange(n).reshape(nz, nr)
    rows, cols, vals = [], [], []
    diag = np.zeros(n)

    def link(p, q, g):
        """!
        @brief Add a symmetric conductance.
        @param p Node.
        @param q Node.
        @param g Conductance in W/K.
        @return None.
        """
        rows.extend((p, q))
        cols.extend((q, p))
        vals.extend((-g, -g))
        diag[p] += g
        diag[q] += g
    for j in range(nz):
        for i in range(nr):
            p = idx[j, i]
            if i + 1 < nr:
                area = 2 * math.pi * r_e[i + 1] * dz[j]
                link(p, idx[j, i + 1], area / (0.5 * dr[i] / kr[j, i] + 0.5 * dr[i + 1] / kr[j, i + 1]))
            if j + 1 < nz:
                area = math.pi * (r_e[i + 1] ** 2 - r_e[i] ** 2)
                link(p, idx[j + 1, i], area / (0.5 * dz[j] / kz[j, i] + 0.5 * dz[j + 1] / kz[j + 1, i]))
    for i in range(nr):
        area = math.pi * (r_e[i + 1] ** 2 - r_e[i] ** 2)
        diag[idx[nz - 1, i]] += area / (0.5 * dz[nz - 1] / kz[nz - 1, i])
    mat = sp.coo_matrix((vals, (rows, cols)), shape=(n, n)).tocsr() + sp.diags(diag)
    top_area = math.pi * (r_e[1:] ** 2 - r_e[:-1] ** 2)
    load = top_area if flux_over_hole else np.where(rc >= r_hole, top_area, 0.0)
    q_in = np.zeros(n)
    q_in[idx[0, :]] = load / load.sum()
    T = spla.spsolve(mat.tocsc(), q_in)
    t_face = T[idx[0, :]] + (1.0 / load.sum()) * 0.5 * dz[0] / kz[0, :]
    return float((t_face * load).sum() / load.sum())
