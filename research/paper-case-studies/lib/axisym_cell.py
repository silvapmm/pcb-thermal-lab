#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file axisym_cell.py
@brief The through-plane effective conductivity of a board with one via per unit cell: the closed form of Soleymani Koohbanani (2016) equations 28 and 29 and an independent axisymmetric
       finite-volume solver of the same unit cell (equal-area disc, barrel, air core, FR-4, optional copper foils). Imports nothing from pcbthermal.
@details Closed form (thesis page 59, equations 28 and 29, read from the page image): the heat crosses the thickness in three parallel paths, FR-4 (area u^2 - pi D_o^2 / 4 for the straight
         cell, v^2 - pi D_o^2 / 2 for the staggered cell that holds two vias), copper (pi/4 (D_o^2 - D_i^2), or pi/2 for two vias) and the air of the core (pi/4 D_i^2, or pi/2), divided by the
         area of the cell. It is exact for isothermal faces and no copper foil, and independent of the thickness.
         The solver: cell-centred axisymmetric finite volumes, radial cells graded towards the barrel, vertical cells uniform in every layer; the cell wall is adiabatic (symmetry); the top and
         the bottom faces are either isothermal ("isothermal": the guarded heat-flux-meter test bed of the thesis, page 17 of its chapter 2) or a uniform flux on the solid top with an
         isothermal bottom ("flux": the only condition the program can impose, a heater over the face). Optional copper foils of thickness t_foil on both faces (the drill goes through them).
         The unit cell of area A is replaced by the disc of the same area (radius a = sqrt(A / pi)); the error of that replacement for a square cell is the reason the unit-cell number is
         compared with the closed form (exact) in the isothermal case, where the field is one-dimensional and the replacement is immaterial.
         Tests: `tests/test_paper_case_studies.py` (closed form against the solver to 1e-9 with isothermal faces and no foil, energy balance, refinement, foil limit).
"""

import math

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

K_CU = 385.0          # W/mK, the value of the thesis (Table 10)
K_FR4 = 0.33          # W/mK, Table 10
K_AIR = 0.026         # W/mK


def k_overall_straight(u, d_o, d_i, k_fr4=K_FR4, k_cu=K_CU, k_air=K_AIR):
    """!
    @brief Equation (28) of the thesis: the through-plane conductivity of a board with a square lattice of vias, side u.
    @param u Side of the straight unit cell (the spacing) in m.
    @param d_o Outer diameter of the copper barrel (the drill) in m.
    @param d_i Inner diameter of the barrel in m.
    @param k_fr4 Conductivity of FR-4 in W/mK.
    @param k_cu Conductivity of copper in W/mK.
    @param k_air Conductivity of the air in the core in W/mK.
    @return float k_overall in W/mK.
    """
    a_fr4 = u * u - math.pi / 4.0 * d_o ** 2
    a_cu = math.pi / 4.0 * (d_o ** 2 - d_i ** 2)
    a_air = math.pi / 4.0 * d_i ** 2
    return (k_fr4 * a_fr4 + k_cu * a_cu + k_air * a_air) / (u * u)


def k_overall_staggered(v, d_o, d_i, k_fr4=K_FR4, k_cu=K_CU, k_air=K_AIR):
    """!
    @brief Equation (29) of the thesis: the staggered cell of side v holds two vias.
    @param v Side of the staggered unit cell in m.
    @param d_o Outer diameter of the copper barrel in m.
    @param d_i Inner diameter of the barrel in m.
    @param k_fr4 Conductivity of FR-4 in W/mK.
    @param k_cu Conductivity of copper in W/mK.
    @param k_air Conductivity of the air in the core in W/mK.
    @return float k_overall in W/mK.
    """
    a_fr4 = v * v - math.pi / 2.0 * d_o ** 2
    a_cu = math.pi / 2.0 * (d_o ** 2 - d_i ** 2)
    a_air = math.pi / 2.0 * d_i ** 2
    return (k_fr4 * a_fr4 + k_cu * a_cu + k_air * a_air) / (v * v)


def _graded_edges(r_in, r_out, n, ratio=12.0):
    """!
    @brief Radial cell edges from r_in to r_out, fine at r_in, coarse at r_out.
    @param r_in Inner radius in m.
    @param r_out Outer radius in m.
    @param n Number of cells.
    @param ratio Ratio of the last to the first cell width.
    @return numpy.ndarray of n + 1 edges.
    """
    w = np.geomspace(1.0, ratio, n)
    return r_in + (r_out - r_in) * np.concatenate([[0.0], np.cumsum(w) / w.sum()])


def unit_cell_k(area, d_o, d_i, t, k_fr4_z=K_FR4, k_fr4_r=None, k_cu=K_CU, k_fill=K_AIR, t_foil=0.0, bc="isothermal", n_rad=60, n_z=40, n_foil=3, n_hole=4):
    """!
    @brief The effective through-plane conductivity of one via unit cell by an axisymmetric finite-volume solve.
    @param area Plan area of the cell per via in m2 (u^2 for the straight lattice, v^2 / 2 for the staggered one).
    @param d_o Outer diameter of the barrel (the drill) in m.
    @param d_i Inner diameter of the barrel in m (d_i = 0 is a solid copper rod).
    @param t Total thickness of the board in m (the foils, when present, are part of it).
    @param k_fr4_z Through-plane conductivity of FR-4 in W/mK.
    @param k_fr4_r In-plane conductivity of FR-4 in W/mK (default: the same as the through value).
    @param k_cu Conductivity of copper in W/mK.
    @param k_fill Conductivity of the core of the via in W/mK.
    @param t_foil Thickness of the copper foil on each face in m (0 = none).
    @param bc "isothermal" (both faces at fixed temperatures) or "flux" (uniform flux over the solid top, bottom isothermal).
    @param n_rad Radial cells outside the barrel.
    @param n_z Vertical cells in the FR-4 core of the board (between the foils).
    @param n_foil Vertical cells in each foil.
    @param n_hole Radial cells in the core of the via.
    @return dict with k_eff (W/mK, defined as Q t / (area dT), dT the difference of the mean face temperatures), q (W of the cell for dT = 1 K in the isothermal case, for 1 W otherwise),
            dT (K between the mean top and mean bottom temperatures), dT_nodes (K between the mean temperatures of the two foils, equal to dT without foil), r_nodes (dT_nodes / q in K/W,
            the resistance a layered model reports between its two copper nodes), balance (relative energy-balance residual).
    @throws ValueError If the geometry is inconsistent or bc is unknown.
    """
    if bc not in ("isothermal", "flux"):
        raise ValueError("bc must be 'isothermal' or 'flux'")
    k_fr4_r = k_fr4_z if k_fr4_r is None else k_fr4_r
    a_cell = math.sqrt(area / math.pi)                # radius of the equal-area disc
    r_o, r_i = d_o / 2.0, d_i / 2.0
    if not (0.0 <= r_i < r_o < a_cell) or 2 * t_foil >= t:
        raise ValueError("need 0 <= d_i < d_o < the cell and 2 foils thinner than the board")
    # radial edges: core (uniform), barrel wall (2 cells), then the FR-4 out to the cell wall (graded, fine at the barrel)
    r_core = np.linspace(0.0, r_i, n_hole + 1)[:-1] if r_i > 0 else np.array([])      # the last edge (r_i) is the first of the wall
    r_wall = np.linspace(r_i, r_o, 3)
    r_out = _graded_edges(r_o, a_cell, n_rad)
    r_e = np.concatenate([r_core, r_wall[:-1], r_out])
    # vertical edges: foil, core, foil (the top is z = 0)
    z_layers = ([(t_foil, n_foil, True)] if t_foil > 0 else []) + [(t - 2 * t_foil, n_z, False)] + ([(t_foil, n_foil, True)] if t_foil > 0 else [])
    z_e, foil_row = [0.0], []
    for th, n, is_foil in z_layers:
        z_e.extend(list(z_e[-1] + np.linspace(0.0, th, n + 1)[1:]))
        foil_row.extend([is_foil] * n)
    z_e, foil_row = np.array(z_e), np.array(foil_row)
    nr, nz = len(r_e) - 1, len(z_e) - 1
    rc, dr, dz = 0.5 * (r_e[1:] + r_e[:-1]), np.diff(r_e), np.diff(z_e)
    # material of every cell: core < r_i, barrel r_i..r_o, then foil rows copper, others FR-4 (anisotropic)
    kr = np.empty((nz, nr))
    kz = np.empty((nz, nr))
    for j in range(nz):
        for i in range(nr):
            if rc[i] < r_i:
                kr[j, i] = kz[j, i] = k_fill
            elif rc[i] < r_o:
                kr[j, i] = kz[j, i] = k_cu
            elif foil_row[j]:
                kr[j, i] = kz[j, i] = k_cu
            else:
                kr[j, i], kz[j, i] = k_fr4_r, k_fr4_z
    idx = np.arange(nz * nr).reshape(nz, nr)
    ring = math.pi * (r_e[1:] ** 2 - r_e[:-1] ** 2)         # plan area of every ring
    # radial links (face area 2 pi r dz) and vertical links (ring area), harmonic means of the two half cells
    g_r = (2 * math.pi * r_e[1:-1][None, :] * dz[:, None]) / (0.5 * dr[None, :-1] / kr[:, :-1] + 0.5 * dr[None, 1:] / kr[:, 1:])
    g_z = ring[None, :] / (0.5 * dz[:-1, None] / kz[:-1, :] + 0.5 * dz[1:, None] / kz[1:, :])
    rows = np.concatenate([idx[:, :-1].ravel(), idx[:-1, :].ravel()])
    cols = np.concatenate([idx[:, 1:].ravel(), idx[1:, :].ravel()])
    g = np.concatenate([g_r.ravel(), g_z.ravel()])
    diag = np.zeros(nz * nr)
    np.add.at(diag, rows, g)
    np.add.at(diag, cols, g)
    # the bottom face is isothermal (T = 0) through half a cell; the top too in the isothermal case (T = 1)
    g_bot = ring / (0.5 * dz[-1] / kz[-1, :])
    diag[idx[-1, :]] += g_bot
    rhs = np.zeros(nz * nr)
    if bc == "isothermal":
        g_top = ring / (0.5 * dz[0] / kz[0, :])
        diag[idx[0, :]] += g_top
        rhs[idx[0, :]] = g_top                       # T_top = 1 K
    else:
        # uniform flux of 1 W over the solid top (the core of an open via carries none: the heat of a heater cannot enter the air of the hole)
        solid = np.where(rc >= r_i, ring, 0.0)
        rhs[idx[0, :]] = solid / solid.sum()
    K = sp.coo_matrix((np.concatenate([-g, -g]), (np.concatenate([rows, cols]), np.concatenate([cols, rows]))), shape=(nz * nr, nz * nr)).tocsr() + sp.diags(diag)
    T = spla.spsolve(K.tocsc(), rhs).reshape(nz, nr)
    q_bot = float((g_bot * T[-1, :]).sum())
    if bc == "isothermal":
        q_top = float((g_top * (1.0 - T[0, :])).sum())
        dT = 1.0
        q = q_bot
        balance = abs(q_top - q_bot) / max(abs(q_bot), 1e-300)
    else:
        # the face temperature is the cell value plus the half-cell drop to the face; the mean over the solid top and over the whole bottom
        solid = np.where(rc >= r_i, ring, 0.0)
        t_top = float(((T[0, :] + (1.0 / solid.sum()) * 0.5 * dz[0] / kz[0, :]) * solid).sum() / solid.sum())
        t_bot = 0.0                                   # isothermal at 0 by construction
        dT = t_top - t_bot
        q = 1.0
        balance = abs(q_bot - 1.0)
    # The temperature of the foil "node" of a layered model is the mean over the foil (its mid-plane for a linear profile); without foil the faces are the nodes
    if t_foil > 0:
        w = ring / ring.sum()
        top_node = float((T[:n_foil, :].mean(axis=0) * w).sum())
        bot_node = float((T[-n_foil:, :].mean(axis=0) * w).sum())
        dT_nodes = top_node - bot_node
    else:
        dT_nodes = dT
    return {"k_eff": q * t / (area * dT), "q": q, "dT": dT, "dT_nodes": dT_nodes, "r_nodes": dT_nodes / q, "balance": balance}
