#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file shen_case.py
@brief The published case of Shen, Wang, Blaabjerg, Zhao and Long (IEEE Trans. Power Electron. 35(1), 2020, pp. 882-900): a 5.6 x 5.6 mm, 1.6 mm, four-layer (70 um copper) PCB with a 12 x 12 array of
       open 0.25 mm vias under a uniform 1 W top flux, the bottom face at the ambient; the formulas of the paper (equations 2 to 5, Pattern I), an independent axisymmetric finite-volume solver of the via
       unit cell, and the same board as a `pcbthermal` Problem.
@details What the paper gives (accepted manuscript read in full for sections II to IV, figures rendered to images; page numbers are those of the 20-page accepted manuscript):
         * Fig. 17 (p. 14) caption: PCB 5.6 mm x 5.6 mm x 1.6 mm, 4 copper layers of 2 oz, 1 W on the top surface, the bottom surface fixed at 20 degC; text p. 14: the thermal resistance of the pad falls from
           120.3 K/W (no via) to 1.86 K/W (via diameter 0.25 mm), CFD in ANSYS Icepak 18.0. Fig. 17(c) shows 12 x 12 vias (counted on the image).
         * Equations (2) to (5) (p. 3 and 4): vertical resistances of a via unit (filler, barrel, copper + FR-4 layers), Pattern I unit (phi + s)^2 with the paper's s = 0.2 mm (p. 5, "s = 0.2 mm is used in the
           following analysis and experiments"), plating t_PTH = 25 um, Table I conductivities (copper 393, FR-4 0.29 through and 0.81 in plane, air 0.026 W/mK). `shen_array_resistance` implements them.
         * Fig. 18(a) (p. 14), air-filled Pattern I curve at phi = 0.25 mm: analytical about 1.82 and CFD about 1.85 K/W (READ FROM THE PLOT; the pad of that figure is the DPAK pad of the paper, whose size is
           not stated in the text read).
         Assumed here (not stated in the text read): the unit pitch 0.45 mm = phi + s, so 12 vias fill 5.4 mm of the 5.6 mm; copper layers at the two faces and at one third and two thirds of the thickness; the via
         hole passes through every layer; the FR-4 isotropic ratio of Table I (0.29 through, 0.81 in plane); the top flux uniform over the solid top (the hole is excluded: the package heat cannot enter the air of the open hole).
         The axisymmetric solver replaces the square unit cell by the disc of equal area (radius a = pitch / sqrt(pi)), cell-centred finite volumes on graded grids with harmonic means; it imports nothing of
         the program. `unit_cell` returns the resistance R_cell = (area mean of the top temperature) / (heat of the cell); the array resistance is R_cell / N.
"""

import math
import os
import sys

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Table I of the paper (p. 4), W/mK
K_CU, K_FR4_THROUGH, K_FR4_INPLANE, K_AIR = 393.0, 0.29, 0.81, 0.026
T_BOARD, T_CU, N_CU, T_PTH = 1.6e-3, 70e-6, 4, 25e-6      # Fig. 17 caption: 1.6 mm, 2 oz = 70 um, 4 layers; p. 4: plating 25 um
SIDE = 5.6e-3                                                 # Fig. 17 caption
PHI, SPACING = 0.25e-3, 0.2e-3                                # via diameter (Fig. 17) and via-to-via spacing (p. 5)
N_SIDE = 12                                                   # vias per side counted on Fig. 17(c)


def shen_unit_resistance(phi=PHI, s=SPACING, k_fill=K_AIR, k_fr4=K_FR4_THROUGH, t=T_BOARD, t_cu=T_CU, n_cu=N_CU, t_pth=T_PTH, pattern=1):
    """!
    @brief Vertical thermal resistance of one via unit, equations (2) and (3) of the paper.
    @param phi Via diameter in m.
    @param s Via-to-via spacing in m.
    @param k_fill Conductivity of the via filler in W/mK.
    @param k_fr4 Through-plane FR-4 conductivity in W/mK.
    @param t Board thickness in m.
    @param t_cu Copper layer thickness in m.
    @param n_cu Number of copper layers.
    @param t_pth Plating thickness in m.
    @param pattern 1 (square unit (phi + s)^2) or 2 (rectangular unit sqrt(3)(phi + s)^2 / 2).
    @return float Resistance of the unit in K/W.
    """
    th_filler = t / (k_fill * math.pi * (phi / 2 - t_pth) ** 2)
    th_barrel = t / (K_CU * math.pi * t_pth * (phi - t_pth))
    area = (phi + s) ** 2 if pattern == 1 else math.sqrt(3.0) * (phi + s) ** 2 / 2.0
    th_layers = (n_cu * t_cu / K_CU + (t - n_cu * t_cu) / k_fr4) / (area - math.pi * phi ** 2 / 4.0)
    return 1.0 / (1.0 / th_filler + 1.0 / th_barrel + 1.0 / th_layers)


def shen_array_resistance(n=N_SIDE, **kw):
    """!
    @brief Equation (4): the via units in parallel, n x n units.
    @param n Units per side.
    @param kw Arguments of `shen_unit_resistance`.
    @return float K/W.
    """
    return shen_unit_resistance(**kw) / (n * n)


def shen_no_via_resistance(side=SIDE, k_fr4=K_FR4_THROUGH, t=T_BOARD, t_cu=T_CU, n_cu=N_CU):
    """!
    @brief One-dimensional resistance of the board without vias (copper and FR-4 layers in series over the whole area).
    @param side Board side in m.
    @param k_fr4 Through-plane FR-4 conductivity in W/mK.
    @param t Board thickness in m.
    @param t_cu Copper layer thickness in m.
    @param n_cu Copper layers.
    @return float K/W.
    """
    return (n_cu * t_cu / K_CU + (t - n_cu * t_cu) / k_fr4) / (side * side)


def _edges(points, n_each):
    """!
    @brief Cell edges from a list of breakpoints with a number of cells in every interval.
    @param points Increasing breakpoints in m (first = 0).
    @param n_each Cells in every interval (list of len(points) - 1).
    @return numpy.ndarray of edges.
    """
    out = [points[0]]
    for a, b, n in zip(points[:-1], points[1:], n_each):
        out += list(np.linspace(a, b, n + 1)[1:])
    return np.array(out)


def layer_stack(t=T_BOARD, t_cu=T_CU, n_cu=N_CU):
    """!
    @brief Vertical layout of the stack from the top face: copper at both faces and the inner layers equally spaced.
    @param t Board thickness in m.
    @param t_cu Copper thickness in m.
    @param n_cu Copper layers.
    @return list of (thickness, is_copper) from the top down.
    """
    gap = (t - n_cu * t_cu) / (n_cu - 1)
    stack = []
    for i in range(n_cu):
        stack.append((t_cu, True))
        if i < n_cu - 1:
            stack.append((gap, False))
    return stack


def unit_cell(pitch=PHI + SPACING, phi=PHI, k_fill=K_AIR, k_fr4_z=K_FR4_THROUGH, k_fr4_r=K_FR4_INPLANE, t_pth=T_PTH, nr_out=48, nr_barrel=6, nr_hole=6, nz_cu=4, nz_gap=14):
    """!
    @brief Resistance of one via unit cell by an axisymmetric finite-volume solve (uniform top flux, isothermal bottom, insulated side).
    @param pitch Side of the square unit cell in m (the disc of the same area is solved).
    @param phi Via (drill) diameter in m: the hole inside the plating has the radius phi / 2 - t_pth.
    @param k_fill Filler conductivity in W/mK.
    @param k_fr4_z Through-plane FR-4 conductivity in W/mK.
    @param k_fr4_r In-plane FR-4 conductivity in W/mK.
    @param t_pth Plating in m.
    @param nr_out Radial cells from the barrel to the cell wall (graded, fine at the barrel).
    @param nr_barrel Radial cells across the plating.
    @param nr_hole Radial cells in the hole.
    @param nz_cu Vertical cells per copper layer.
    @param nz_gap Vertical cells per FR-4 gap (graded: fine at the copper faces is not applied, uniform).
    @return float Resistance of the cell in K/W (mean top temperature over the heat of the cell).
    """
    a = pitch / math.sqrt(math.pi)                    # equal-area disc
    r_hole, r_bar = phi / 2 - t_pth, phi / 2
    # radial edges: hole, barrel wall, then geometric growth out to the cell wall
    ro = r_bar + (a - r_bar) * (np.geomspace(1.0, 20.0, nr_out + 1) - 1.0) / 19.0
    r_e = np.concatenate([np.linspace(0.0, r_hole, nr_hole + 1), np.linspace(r_hole, r_bar, nr_barrel + 1)[1:], ro[1:]])
    stack = layer_stack()
    z_pts, nz_each = [0.0], []
    for th, cu in stack:                                # from the top down; z measured from the top face
        z_pts.append(z_pts[-1] + th)
        nz_each.append(nz_cu if cu else nz_gap)
    z_e = _edges(z_pts, nz_each)
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
                kr[j, i] = kz[j, i] = k_fill
            elif rc[i] < r_bar:
                kr[j, i] = kz[j, i] = K_CU
            elif is_cu_row[j]:
                kr[j, i] = kz[j, i] = K_CU
            else:
                kr[j, i], kz[j, i] = k_fr4_r, k_fr4_z
    dr, dz = np.diff(r_e), np.diff(z_e)
    n = nr * nz
    idx = np.arange(n).reshape(nz, nr)
    rows, cols, vals = [], [], []
    diag = np.zeros(n)

    def link(p, q, g):
        rows.extend((p, q))
        cols.extend((q, p))
        vals.extend((-g, -g))
        diag[p] += g
        diag[q] += g
    for j in range(nz):
        for i in range(nr):
            p = idx[j, i]
            if i + 1 < nr:                              # radial link, face area 2 pi r_e dz, harmonic mean
                area = 2 * math.pi * r_e[i + 1] * dz[j]
                g = area / (0.5 * dr[i] / kr[j, i] + 0.5 * dr[i + 1] / kr[j, i + 1])
                link(p, idx[j, i + 1], g)
            if j + 1 < nz:                              # vertical link, annulus area
                area = math.pi * (r_e[i + 1] ** 2 - r_e[i] ** 2)
                g = area / (0.5 * dz[j] / kz[j, i] + 0.5 * dz[j + 1] / kz[j + 1, i])
                link(p, idx[j + 1, i], g)
    # bottom face: isothermal (T = 0) through half a cell
    for i in range(nr):
        area = math.pi * (r_e[i + 1] ** 2 - r_e[i] ** 2)
        diag[idx[nz - 1, i]] += area / (0.5 * dz[nz - 1] / kz[nz - 1, i])
    A = sp.coo_matrix((vals, (rows, cols)), shape=(n, n)).tocsr() + sp.diags(diag)
    top_area = math.pi * (r_e[1:] ** 2 - r_e[:-1] ** 2)
    # the flux enters only where there is a solid top (outside the hole): the heat of the package cannot enter the air of the open hole
    load = np.where(rc >= r_hole, top_area, 0.0)
    q_in = np.zeros(n)
    q_in[idx[0, :]] = load / load.sum()                  # unit heat, uniform flux on the solid top
    T = spla.spsolve(A.tocsc(), q_in)
    # top face temperature: the cell value plus the half-cell drop to the face (flux q'' = 1 / load area)
    t_face = T[idx[0, :]] + (1.0 / load.sum()) * 0.5 * dz[0] / kz[0, :]
    return float((t_face * load).sum() / load.sum())


def program_problem(n=N_SIDE, pitch=PHI + SPACING, phi=PHI, with_vias=True, k_fill=K_AIR, power=1.0):
    """!
    @brief The Fig. 17 board as a `pcbthermal` Problem (full copper on four layers, full-board 1 W source on layer 1, bottom film so large that the bottom is the ambient, no top or edge loss).
    @param n Vias per side.
    @param pitch Via pitch in m.
    @param phi Via diameter in m.
    @param with_vias False: the board without vias.
    @param k_fill Filler conductivity in W/mK (the air of an open via, 0.026, as in the paper).
    @param power Power in W.
    @return Problem.
    """
    from pcbthermal import Problem
    from pcbthermal.model import Materials
    side = SIDE * 1e3
    p = Problem.new(side, side, N_CU, T_BOARD * 1e3, T_CU * 1e6, h_top=0.0, h_bottom=1.0e7, h_side=0.0,
                    via_plating=T_PTH, materials=Materials(k_copper=K_CU, k_fr4_through=K_FR4_THROUGH, k_fr4_inplane=K_FR4_INPLANE))
    for layer in range(1, N_CU + 1):
        p.add_zone(layer, rect=(0.0, 0.0, side, side))
    p.add_heater(1, power, rect=(0.0, 0.0, side, side))
    if with_vias:
        c = side / 2
        for i in range(n):
            for j in range(n):
                p.add_via(c + (i - (n - 1) / 2) * pitch * 1e3, c + (j - (n - 1) / 2) * pitch * 1e3, phi * 1e3, fill_k=k_fill)
    return p
