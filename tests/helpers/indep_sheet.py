#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file indep_sheet.py
@brief Independent reference (copy of research/cut-cell-links/lib/indep_sheet.py, for tests/test_solid3d_sliver_cells.py): two coupled conducting sheets on an aligned rectangle, written without any code of the program (it imports nothing from pcbthermal).
@details The layered idealisation of the two-layer full-copper board of the studies: two sheets of conductance `S` per square joined by the gap conductance per area `GZ`,
         films `HT` on the top sheet and `HB` on the bottom sheet, and an edge film `h_side` times the slab thickness `SLAB` per length of edge on each sheet. Cell-centred
         finite volumes on a rectangle aligned with the grid (no cut cell anywhere), with the edge film **in series with the half-cell conduction** from the node to the edge
         (second order at the edge; the program puts the film on the node, first order). The source is a rectangle (exact area weights) or a polygon (8 x 8 samples per cell).
         The constants are the values of `Problem.new(..., 2)` with full copper read once from the program's network (S = 0.0141635 W/K, gap 196.08 W/m2K, h_top 10,
         h_bottom 15 W/m2K, slab 0.8 mm), i.e. the same board; the discretisation is this file's own. `richardson` extrapolates three cells halved in turn.
"""

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

S = 0.0141635               # Sheet conductance of a copper layer node (35 um copper and 0.765 mm of FR-4 in-plane), W/K
GZ = 196.078431372549       # Gap conductance per area (0.3 W/mK over 1.53 mm), W/m2K
HT = 10.0                   # Film on the top face, W/m2K
HB = 15.0                   # Film on the bottom face, W/m2K
SLAB = 0.8e-3               # Thickness represented by each sheet (edge film per length = h_side * SLAB), m


def weights_rect(r, W, H, nx, ny):
    """!
    @brief Exact area weights of an aligned rectangle on the grid.
    @param r Rectangle (x0, y0, x1, y1) in m.
    @param W Width of the board in m.
    @param H Height of the board in m.
    @param nx Cells along x.
    @param ny Cells along y.
    @return Array (ny, nx) summing to 1.
    """
    dx, dy = W / nx, H / ny
    xe, ye = np.arange(nx + 1) * dx, np.arange(ny + 1) * dy
    ox = np.clip(np.minimum(xe[1:], r[2]) - np.maximum(xe[:-1], r[0]), 0, None)
    oy = np.clip(np.minimum(ye[1:], r[3]) - np.maximum(ye[:-1], r[1]), 0, None)
    w = oy[:, None] * ox[None, :]
    return w / w.sum()


def weights_poly(poly, W, H, nx, ny, m=8):
    """!
    @brief Area weights of a polygon by m x m point samples per cell (the turned part of the frame problems).
    @param poly Polygon (n, 2) in m.
    @param W Width in m.
    @param H Height in m.
    @param nx Cells along x.
    @param ny Cells along y.
    @param m Samples per cell side.
    @return Array (ny, nx) summing to 1.
    """
    from matplotlib.path import Path
    dx, dy = W / nx, H / ny
    xs, ys = (np.arange(nx * m) + 0.5) * dx / m, (np.arange(ny * m) + 0.5) * dy / m
    X, Y = np.meshgrid(xs, ys)
    ins = Path(np.asarray(poly)).contains_points(np.c_[X.ravel(), Y.ravel()]).reshape(ny * m, nx * m)
    w = ins.reshape(ny, m, nx, m).sum(axis=(1, 3)).astype(float)
    return w / w.sum()


def solve(W, H, h, h_side, src, power=2.0, poly=False):
    """!
    @brief Steady rise of the two sheets with the source on the top sheet.
    @param W Width of the rectangle in m.
    @param H Height in m.
    @param h Target cell side in m (the cells are W/nx by H/ny).
    @param h_side Edge coefficient in W/m2K.
    @param src Source rectangle (x0, y0, x1, y1) in m, or a polygon (n, 2) when `poly`.
    @param power Power in W.
    @param poly True when `src` is a polygon.
    @return (peak rise of the top sheet in K, heat to the air over the power).
    """
    nx, ny = max(int(round(W / h)), 2), max(int(round(H / h)), 2)
    dx, dy = W / nx, H / ny
    w = weights_poly(src, W, H, nx, ny) if poly else weights_rect(src, W, H, nx, ny)
    n = nx * ny
    idx = np.arange(2 * n).reshape(2, ny, nx)
    rows, cols, vals = [], [], []

    def cp(a, b, g):
        # Symmetric link g between nodes a and b
        a, b = a.ravel(), b.ravel()
        g = np.broadcast_to(g, a.shape).ravel()
        rows.extend([a, b, a, b])
        cols.extend([a, b, b, a])
        vals.extend([g, g, -g, -g])

    for L in (0, 1):
        cp(idx[L, :, :-1], idx[L, :, 1:], S * dy / dx)
        cp(idx[L, :-1, :], idx[L, 1:, :], S * dx / dy)
    cp(idx[0], idx[1], GZ * dx * dy)
    diag = np.zeros((2, ny, nx))
    diag[0] += HT * dx * dy
    diag[1] += HB * dx * dy
    if h_side:
        Hl = h_side * SLAB
        # Film in series with the conduction over half a cell to the edge
        ex = 1.0 / (1.0 / (Hl * dy) + 0.5 * dx / (S * dy))
        ey = 1.0 / (1.0 / (Hl * dx) + 0.5 * dy / (S * dx))
        diag[:, :, 0] += ex
        diag[:, :, -1] += ex
        diag[:, 0, :] += ey
        diag[:, -1, :] += ey
    rows.append(np.arange(2 * n))
    cols.append(np.arange(2 * n))
    vals.append(diag.ravel())
    K = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(2 * n, 2 * n)).tocsc()
    q = np.zeros(2 * n)
    q[:n] = power * w.ravel()
    T = spla.spsolve(K, q)
    return float(T[:n].max()), float((diag.ravel() * T).sum() / power)


def richardson(f, hs):
    """!
    @brief Extrapolate a value from three cells, each half of the previous one (order read from the ratio, first order outside 1.5 to 6).
    @param f Function of the cell (m) returning the value.
    @param hs Three cells in m.
    @return (extrapolated value, the three values, observed order or NaN).
    """
    t = [f(h) for h in hs]
    d12, d23 = t[1] - t[0], t[2] - t[1]
    r = d12 / d23 if abs(d23) > 1e-12 else 4.0
    p = float(np.log2(r)) if r > 1 else float("nan")
    ref = t[2] + d23 / (r - 1.0) if 1.5 <= r <= 6.0 else t[2] + d23
    return ref, t, p
