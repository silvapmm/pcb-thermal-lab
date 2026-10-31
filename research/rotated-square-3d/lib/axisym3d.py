#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file axisym3d.py
@brief An independent axisymmetric reference for the real-slab 3D solid: a round two-copper-layer board solved in (r, z) with rings and slabs, with no square grid and no cut cells.
@details A full-copper round board with a round part at its centre is axisymmetric, so the 3D conduction problem of the solid (copper slabs, dielectric
         sub-slabs with their own in-plane and through conductivity, films on both faces, a film on the rim over every slab) reduces to rings in
         the radius times the same slabs through the thickness. The rings are finer than any cell of the program (thousands of them, halved to check),
         and the rim is a plain boundary of the last ring (conduction over half a ring in series with the film). The slab list is read from the
         Problem in the way `pcbthermal.solid3d.Solid` builds it for a full-copper board (copper slab, `n_diel` dielectric slabs per gap, copper
         slab), so that the model solved is the same continuum problem; nothing of the program's grid, cover or edge-length rule is used.
         Checked in tests/test_rotated_square.py against the modified Bessel solution of a thin plate, the series circuit and an energy balance.
"""

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla


def slabs_of(problem, n_diel=4):
    """!
    @brief The slabs (dz, kr, kz) from the top face down of a full-copper board, as the 3D solid builds them.
    @param problem Problem with full copper on every layer (and no vias, blocks or outline needed here).
    @param n_diel Dielectric sub-slabs per gap.
    @return List of tuples (dz in m, in-plane k, through k in W/mK).
    """
    b, m = problem.board, problem.board.materials
    L = b.layers
    tc = np.asarray(b.copper_thickness)
    gaps = b.gap_thicknesses()
    g_kz, g_kip, _ = b.gap_properties()
    out = []
    for l in range(L):
        out.append((float(tc[l]), m.k_copper, m.k_copper))
        if l < L - 1:
            out += [(float(gaps[l]) / n_diel, float(g_kip[l]), float(g_kz[l]))] * n_diel
    return out


def solve_disc(radius, part_radius, power, slabs, h_top, h_bottom, h_side, n_rings=2000):
    """!
    @brief Steady temperature rise of a round laminate with a disc heat source on the top face.
    @param radius Radius of the board in m.
    @param part_radius Radius of the heated disc on the top slab in m.
    @param power Heat in W.
    @param slabs List of (dz, kr, kz) from the top down.
    @param h_top Film coefficient on the top face (everywhere, also under the part, as the program does) in W/m2K.
    @param h_bottom Film coefficient on the bottom face in W/m2K.
    @param h_side Film coefficient on the rim, over every slab, in W/m2K.
    @param n_rings Rings of equal width.
    @return dict with theta (ns, n_rings) rise in K, r (ring centres), t_top_max (rise of the first ring of the top slab), heat_top, heat_bottom, heat_rim (W), residual.
    """
    ns, n = len(slabs), n_rings
    dr = radius / n
    r_in = np.arange(n) * dr
    r_out = r_in + dr
    r_mid = 0.5 * (r_in + r_out)
    ring_area = np.pi * (r_out ** 2 - r_in ** 2)
    idx = np.arange(ns * n).reshape(ns, n)
    rows, cols, vals = [], [], []
    diag = np.zeros(ns * n)

    def couple(a, b_, g):
        rows.append(a.ravel())
        cols.append(b_.ravel())
        vals.append(-g.ravel())
        diag[a.ravel()] += g.ravel()
        diag[b_.ravel()] += g.ravel()

    for s, (dz, kr, kz) in enumerate(slabs):
        # Radial: conductance between ring i and i+1 through the face at r_out[i] (equal rings: the half distances are equal)
        g = 2.0 * np.pi * r_out[:-1] * dz * kr / dr
        couple(idx[s, :-1], idx[s, 1:], g)
        if s < ns - 1:
            dz2, _, kz2 = slabs[s + 1]
            couple(idx[s], idx[s + 1], ring_area / (dz / (2.0 * kz) + dz2 / (2.0 * kz2)))
    # Films on the faces (half-slab conduction in series) and on the rim (half-ring conduction in series)
    g_top = ring_area / (1.0 / h_top + slabs[0][0] / (2.0 * slabs[0][2])) if h_top > 0 else np.zeros(n)
    g_bot = ring_area / (1.0 / h_bottom + slabs[-1][0] / (2.0 * slabs[-1][2])) if h_bottom > 0 else np.zeros(n)
    diag[idx[0]] += g_top
    diag[idx[-1]] += g_bot
    g_rim = np.zeros((ns, n))
    if h_side > 0:
        for s, (dz, kr, kz) in enumerate(slabs):
            area = 2.0 * np.pi * radius * dz
            g_rim[s, -1] = 1.0 / (1.0 / (h_side * area) + (0.5 * dr) / (kr * area))
    diag += g_rim.ravel()
    K = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(ns * n, ns * n)).tocsr()
    K = K + K.T + sp.diags(diag)
    # The heat enters the top slab over the disc of radius part_radius (partial ring by area)
    q = np.zeros((ns, n))
    inside = np.clip((np.minimum(r_out, part_radius) ** 2 - np.minimum(r_in, part_radius) ** 2) * np.pi, 0.0, None)
    q[0] = power * inside / (np.pi * part_radius ** 2)
    theta = spla.spsolve(K.tocsc(), q.ravel())
    res = float(np.linalg.norm(K @ theta - q.ravel()) / np.linalg.norm(q))
    th = theta.reshape(ns, n)
    return {"theta": th, "r": r_mid, "t_top_max": float(th[0, 0]), "heat_top": float((g_top * th[0]).sum()), "heat_bottom": float((g_bot * th[-1]).sum()),
            "heat_rim": float((g_rim * th).sum()), "residual": res}


def solve_layered_disc(problem, radius, part_radius, n_rings=2000):
    """!
    @brief The axisymmetric reduction of the layered model (FVM/FDM idealisation) of a full-copper two-layer round board: one node per layer and ring.
    @details Sheet conductance of a layer = copper + the dielectric share of its slab in parallel (as docs/theory.md defines the layer node), vertical
             conductance per area = through conductivity / gap, films on both faces everywhere, the rim film over the slab thickness of the layer.
    @param problem Problem (two layers, full copper) giving the materials, films and thicknesses.
    @param radius Board radius in m.
    @param part_radius Radius of the heated disc on the top layer in m.
    @param n_rings Rings.
    @return Rise of the first ring of the top layer in K.
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
        diag[base + n_rings - 1] += b.h_side * slab[layer] * 2.0 * np.pi * radius
    idx = np.arange(n_rings)
    rows += list(idx) + list(idx + n_rings)
    cols += list(idx + n_rings) + list(idx)
    vals += list(-g_z * area) * 2
    K = (sp.csr_matrix((vals, (rows, cols)), shape=(n, n)) + sp.diags(diag)).tocsc()
    q = np.zeros(n)
    covered = np.pi * (np.clip(r_out, 0, part_radius) ** 2 - np.clip(r_in, 0, part_radius) ** 2)
    q[:n_rings] = problem.heaters[0].power * covered / (np.pi * part_radius ** 2)
    return float(spla.spsolve(K, q)[0])
