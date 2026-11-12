#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file ref3d_via.py
@brief Independent 3D finite-volume reference of the 10 x 10 mm test board of this folder: copper planes, laminate sub-slabs, the via barrel drawn at its real size, films on both faces
       and on the four sides (imports nothing from the program).
@details Half board (the board, the source and the via are symmetric about y = 5 mm; that plane is adiabatic). Stack from the top: copper (t_cu), then for every gap `n_sub` laminate
         sub-slabs, then copper, ... Each slab has a conductivity array in the plane and through the thickness; where a via disc covers a share f of a cell the cell of every slab of the
         barrel (the gap slabs, and the copper slabs, which are whole copper anyway) is the area mixture f k_fill + (1 - f) k. A copper fill `fill` < 1 is a stripe pattern along y
         (period `pitch` cells, copper cells 'fill * pitch'). Films: `h_top` on the whole top face (also under the source, as the program does), `h_bottom`, `h_side` on x = 0, x = W and
         y = H on every slab, each behind half a cell of the slab. The solve is CG preconditioned by smoothed-aggregation multigrid (pyamg) with a direct solve for small systems.
         The tests check it against a series circuit and an energy balance (tests/test_order_study.py).
"""

import math

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

K_CU = 385.0


def disc_share(cx, cy, r, dx, nx, ny, sub=24):
    """!
    @brief Share of every cell (cell (j, i) of size dx, origin 0) covered by the disc of radius r at (cx, cy).
    @param cx Centre x in m.
    @param cy Centre y in m (the symmetry plane is y = 0 of this frame: the half disc above it is counted).
    @param r Radius in m.
    @param dx Cell size in m.
    @param nx Cells along x.
    @param ny Cells along y.
    @param sub Samples per cell side.
    @return array (ny, nx) of area shares.
    """
    s = (np.arange(sub) + 0.5) / sub
    xs = ((np.arange(nx)[:, None] + s[None, :]) * dx).ravel()
    ys = ((np.arange(ny)[:, None] + s[None, :]) * dx).ravel()
    X, Y = np.meshgrid(xs, ys)
    inside = (np.hypot(X - cx, Y - cy) <= r).reshape(ny, sub, nx, sub)
    return inside.mean(axis=(1, 3))


def solve(dx, width, half_height, layers, t_cu, gaps, n_sub, k_fr4_xy, k_fr4_z, fill, h_top, h_bottom, h_side, source, power, vias, k_via, pitch_cells=8, direct=False):
    """!
    @brief Steady rise of the half board.
    @param dx Cell size in m.
    @param width Board width (x) in m.
    @param half_height Half of the board height in m (y from the symmetry plane to the edge).
    @param layers Copper layers.
    @param t_cu Copper thickness in m.
    @param gaps List of gap thicknesses in m (layers - 1).
    @param n_sub Laminate sub-slabs per gap.
    @param k_fr4_xy FR-4 conductivity in the plane in W/mK.
    @param k_fr4_z FR-4 conductivity through the thickness in W/mK.
    @param fill Copper fill of every layer (1 = whole; below 1: stripes along y).
    @param h_top Top film in W/m2K.
    @param h_bottom Bottom film in W/m2K.
    @param h_side Side film in W/m2K (0 = adiabatic).
    @param source (x0, y0, x1, y1) in m of the part of the source in the half board (y0 = 0 at the symmetry plane).
    @param power Heat in the half source in W.
    @param vias List of (x, y, radius) in m (y measured from the symmetry plane).
    @param k_via Conductivity of the barrel (copper plus fill) in W/mK.
    @param pitch_cells Stripe period in cells for a fill below 1.
    @param direct True: sparse LU, False: CG with multigrid.
    @return dict T_top_max (K), T (array nz ny nx), heat_out (W) and dz (m).
    """
    nx, ny = int(round(width / dx)), int(round(half_height / dx))
    stripes = np.zeros((ny, nx), dtype=bool)
    if fill < 1.0:
        n_cu = max(int(round(fill * pitch_cells)), 1)
        stripes[:] = ((np.arange(ny) % pitch_cells) < n_cu)[:, None]
    share = np.zeros((ny, nx))
    for (x, y, r) in vias:
        share += disc_share(x, y, r, dx, nx, ny)
    share = np.minimum(share, 1.0)
    dz, kxy, kz, is_cu = [], [], [], []
    for lyr in range(layers):
        cu = np.ones((ny, nx), dtype=bool) if fill >= 1.0 else stripes
        kxy.append(np.where(cu, K_CU, k_fr4_xy))
        kz.append(np.where(cu, K_CU, k_fr4_z))
        dz.append(t_cu)
        is_cu.append(True)
        if lyr < layers - 1:
            for _ in range(n_sub):
                dz.append(gaps[lyr] / n_sub)
                kxy.append(np.full((ny, nx), k_fr4_xy))
                kz.append(np.full((ny, nx), k_fr4_z))
                is_cu.append(False)
    nz = len(dz)
    for s in range(nz):                                        # the barrel: area mixture in every slab (it runs through the whole stack)
        if share.any():
            kxy[s] = (1 - share) * kxy[s] + share * k_via
            kz[s] = (1 - share) * kz[s] + share * k_via
    dz = np.array(dz)
    n = nz * ny * nx
    idx = np.arange(n).reshape(nz, ny, nx)
    rows, cols, vals = [], [], []
    diag = np.zeros(n)

    def link(a, b, g):
        g = np.broadcast_to(g, a.shape)
        rows.extend([a.ravel(), b.ravel()])
        cols.extend([b.ravel(), a.ravel()])
        vals.extend([-g.ravel(), -g.ravel()])
        np.add.at(diag, a.ravel(), g.ravel())
        np.add.at(diag, b.ravel(), g.ravel())

    area = dx * dx
    for k in range(nz):                                        # in-plane: harmonic mean of the two half cells
        a, b = kxy[k][:, :-1], kxy[k][:, 1:]
        link(idx[k, :, :-1], idx[k, :, 1:], dz[k] * 2 * a * b / (a + b))
        a, b = kxy[k][:-1, :], kxy[k][1:, :]
        link(idx[k, :-1, :], idx[k, 1:, :], dz[k] * 2 * a * b / (a + b))
    for k in range(nz - 1):                                    # vertical: two half cells in series
        link(idx[k], idx[k + 1], 1.0 / (dz[k] / (2 * kz[k] * area) + dz[k + 1] / (2 * kz[k + 1] * area)))
    g_top = 1.0 / (dz[0] / (2 * kz[0] * area) + 1.0 / (h_top * area)) if h_top > 0 else np.zeros((ny, nx))
    g_bot = 1.0 / (dz[-1] / (2 * kz[-1] * area) + 1.0 / (h_bottom * area))
    diag[idx[0].ravel()] += np.broadcast_to(g_top, (ny, nx)).ravel()
    diag[idx[-1].ravel()] += np.broadcast_to(g_bot, (ny, nx)).ravel()
    g_side = np.zeros((nz, ny, nx))
    if h_side > 0:
        for k in range(nz):
            gx = 1.0 / (dx / (2 * kxy[k] * dz[k] * dx) + 1.0 / (h_side * dz[k] * dx))
            g_side[k, :, 0] += gx[:, 0]
            g_side[k, :, -1] += gx[:, -1]
            g_side[k, -1, :] += gx[-1, :]                       # the far edge y = H (the symmetry plane y = 0 is adiabatic)
    diag += g_side.ravel()
    xs, ys = (np.arange(nx) + 0.5) * dx, (np.arange(ny) + 0.5) * dx
    m = (xs[None, :] > source[0]) & (xs[None, :] < source[2]) & (ys[:, None] > source[1]) & (ys[:, None] < source[3])
    q = np.zeros(n)
    q[idx[0][m]] = power / m.sum()
    K = (sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsr() + sp.diags(diag)).tocsr()
    if direct or n < 60000:
        T = spla.spsolve(K.tocsc(), q)
    else:
        import pyamg
        ml = pyamg.smoothed_aggregation_solver(K, strength="evolution", max_coarse=500)
        T, info = spla.cg(K, q, rtol=1e-12, atol=0.0, M=ml.aspreconditioner(cycle="V"), maxiter=400)
        if info != 0:
            raise RuntimeError(f"CG did not converge ({info})")
    Tt, Tb = T[idx[0].ravel()].reshape(ny, nx), T[idx[-1].ravel()].reshape(ny, nx)
    heat = float((np.broadcast_to(g_top, (ny, nx)) * Tt).sum() + (np.broadcast_to(g_bot, (ny, nx)) * Tb).sum() + (g_side.ravel() * T).sum())
    T = T.reshape(nz, ny, nx)
    return {"T_top_max": float(T[0].max()), "T": T, "heat_out": heat, "dz": dz}


def edge_board_reference(layers=2, fill=1.0, h_side=10.0, distance=1.0, vias="one", fill_k=385.0, dx_mm=1 / 16, n_sub=8, with_via=True, power=0.5, direct=False):
    """!
    @brief The reference of cases.board (10 x 10 mm, source 3 x 2 mm at (1..4, 4..6), via(s) at `distance` from the right edge).
    @param layers 2 or 4.
    @param fill Copper fill of every layer.
    @param h_side Side film in W/m2K.
    @param distance Via distance from the right edge in mm.
    @param vias "one" or "block" (2 x 2 at 0.8 mm pitch).
    @param fill_k Barrel fill conductivity in W/mK (385: the whole disc is copper).
    @param dx_mm Cell in mm (divides 0.1, 0.5 and the source edges).
    @param n_sub Sub-slabs per gap.
    @param with_via False: no via.
    @param power Power in W.
    @param direct Force the sparse LU.
    @return float maximum top rise in K.
    """
    t_cu = 35e-6
    tot = 1.6e-3
    gap = (tot - layers * t_cu) / (layers - 1)
    w = 10e-3
    x = w - distance * 1e-3
    if vias == "one":
        vl = [(x, 0.0, 0.15e-3)]
    else:
        # The four vias at y = 4.6 and 5.4 mm are mirror images about y = 5: the half board holds the two at y = 0.4 mm from the symmetry plane
        vl = [(x, 0.4e-3, 0.15e-3), (x - 0.8e-3, 0.4e-3, 0.15e-3)]
    res = solve(dx_mm * 1e-3, w, 5e-3, layers, t_cu, [gap] * (layers - 1), n_sub, 0.3, 0.3, fill, 10.0, 200.0, float(h_side or 0.0), (1e-3, 0.0, 4e-3, 1e-3), power / 2,
                vl if with_via else [], fill_k if fill_k > 0 else 0.026, direct=direct)
    return res["T_top_max"]
