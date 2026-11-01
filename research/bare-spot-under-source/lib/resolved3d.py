#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file resolved3d.py
@brief Independent resolved 3D finite-volume solver of a laminated board with patterned copper, orthotropic laminate, films on both faces (imports nothing from pcbthermal).
@details The reference of the bare-spot investigation. A structured grid of nx x ny cells in the plane (square, size dx) and a list of slabs through the thickness, each cut
         into sub-slabs; every slab has an in-plane conductivity kxy and a through conductivity kz that may be arrays (ny, nx) (a copper layer with a window is copper where the
         mask is true and laminate elsewhere). The conductance between two neighbours is the series of the half-cell resistances (harmonic mean). Films act on the whole top and bottom faces
         through the half top (bottom) cell, as the program applies them (also under the source); the sides are insulated, so a symmetric board can be solved on a quadrant.
         The source is a flux on the top face of a rectangle. The surface temperature of a source cell is corrected from the cell centre to the face by the half-cell drop.
         Temperatures are rises over the ambient. Checked in tests/test_resolved3d.py against a series circuit, the energy balance, a uniform column and the closed-form series of
         Muzychka, Culham and Yovanovich (2003) for a rectangular source on a plate (lib/closed_forms.py).
"""

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla


def build_slabs(layers, copper_mask, k_cu, gaps, t_cu, nsub, kxy_lam, kz_lam):
    """!
    @brief Slab list of a board: copper layers (patterned by a mask) separated by dielectric gaps cut into sub-slabs.
    @param layers Number of copper layers.
    @param copper_mask List (one per layer) of boolean arrays (ny, nx) or fractions in [0, 1], True/1 = copper; None = full copper.
    @param k_cu Copper conductivity in W/mK (isotropic).
    @param gaps List of layers-1 gap thicknesses in m.
    @param t_cu List of copper thicknesses in m (one per layer).
    @param nsub Sub-slabs per gap (a single int or one per gap).
    @param kxy_lam In-plane conductivity of the laminate in W/mK (a scalar or one per gap).
    @param kz_lam Through conductivity of the laminate in W/mK (a scalar or one per gap).
    @return List of (thickness, kxy, kz, n) tuples from the top down, for solve().
    @note Where a copper layer has no copper its thickness is laminate of the adjacent gap above (the top layer: the gap below), isotropic as the gap.
    """
    nsub = [nsub] * (layers - 1) if np.isscalar(nsub) else list(nsub)
    kxy_lam = [kxy_lam] * (layers - 1) if np.isscalar(kxy_lam) else list(kxy_lam)
    kz_lam = [kz_lam] * (layers - 1) if np.isscalar(kz_lam) else list(kz_lam)
    out = []
    for l in range(layers):
        g = max(l - 1, 0) if layers > 1 else 0
        m = None if copper_mask is None else copper_mask[l]
        if m is None:
            kxy, kz = k_cu, k_cu
        else:
            f = np.asarray(m, dtype=float)
            # A fraction mixes the conductivities arithmetically (exact for a binary mask)
            kxy = kxy_lam[g] + f * (k_cu - kxy_lam[g]) if layers > 1 else k_cu * f
            kz = kz_lam[g] + f * (k_cu - kz_lam[g]) if layers > 1 else k_cu * f
        out.append((t_cu[l], kxy, kz, 1))
        if l < layers - 1:
            out.append((gaps[l], kxy_lam[l], kz_lam[l], nsub[l]))
    return out


def solve(dx, nx, ny, slabs, source, power, h_top, h_bottom):
    """!
    @brief Steady temperature rise of the board.
    @param dx Cell size in the plane in m.
    @param nx Cells along x.
    @param ny Cells along y.
    @param slabs List of (thickness m, kxy, kz, n sub-slabs) from the top down; kxy and kz scalars or arrays (ny, nx).
    @param source Rectangle (x0, y0, x1, y1) in m on the top face, edges on cell edges.
    @param power Heat in W flowing into the rectangle.
    @param h_top Film coefficient of the top face in W/m2K (acts on the whole face, also under the source).
    @param h_bottom Film coefficient of the bottom face in W/m2K.
    @return dict with T (nz, ny, nx), dz (nz,), mask (ny, nx) of the source cells, surf (ny, nx) rises of the top face, max, mean (over the source cells, surface), heat_out (W),
            balance (heat_out / power), z (cell centres, m).
    @throws ValueError If a source edge is not on a cell edge or the source covers no cell.
    """
    dz, kxy, kz = [], [], []
    for t, a, c, n in slabs:
        dz += [t / n] * n
        kxy += [np.broadcast_to(np.asarray(a, dtype=float), (ny, nx))] * n
        kz += [np.broadcast_to(np.asarray(c, dtype=float), (ny, nx))] * n
    dz, kxy, kz = np.array(dz), np.array(kxy), np.array(kz)
    nz = len(dz)
    e = np.asarray(source, dtype=float) / dx
    if np.abs(e - np.round(e)).max() > 1e-6:
        raise ValueError("source edge between cell edges")
    xs, ys = (np.arange(nx) + 0.5) * dx, (np.arange(ny) + 0.5) * dx
    mask = (xs[None, :] > source[0]) & (xs[None, :] < source[2]) & (ys[:, None] > source[1]) & (ys[:, None] < source[3])
    if not mask.any():
        raise ValueError("the source covers no cell")
    n = nz * ny * nx
    idx = np.arange(n).reshape(nz, ny, nx)
    rows, cols, vals = [], [], []
    diag = np.zeros(n)

    def link(a, b, g):
        a, b, g = a.ravel(), b.ravel(), g.ravel()
        rows.extend([a, b])
        cols.extend([b, a])
        vals.extend([-g, -g])
        np.add.at(diag, a, g)
        np.add.at(diag, b, g)

    dzv = dz[:, None, None]
    # In-plane links: series of two half-cells, k dz dy / (dx/2) each
    ga = kxy * dzv * dx / (dx / 2)
    link(idx[:, :, :-1], idx[:, :, 1:], ga[:, :, :-1] * ga[:, :, 1:] / (ga[:, :, :-1] + ga[:, :, 1:]))
    link(idx[:, :-1, :], idx[:, 1:, :], ga[:, :-1, :] * ga[:, 1:, :] / (ga[:, :-1, :] + ga[:, 1:, :]))
    # Through links: series of two half-cells
    A = dx * dx
    gz = kz * A / (dzv / 2)
    link(idx[:-1], idx[1:], gz[:-1] * gz[1:] / (gz[:-1] + gz[1:]))
    # Films through the half outer cell
    gt = 1.0 / (1.0 / (h_top * A) + 1.0 / gz[0]) if h_top > 0 else np.zeros((ny, nx))
    gb = 1.0 / (1.0 / (h_bottom * A) + 1.0 / gz[-1]) if h_bottom > 0 else np.zeros((ny, nx))
    diag[idx[0].ravel()] += gt.ravel()
    diag[idx[-1].ravel()] += gb.ravel()
    q = np.zeros(n)
    q[idx[0][mask]] = power / mask.sum()
    K = sp.csc_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)) + sp.diags(diag)
    T = spla.spsolve(K.tocsc(), q).reshape(nz, ny, nx)
    # Top face temperature: T_s (1 + h dz/(2 kz)) = T_cell + Q dz/(2 kz A)
    qin = np.zeros((ny, nx))
    qin[mask] = power / mask.sum()
    hz = h_top * dz[0] / (2 * kz[0])
    surf = (T[0] + qin * dz[0] / (2 * kz[0] * A)) / (1 + hz)
    out = float((gt * T[0]).sum() + (gb * T[-1]).sum())
    return {"T": T, "dz": dz, "mask": mask, "surf": surf, "max": float(surf[mask].max()), "mean": float(surf[mask].mean()),
            "heat_out": out, "balance": out / power, "z": np.cumsum(dz) - dz / 2}


def window_masks(nx, ny, dx, layers, window, window_layers=(0,)):
    """!
    @brief Copper masks of a board whose copper has a rectangular window (no copper) in some layers.
    @param nx Cells along x.
    @param ny Cells along y.
    @param dx Cell size in m.
    @param layers Number of copper layers.
    @param window Rectangle (x0, y0, x1, y1) in m of the copper-free window (None: no window).
    @param window_layers 0-based layers that have the window.
    @return list of boolean arrays (ny, nx), True = copper.
    """
    xs, ys = (np.arange(nx) + 0.5) * dx, (np.arange(ny) + 0.5) * dx
    out = []
    for l in range(layers):
        m = np.ones((ny, nx), dtype=bool)
        if window is not None and l in window_layers:
            m &= ~((xs[None, :] > window[0]) & (xs[None, :] < window[2]) & (ys[:, None] > window[1]) & (ys[:, None] < window[3]))
        out.append(m)
    return out
