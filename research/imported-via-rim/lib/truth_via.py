#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file truth_via.py
@brief Independent 3D reference of a small board with a via field through copper planes that have an antipad, a thermal relief or a solid connection (imports nothing from pcbthermal).
@details Cartesian cell-centred finite volumes, anisotropic laminate (0.9 W/mK in the plane, 0.3 through it), copper 385 W/mK, copper layers as real slabs (35 um) and the laminate between
         them cut into `nlam` sub-slabs per gap, so nothing of the program's one-node-per-layer idealisation is used. Every via is a square block of cells (3 x 3 cells of 0.1 mm for a
         0.3 mm drill) whose through conductivity is the copper of the hollow barrel spread over the block (kz = 385 A_barrel / A_block, 0.9 in the plane); on a copper layer the plane is
         385 W/mK everywhere except where the layer pattern is bare. Layer patterns around a via: 'solid' (plane over the whole block), 'anti' (a copper pad island of radius `pad_r`
         around the via, bare laminate out to `anti_r`, the plane beyond: the antipad of a signal via; the pad touches the barrel but not the plane), 'relief' (as 'anti' with
         four copper spokes of width `spoke_w` joining the pad to the plane). The board is square, the sides are insulated, the top and bottom faces have films (also under the heater),
         the heater is a square of the top face over the top copper. Returns the mean and the maximum rise of the heater cells, the heat balance and the rim data used by the program run.
@note Written for this investigation; own tests (`tests/test_truth_via.py`): a one-via-free board equals a series circuit, the energy balance closes.
"""

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

K_CU, K_XY, K_Z = 385.0, 0.9, 0.3


def layer_pattern(n, d, centres, kind, pad_r, anti_r, spoke_w):
    """!
    @brief Copper mask of one layer.
    @param n Cells per side.
    @param d Cell in m.
    @param centres List of (x, y) via centres in m.
    @param kind 'solid', 'anti' or 'relief'.
    @param pad_r Radius of the pad island in m.
    @param anti_r Radius of the clearance in m.
    @param spoke_w Width of a spoke in m.
    @return bool array (n, n): True where the cell is copper.
    """
    c = (np.arange(n) + 0.5) * d
    X, Y = np.meshgrid(c, c)
    m = np.ones((n, n), bool)
    if kind == "solid":
        return m
    for (cx, cy) in centres:
        r = np.hypot(X - cx, Y - cy)
        ring = (r > pad_r) & (r <= anti_r)
        if kind == "relief":
            spoke = (np.abs(X - cx) <= spoke_w / 2) | (np.abs(Y - cy) <= spoke_w / 2)
            ring &= ~spoke
        m &= ~ring
    return m


def solve(kinds, centres, heater, cell_mm=0.1, nlam=6, width_mm=10.0, drill=0.3e-3, plating=25e-6, pad_r=0.25e-3, anti_r=0.55e-3, spoke_w=0.25e-3, h_top=10.0, h_bottom=10.0,
          power=1.0, board_t=1.6e-3, t_cu=35e-6, with_vias=True):
    """!
    @brief Steady rise of the board.
    @param kinds List of the pattern of every copper layer, top first ('solid', 'anti' or 'relief').
    @param centres List of via centres (x, y) in m (cell centres).
    @param heater (x0, y0, x1, y1) in m, edges on cell edges.
    @param cell_mm Cell in the plane in mm.
    @param nlam Laminate sub-slabs per gap.
    @param width_mm Board side in mm.
    @param drill Drill diameter in m.
    @param plating Barrel plating in m.
    @param pad_r Pad radius in m.
    @param anti_r Antipad radius in m.
    @param spoke_w Spoke width in m.
    @param h_top Top film W/m2K.
    @param h_bottom Bottom film W/m2K.
    @param power Heater power W.
    @param board_t Board thickness m.
    @param t_cu Copper thickness m.
    @param with_vias False: the same board without any via (bare laminate pattern kept).
    @return dict with 'mean', 'max' (heater rise K), 'balance' (relative heat balance error), 'nz'.
    """
    d = cell_mm * 1e-3
    n = int(round(width_mm / cell_mm))
    L = len(kinds)
    gap = (board_t - L * t_cu) / (L - 1)
    dz, kxy_l, kz_l = [], [], []
    # via blocks: the cells within half a drill (square block) of a centre
    c = (np.arange(n) + 0.5) * d
    X, Y = np.meshgrid(c, c)
    block = np.zeros((n, n), bool)
    for (cx, cy) in centres:
        block |= (np.abs(X - cx) <= drill / 2 + 1e-12) & (np.abs(Y - cy) <= drill / 2 + 1e-12)
    r_in = drill / 2 - plating
    a_barrel = np.pi * (drill ** 2 / 4 - r_in ** 2)
    kz_block = K_CU * a_barrel / (block.sum() / max(len(centres), 1) * d * d)
    for li in range(L):
        mk = layer_pattern(n, d, centres, kinds[li], pad_r, anti_r, spoke_w)
        # the block cells keep the copper of the pattern; where the layer is bare there the barrel passes through (kz_block, laminate in the plane)
        kxy = np.where(mk, K_CU, K_XY)
        kz = np.where(mk, K_CU, K_Z)
        if with_vias:
            kz = np.where(block & ~mk, kz_block, kz)
        dz.append(t_cu)
        kxy_l.append(kxy)
        kz_l.append(kz)
        if li < L - 1:
            for _ in range(nlam):
                dz.append(gap / nlam)
                kxy_l.append(np.full((n, n), K_XY))
                kz_l.append(np.where(block, kz_block, K_Z) if with_vias else np.full((n, n), K_Z))
    nz = len(dz)
    kxy, kz = np.array(kxy_l), np.array(kz_l)
    N = n * n
    idx = np.arange(nz * N).reshape(nz, n, n)
    rows, cols, vals = [], [], []
    diag = np.zeros(nz * N)

    def link(a, b, g):
        """!
        @brief Symmetric link of conductance g between two node arrays.
        @param a Node indices.
        @param b Node indices.
        @param g Conductance (array).
        @return None.
        """
        a, b, g = a.ravel(), b.ravel(), np.broadcast_to(g, a.shape).ravel()
        rows.extend([a, b])
        cols.extend([b, a])
        vals.extend([-g, -g])
        np.add.at(diag, a, g)
        np.add.at(diag, b, g)

    for k in range(nz):
        a, b = kxy[k][:, :-1], kxy[k][:, 1:]
        link(idx[k, :, :-1], idx[k, :, 1:], dz[k] * 2 * a * b / (a + b))
        a, b = kxy[k][:-1, :], kxy[k][1:, :]
        link(idx[k, :-1, :], idx[k, 1:, :], dz[k] * 2 * a * b / (a + b))
    for k in range(nz - 1):
        r = dz[k] / (2 * kz[k] * d * d) + dz[k + 1] / (2 * kz[k + 1] * d * d)
        link(idx[k], idx[k + 1], 1.0 / r)
    gt = 1.0 / (dz[0] / (2 * kz[0] * d * d) + 1.0 / (h_top * d * d))
    gb = 1.0 / (dz[-1] / (2 * kz[-1] * d * d) + 1.0 / (h_bottom * d * d))
    np.add.at(diag, idx[0].ravel(), gt.ravel())
    np.add.at(diag, idx[-1].ravel(), gb.ravel())
    x0, y0, x1, y1 = heater
    hm = (X > x0) & (X < x1) & (Y > y0) & (Y < y1)
    q = np.zeros(nz * N)
    q[idx[0].ravel()] = (power * hm / hm.sum()).ravel()
    K = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(nz * N, nz * N)).tocsr() + sp.diags(diag)
    T = spla.spsolve(K.tocsc(), q).reshape(nz, n, n)
    out = (gt * T[0]).sum() + (gb * T[-1]).sum()
    return {"mean": float(T[0][hm].mean()), "max": float(T[0].max()), "balance": float(out / power - 1.0), "nz": nz}
