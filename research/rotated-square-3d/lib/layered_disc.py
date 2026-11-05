#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file layered_disc.py
@brief The axisymmetric reduction of the layered idealisation of a round two-layer board, returning the whole radial field, the rim loss and the mean of the top layer.
@details Same equations as `axisym3d.solve_layered_disc` (which returns only the centre value): one node per layer and ring, sheet conductance
         copper + the dielectric share of the slab, vertical conductance per area through / gap, films on both faces and on the rim (over the slab thickness).
         The rim loss and the whole radial field are what the cut-cell study needs. The cell-centred unknown of the FVM is compared with the field at the
         centre of the hot cell, `dx / sqrt(2)` from the disc centre (`study_cut_cells_fvm.py disc`, README 10.2); `quadrant_mean` (the mean over the cell) is
         not used by the studies; the disc-centre value was the first, wrong, read-out (0.4 % of the rise at 1 mm, README 10.2).
"""

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla


def solve(problem, radius, part_radius, n_rings=4000):
    """!
    @brief Radial field of the two-layer round board.
    @param problem Problem (two layers, full copper, one heater of the given power on the top layer).
    @param radius Board radius in m.
    @param part_radius Radius of the heated disc in m.
    @param n_rings Rings.
    @return dict with r (ring centres, m), top and bottom (rise in K), heat_rim (W, both layers), heat_top, heat_bottom, power (W), mean_top (area mean, K).
    """
    b, m = problem.board, problem.board.materials
    dr = radius / n_rings
    r_in = np.arange(n_rings) * dr
    r_out = r_in + dr
    area = np.pi * (r_out ** 2 - r_in ** 2)
    slab, tcu = b.slab_thicknesses(), np.asarray(b.copper_thickness)
    k_lam = b.layer_laminate()[0]
    sheet = m.k_copper * tcu + k_lam * (slab - tcu)
    g_z = b.gap_properties()[0][0] / b.gap_thicknesses()[0]
    h = [b.h_top, b.h_bottom]
    n = 2 * n_rings
    rows, cols, vals, diag = [], [], [], np.zeros(n)
    g_rim = np.zeros(n)
    for layer in range(2):
        base = layer * n_rings
        g_r = 2.0 * np.pi * r_out[:-1] * sheet[layer] / dr
        i = base + np.arange(n_rings - 1)
        rows += list(i) + list(i + 1)
        cols += list(i + 1) + list(i)
        vals += list(-g_r) * 2
        diag[i] += g_r
        diag[i + 1] += g_r
        diag[base:base + n_rings] += h[layer] * area + g_z * area
        g_rim[base + n_rings - 1] = b.h_side * slab[layer] * 2.0 * np.pi * radius
    diag += g_rim
    idx = np.arange(n_rings)
    rows += list(idx) + list(idx + n_rings)
    cols += list(idx + n_rings) + list(idx)
    vals += list(-g_z * area) * 2
    K = (sp.csr_matrix((vals, (rows, cols)), shape=(n, n)) + sp.diags(diag)).tocsc()
    q = np.zeros(n)
    covered = np.pi * (np.clip(r_out, 0, part_radius) ** 2 - np.clip(r_in, 0, part_radius) ** 2)
    power = problem.heaters[0].power
    q[:n_rings] = power * covered / (np.pi * part_radius ** 2)
    th = spla.spsolve(K, q)
    top, bot = th[:n_rings], th[n_rings:]
    return {"r": 0.5 * (r_in + r_out), "top": top, "bottom": bot, "heat_rim": float((g_rim * th).sum()),
            "heat_top": float((h[0] * area * top).sum()), "heat_bottom": float((h[1] * area * bot).sum()), "power": power,
            "mean_top": float((area * top).sum() / area.sum())}


def quadrant_mean(sol, dx, n=64):
    """!
    @brief Mean of the top-layer rise over the square [0, dx] x [0, dx] with the disc centre at its corner (a cell next to the centre of the board).
    @param sol dict from `solve`.
    @param dx Cell side in m.
    @param n Midpoints per side.
    @return Mean rise in K.
    """
    s = (np.arange(n) + 0.5) * dx / n
    x, y = np.meshgrid(s, s)
    return float(np.interp(np.hypot(x, y).ravel(), sol["r"], sol["top"]).mean())
