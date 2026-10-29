#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file layered3d.py
@brief A small independent 3D finite-volume conduction solver for a laminated block (layers of different conductivity, convection on the two faces, adiabatic sides).
@details Written to repeat the test coupons of the literature (Culham and Yovanovich, Lee) without using any model of the program: a structured grid of nx x ny cells in the
         plane and the given slabs through the thickness, conductivity uniform in a slab (isotropic), harmonic mean of the half-cell resistances between neighbours, heat flux
         applied to a rectangle of the top face, convection (a film coefficient) on the rest of the top face and on the bottom face, the four sides insulated.
         Temperatures are rises over the ambient.
@note This is a copy of research/effective-conductivity/lib/layered3d.py (the investigation that wrote and tested it against a series circuit, two energy balances,
      a uniform layer and three published results; that folder is `research/effective-conductivity/`), kept here as the independent
      reference of tests/test_layered_vs_3d.py. The same code is in research/solid3d-verification/lib/layered3d.py. It imports nothing from pcbthermal.
"""

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla


def solve(dx, nx, ny, slabs, source, power, h_top, h_bottom, film_under_source=False):
    """!
    @brief Solve the steady temperature rise of a laminated block with a flux on a rectangle of the top face.
    @param dx Cell size in the plane in m (square cells).
    @param nx Cells along x.
    @param ny Cells along y.
    @param slabs List of (thickness in m, conductivity in W/mK, number of sub-slabs) from the top down; the conductivity is a number or an array (ny, nx)
                 of the conductivity of every cell of the slab (isotropic in each cell, a patterned copper layer for example).
    @param source Tuple (x0, y0, x1, y1) of the heated rectangle on the top face in m, measured from the corner; its edges must lie on cell edges (checked). A list of such tuples is accepted too (several sources).
    @param power Heat flowing into the source rectangle in W (a list with one value per rectangle when `source` is a list).
    @param h_top Film coefficient on the top face outside the source in W/m2K (0 = insulated).
    @param h_bottom Film coefficient on the bottom face in W/m2K.
    @param film_under_source True: the film coefficient also acts on the top face under the source (as the program does); False: the source area is insulated (as in the papers).
    @return dict with T (array nz x ny x nx, rise in K), dz (list), area_source, mask_source (ny x nx bool), mean_source, max_source (surface temperatures of the heated cells),
            cell_mean_source, cell_max_source (cell centres), per_source, surface_top, heat_out, wall_top, wall_bottom, top_surface_mean, mean_wall.
    @throws ValueError If a source edge does not lie on a cell edge or a source covers no cell.
    """
    dz, kz = [], []
    for t, k, n in slabs:
        dz += [t / n] * n
        kz += [np.broadcast_to(np.asarray(k, dtype=float), (ny, nx))] * n
    dz, kz = np.array(dz), np.array(kz)                          # kz: (nz, ny, nx), the conductivity of every cell
    nz = len(dz)
    xs = (np.arange(nx) + 0.5) * dx
    ys = (np.arange(ny) + 0.5) * dx
    multi = isinstance(source[0], (tuple, list))
    rects = list(source) if multi else [source]
    powers = list(power) if multi else [power]
    for r in rects:                                              # an edge between cell edges would silently change the heated area
        e = np.asarray(r, dtype=float) / dx
        if np.abs(e - np.round(e)).max() > 1e-6:
            raise ValueError(f"source {tuple(r)} has an edge between cell edges (cell {dx} m)")
    masks = [(xs[None, :] > r[0]) & (xs[None, :] < r[2]) & (ys[:, None] > r[1]) & (ys[:, None] < r[3]) for r in rects]
    mask = np.logical_or.reduce(masks)
    if not all(m.any() for m in masks):
        raise ValueError("a source rectangle covers no cell")
    area = dx * dx
    n = nz * ny * nx
    idx = np.arange(n).reshape(nz, ny, nx)
    rows, cols, vals = [], [], []
    diag = np.zeros(n)

    def link(a, b, g):
        """!
        @brief Add the conductance g between the node arrays a and b (symmetric).
        @param a Node indices.
        @param b Node indices.
        @param g Conductance (scalar or array) in W/K.
        @return None.
        """
        g = np.broadcast_to(g, a.shape)
        rows.extend([a.ravel(), b.ravel()]); cols.extend([b.ravel(), a.ravel()]); vals.extend([-g.ravel(), -g.ravel()])
        np.add.at(diag, a.ravel(), g.ravel()); np.add.at(diag, b.ravel(), g.ravel())

    for k in range(nz):                                          # in-plane links of every slab: harmonic mean of the two half cells, times dz dy / dx (dy = dx)
        a, b = kz[k][:, :-1], kz[k][:, 1:]
        link(idx[k, :, :-1], idx[k, :, 1:], dz[k] * 2.0 * a * b / (a + b))
        a, b = kz[k][:-1, :], kz[k][1:, :]
        link(idx[k, :-1, :], idx[k, 1:, :], dz[k] * 2.0 * a * b / (a + b))
    for k in range(nz - 1):                                      # vertical links: half-cell resistances in series
        r = dz[k] / (2 * kz[k] * area) + dz[k + 1] / (2 * kz[k + 1] * area)
        link(idx[k], idx[k + 1], 1.0 / r)
    q = np.zeros(n)
    top, bot = idx[0], idx[-1]
    rh_top = dz[0] / (2 * kz[0] * area)                          # half-cell resistances between the outer cell centres and their faces (K/W)
    rh_bot = dz[-1] / (2 * kz[-1] * area)
    free_top = np.ones_like(mask) if film_under_source else ~mask
    g_film = np.where(free_top, max(h_top, 0.0) * area, 0.0)     # film conductance of every top-face cell (W/K)
    gb = np.zeros((ny, nx)) if h_bottom <= 0 else 1.0 / (rh_bot + 1.0 / (h_bottom * area))
    qcell = np.zeros(mask.shape)
    for m, pw in zip(masks, powers):
        qcell[m] += pw / m.sum()                                 # the power of each source spread uniformly over its cells
    # The top face of a cell is a node eliminated from the system: Ts = (q + T/rh) / (1/rh + g_film). The centre then sees the film through
    # rh + 1/g_film and receives q / (1 + g_film rh); the rest of q leaves through the film directly (it matters only where a film acts under a source).
    np.add.at(diag, top.ravel(), (g_film / (1.0 + g_film * rh_top)).ravel())
    np.add.at(diag, bot.ravel(), gb.ravel())
    q[top.ravel()] = (qcell / (1.0 + g_film * rh_top)).ravel()
    K = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsr() + sp.diags(diag)
    T = spla.spsolve(K.tocsc(), q).reshape(nz, ny, nx)
    surface = (qcell + T[0] / rh_top) / (1.0 / rh_top + g_film)  # top-face temperature of every cell (heated, convecting, both or neither)
    t_src = surface[mask]
    walls = []
    wall_top = np.array([])
    wall_bottom = np.array([])
    heat_out = float((g_film * surface).sum())                   # heat leaving through the films, for the energy balance
    if h_top > 0:
        wall_top = surface[free_top]
        walls.append(wall_top)
    if h_bottom > 0:
        wall_bottom = (T[-1] * (1.0 / (h_bottom * area)) / (rh_bot + 1.0 / (h_bottom * area))).ravel()
        walls.append(wall_bottom)
        heat_out += float((h_bottom * area * wall_bottom).sum())
    return {"T": T, "dz": list(dz), "area_source": mask.sum() * area, "mask_source": mask, "mean_source": float(t_src.mean()),
            "max_source": float(t_src.max()), "cell_mean_source": float(T[0][mask].mean()), "cell_max_source": float(T[0][mask].max()), "per_source": [{"mean": float(surface[m].mean()), "cell_mean": float(T[0][m].mean())} for m in masks], "surface_top": surface, "heat_out": heat_out, "wall_top": wall_top, "wall_bottom": wall_bottom, "top_surface_mean": float(surface.mean()), "mean_wall": float(np.concatenate(walls).mean()) if walls else 0.0}


def solid_resistance(res, power):
    """!
    @brief Solid-body resistance of Culham and Yovanovich: (mean source temperature - mean wall temperature) / power.
    @param res Result of solve().
    @param power Heat in W.
    @return float Resistance in K/W.
    """
    return (res["mean_source"] - res["mean_wall"]) / power


def effective_conductivity(dx, nx, ny, total_thickness, source, power, h_top, h_bottom, target, n_sub=8, lo=0.05, hi=2000.0):
    """!
    @brief Conductivity of a single-layer block of the same thickness and boundary conditions that has the same solid-body resistance (the definition of the paper).
    @param dx Cell size in m.
    @param nx Cells along x.
    @param ny Cells along y.
    @param total_thickness Thickness of the block in m.
    @param source Source rectangle (see solve()).
    @param power Heat in W.
    @param h_top Film coefficient on the top face in W/m2K.
    @param h_bottom Film coefficient on the bottom face in W/m2K.
    @param target Solid-body resistance of the laminate in K/W.
    @param n_sub Sub-slabs through the single layer.
    @param lo Lower bracket of the conductivity in W/mK.
    @param hi Upper bracket of the conductivity in W/mK.
    @return float Effective conductivity in W/mK (bisection on the logarithm of k; the resistance falls as k grows).
    """
    a, b = np.log(lo), np.log(hi)
    for _ in range(40):
        m = 0.5 * (a + b)
        r = solid_resistance(solve(dx, nx, ny, [(total_thickness, float(np.exp(m)), n_sub)], source, power, h_top, h_bottom), power)
        if r > target:
            a = m                                                # too resistive: a larger conductivity is needed
        else:
            b = m
    return float(np.exp(0.5 * (a + b)))
