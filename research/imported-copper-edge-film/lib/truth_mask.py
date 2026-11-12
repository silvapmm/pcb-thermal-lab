#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file truth_mask.py
@brief Independent 3D reference for boards of any axis-aligned outline (T, L, square, with any copper polygons, any number of layers): the full board resolved through the thickness (imports nothing from pcbthermal).
@details The physics of `truth3d.py` (cell-centred finite volumes, laminate 0.9 W/mK in the plane and 0.3 through it, copper 385 W/mK and 35 um, laminate between the copper layers cut
         into `nz_lam` sub-slabs, films h_top and h_bottom on the faces, the film h_side in series with the half-cell conduction on the wall) on the whole board instead of a quarter:
         a cell belongs to the board when its centre is inside the outline polygon, a copper layer is the cells whose centre is inside its polygon (None: every cell of the board),
         and a link between a board cell and a cell outside it (or the edge of the grid) is the wall. The outline and the copper edges must lie on cell faces (multiples of the cell).
         `truth` extrapolates three solves as `study_truth.py` does: (2c, nz/2), (c, nz/2), (c, nz) with c = 0.2 mm.
"""

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from matplotlib.path import Path

K_CU, T_CU, K_XY, K_Z = 385.0, 35e-6, 0.9, 0.3


def solve(outline, coppers, heater, h_side, cell_mm, nz_lam, h_top=10.0, h_bottom=10.0, power=1.0, board_t=1.6e-3):
    """!
    @brief Steady rise of the whole board.
    @param outline Outline vertices (n, 2) in mm, board frame with the lower left of the bounding box at the origin.
    @param coppers List (one per copper layer, top first) of polygons (mm) or None for copper on the whole board.
    @param heater Heater rectangle (x0, y0, x1, y1) in mm on the top layer.
    @param h_side Edge film on the whole wall, W/m2K.
    @param cell_mm Cell in the plane, mm (must divide the coordinates of the outline, the copper and the heater).
    @param nz_lam Sub-slabs of the laminate in every gap.
    @param h_top Top film, W/m2K.
    @param h_bottom Bottom film, W/m2K.
    @param power Heater power, W.
    @param board_t Board thickness, m.
    @return Tuple (mean rise of the heater K, hottest rise K, heat balance error).
    """
    d = cell_mm * 1e-3
    o = np.asarray(outline, float)
    nx, ny = int(round(o[:, 0].max() / cell_mm)), int(round(o[:, 1].max() / cell_mm))
    cx = (np.arange(nx) + 0.5) * cell_mm
    cy = (np.arange(ny) + 0.5) * cell_mm
    X, Y = np.meshgrid(cx, cy)
    pts = np.column_stack([X.ravel(), Y.ravel()])
    act = Path(o).contains_points(pts).reshape(ny, nx)
    layers = len(coppers)
    gap = (board_t - layers * T_CU) / (layers - 1)
    dz, kxy_l, kz_l = [], [], []
    for li, poly in enumerate(coppers):
        if poly is None:
            m = act
        else:
            parts = poly if np.ndim(poly[0][0]) == 1 else [poly]               # one polygon or a list of them (stripes)
            m = np.zeros(ny * nx, bool)
            for q in parts:
                m |= Path(np.asarray(q, float)).contains_points(pts)
            m = m.reshape(ny, nx) & act
        dz.append(T_CU)
        kxy_l.append(np.where(m, K_CU, K_XY))
        kz_l.append(np.where(m, K_CU, K_Z))
        if li < layers - 1:
            for _ in range(nz_lam):
                dz.append(gap / nz_lam)
                kxy_l.append(np.full((ny, nx), K_XY))
                kz_l.append(np.full((ny, nx), K_Z))
    nz = len(dz)
    kxy, kz = np.array(kxy_l), np.array(kz_l)
    N = nx * ny
    idx = np.arange(nz * N).reshape(nz, ny, nx)
    rows, cols, vals = [], [], []
    diag = np.zeros(nz * N)

    def link(a, b, g):
        """!
        @brief Symmetric link between node arrays.
        @param a Node indices.
        @param b Node indices.
        @param g Conductance W/K.
        @return None.
        """
        a, b, g = a.ravel(), b.ravel(), np.broadcast_to(g, a.shape).ravel()
        rows.extend([a, b])
        cols.extend([b, a])
        vals.extend([-g, -g])
        np.add.at(diag, a, g)
        np.add.at(diag, b, g)

    wall_nodes = []                                                        # (node indices, conductance) of the wall links
    ap = np.pad(act, 1)
    for k in range(nz):
        a = kxy[k]
        both_x = act[:, :-1] & act[:, 1:]
        both_y = act[:-1, :] & act[1:, :]
        gx = dz[k] * 2 * a[:, :-1] * a[:, 1:] / (a[:, :-1] + a[:, 1:])
        gy = dz[k] * 2 * a[:-1, :] * a[1:, :] / (a[:-1, :] + a[1:, :])
        link(idx[k, :, :-1][both_x], idx[k, :, 1:][both_x], gx[both_x])
        link(idx[k, :-1, :][both_y], idx[k, 1:, :][both_y], gy[both_y])
        # wall: the four neighbours of every board cell; film in series with the half-cell conduction over the face dz x d
        gw = 1.0 / (1.0 / (h_side * dz[k] * d) + (d / 2) / (a * dz[k] * d))
        for nb in (ap[1:-1, :-2], ap[1:-1, 2:], ap[:-2, 1:-1], ap[2:, 1:-1]):
            sel = act & ~nb
            np.add.at(diag, idx[k][sel], gw[sel])
            wall_nodes.append((idx[k][sel], gw[sel]))
    for k in range(nz - 1):
        r = dz[k] / (2 * kz[k] * d * d) + dz[k + 1] / (2 * kz[k + 1] * d * d)
        link(idx[k][act], idx[k + 1][act], (1.0 / r)[act])
    gt = 1.0 / (dz[0] / (2 * kz[0] * d * d) + 1.0 / (h_top * d * d))
    gb = 1.0 / (dz[-1] / (2 * kz[-1] * d * d) + 1.0 / (h_bottom * d * d))
    np.add.at(diag, idx[0][act], gt[act])
    np.add.at(diag, idx[-1][act], gb[act])
    off = np.repeat(~act[None], nz, 0)                                     # nodes outside the board: identity rows, no source
    diag[idx[off]] = 1.0
    x0, y0, x1, y1 = heater
    hm = (X > x0) & (X < x1) & (Y > y0) & (Y < y1) & act
    q = np.zeros(nz * N)
    q[idx[0][hm]] = power / hm.sum()
    K = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(nz * N, nz * N)).tocsr() + sp.diags(diag)
    T = spla.spsolve(K.tocsc(), q).reshape(nz, ny, nx)
    out = (gt * T[0])[act].sum() + (gb * T[-1])[act].sum()
    for nodes, g in wall_nodes:
        out += (g * T.ravel()[nodes]).sum()
    return float(T[0][hm].mean()), float(T[0][act].max()), float(out / power - 1.0)


def truth(outline, coppers, heater, h_side, nz=12, c=0.2, **kw):
    """!
    @brief Extrapolated truth of the mean heater rise (three solves: (2c, nz/2), (c, nz/2), (c, nz); the series of `study_truth.py`).
    @param outline Outline in mm.
    @param coppers Copper polygons per layer.
    @param heater Heater rectangle in mm.
    @param h_side Edge coefficient W/m2K.
    @param nz Sub-slabs per gap at the finest solve.
    @param c Cell of the finest solves in mm.
    @param kw Other arguments of `solve`.
    @return Dict with the truth, the three solves and the balance error.
    """
    a = solve(outline, coppers, heater, h_side, 2 * c, nz // 2, **kw)
    b = solve(outline, coppers, heater, h_side, c, nz // 2, **kw)
    f = solve(outline, coppers, heater, h_side, c, nz, **kw)
    est = f[0] + 0.64 * (f[0] - b[0]) + 0.59 * (b[0] - a[0])
    return {"truth": est, "solves": [a[0], b[0], f[0]], "balance": max(abs(a[2]), abs(b[2]), abs(f[2]))}


if __name__ == "__main__":
    sq = [[0, 0], [20, 0], [20, 20], [0, 20]]
    cu = [[1.2, 1.2], [18.8, 1.2], [18.8, 18.8], [1.2, 18.8]]
    print(truth(sq, [cu, cu], (8.0, 8.0, 12.0, 12.0), 200.0))
