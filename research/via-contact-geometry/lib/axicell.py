#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file axicell.py
@brief Independent axisymmetric finite-volume unit cell of one via through a stack of copper planes and dielectric gaps (imports nothing from the program).
@details The cell of the layered idealisation of the program: an equal-area disc, the copper planes continuous across the drill (the barrel is a vertical conductor between
         the planes), a uniform heat flux over the whole top, an isothermal bottom face, an insulated side. The stack is a list of (thickness, is_copper) from the top down; the
         copper has k_cu in both directions, the dielectric k_z through and k_r in the plane, the hole is filled with a material of conductivity k_fill, the plating of
         thickness t_pth is copper. The result is R = (mean temperature of the top face) / (heat of the cell) in K/W. Same discretisation family as the cell of
         `research/published-cases-followup` (rewritten here for an arbitrary stack; checked against the one-dimensional series circuit without a via and, for the
         stack of Shen and others, against the 207.52 K/W that study prints, in tests/test_via_contact_geometry.py; the review compared it with the independent
         Cartesian 3D solver tests/helpers/layered3d.py in scripts/study_barrel_reference3d.py). It leaves out a film on the bottom face, which the program's boards
         of the barrel study carry (1e7 W/m2K): add 1 / (h pitch^2) to compare.
"""

import math

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla


def _edges(points, counts):
    """!
    @brief Cell edges of consecutive intervals, each cut in a given number of equal parts.
    @param points Interval end points, length m + 1.
    @param counts Number of cells of each of the m intervals.
    @return numpy.ndarray of the edges.
    """
    out = [points[0]]
    for a, b, n in zip(points[:-1], points[1:], counts):
        out.extend(np.linspace(a, b, n + 1)[1:])
    return np.array(out)


def unit_cell(pitch, phi, k_fill, stack, k_cu=393.0, k_z=0.29, k_r=0.81, t_pth=25e-6, nr_out=48, nr_barrel=6, nr_hole=6, nz_cu=4, nz_gap=14, planes_over_hole=True, no_via=False):
    """!
    @brief Resistance of one via unit cell.
    @param pitch Side of the square unit cell in m (the disc of the same area is solved).
    @param phi Drill diameter in m.
    @param k_fill Conductivity of the hole filler in W/mK.
    @param stack List of (thickness in m, is_copper) from the top down.
    @param k_cu Copper conductivity in W/mK.
    @param k_z Through-plane conductivity of the dielectric in W/mK.
    @param k_r In-plane conductivity of the dielectric in W/mK.
    @param t_pth Plating thickness in m.
    @param nr_out Radial cells from the barrel to the cell wall.
    @param nr_barrel Radial cells across the plating.
    @param nr_hole Radial cells in the hole.
    @param nz_cu Vertical cells per copper plane.
    @param nz_gap Vertical cells per dielectric gap.
    @param planes_over_hole True: the planes are continuous over the drill.
    @param no_via True: the board without a via (the series circuit with the in-plane spreading of the planes, which is exact in one dimension).
    @return float R in K/W.
    """
    a = pitch / math.sqrt(math.pi)
    r_bar = phi / 2
    r_hole = max(r_bar - t_pth, 1e-9)
    ro = r_bar + (a - r_bar) * (np.geomspace(1.0, 20.0, nr_out + 1) - 1.0) / 19.0
    r_e = np.concatenate([np.linspace(0.0, r_hole, nr_hole + 1), np.linspace(r_hole, r_bar, nr_barrel + 1)[1:], ro[1:]])
    z_pts, nz_each = [0.0], []
    for th, cu in stack:
        z_pts.append(z_pts[-1] + th)
        nz_each.append(nz_cu if cu else nz_gap)
    z_e = _edges(z_pts, nz_each)
    nr, nz = len(r_e) - 1, len(z_e) - 1
    rc, zc = 0.5 * (r_e[1:] + r_e[:-1]), 0.5 * (z_e[1:] + z_e[:-1])
    is_cu_row = np.zeros(nz, dtype=bool)
    pos = 0.0
    for th, cu in stack:
        is_cu_row |= cu and ((zc > pos) & (zc < pos + th))
        pos += th
    kr = np.zeros((nz, nr))
    kz = np.zeros((nz, nr))
    for j in range(nz):
        for i in range(nr):
            if no_via:
                kr[j, i], kz[j, i] = (k_cu, k_cu) if is_cu_row[j] else (k_r, k_z)
            elif rc[i] < r_hole:
                kr[j, i] = kz[j, i] = k_cu if (planes_over_hole and is_cu_row[j]) else k_fill
            elif rc[i] < r_bar:
                kr[j, i] = kz[j, i] = k_cu
            elif is_cu_row[j]:
                kr[j, i] = kz[j, i] = k_cu
            else:
                kr[j, i], kz[j, i] = k_r, k_z
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
        diag[idx[nz - 1, i]] += area / (0.5 * dz[nz - 1] / kz[nz - 1, i])      # isothermal bottom face
    mat = sp.coo_matrix((vals, (rows, cols)), shape=(n, n)).tocsr() + sp.diags(diag)
    load = math.pi * (r_e[1:] ** 2 - r_e[:-1] ** 2)                             # the flux covers the whole top, the drill included
    q_in = np.zeros(n)
    q_in[idx[0, :]] = load / load.sum()
    temp = spla.spsolve(mat.tocsc(), q_in)
    t_face = temp[idx[0, :]] + (1.0 / load.sum()) * 0.5 * dz[0] / kz[0, :]
    return float((t_face * load).sum() / load.sum())


def equal_gap_stack(n_layers, t_board, t_cu):
    """!
    @brief Stack of n copper planes of equal thickness separated by equal dielectric gaps.
    @param n_layers Number of copper layers (at least 2).
    @param t_board Board thickness in m (copper included).
    @param t_cu Copper thickness in m.
    @return List of (thickness, is_copper) from the top down.
    """
    gap = (t_board - n_layers * t_cu) / (n_layers - 1)
    out = []
    for i in range(n_layers):
        out.append((t_cu, True))
        if i < n_layers - 1:
            out.append((gap, False))
    return out
