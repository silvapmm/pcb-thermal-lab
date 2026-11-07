#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file graded3d.py
@brief The reviewer's independent 3D reference: steady finite volumes of a laminated plate on a GRADED tensor mesh (fine at the board edges and at the source edges), side film
       behind the half cell of every slab, films on both faces; imports nothing from pcbthermal and shares no code with layered3d_side.py.
@details Written because the uniform reference of the study (`layered3d_side.py`, 0.25 to 0.5 mm cells, 4 to 16 sub-slabs) cannot resolve the laminate boundary layer at the edge,
         whose thickness is about `k_xy / h_side` (0.45 mm at 2000 W/m2K). Cells grow geometrically from `h_min` at every board edge and source edge up to `h_max`; the laminate is cut
         into `nz_lam` equal sub-slabs. On a uniform mesh it reproduces `layered3d_side.py` to the printed digits (81.648 / 80.435 K, 3.2 mm, 200 W/m2K, corner, 0.5 mm, 4 / 16
         sub-slabs). The direct solve or smoothed-aggregation AMG with CG (pyamg, tolerance 1e-12; same answer to 1e-12 K on the cases checked) keeps the memory below 1 GB.
"""

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla


def graded(L, h_min, h_max, ratio):
    """!
    @brief Cell widths of an interval, fine (h_min) at both ends, growing by `ratio` up to h_max, uniform in the middle.
    @param L Length of the interval in m.
    @param h_min Width of the end cells in m.
    @param h_max Largest width in m.
    @param ratio Growth factor between neighbouring cells (1 gives a uniform mesh of h_min).
    @return numpy.ndarray Widths in m summing exactly to L.
    """
    def side():
        """!
        @brief Geometric run from one end up to half the interval.
        @return list of widths in m.
        """
        out, h = [], h_min
        while sum(out) < L / 2:
            out.append(min(h, h_max))
            h *= ratio
        return out
    left, right = side(), side()
    sl, sr = sum(left), sum(right)
    while sl + sr > L:                                   # trim the runs until they fit
        if len(left) >= len(right):
            sl -= left.pop()
        else:
            sr -= right.pop()
    mid = L - sl - sr
    if mid <= 1e-12 * L:
        cells = left + right[::-1]
    else:
        nm = max(1, int(np.ceil(mid / h_max - 1e-6)))
        cells = left + [mid / nm] * nm + right[::-1]
    cells = np.array(cells)
    return cells * (L / cells.sum())                     # exact length (round-off)


def axis(L, breaks, h_min, h_max, ratio):
    """!
    @brief Cells of one axis with faces on 0, L and every break (the source edges), graded in every interval.
    @param L Length in m.
    @param breaks Positions in m that must be cell faces.
    @param h_min Smallest cell in m.
    @param h_max Largest cell in m.
    @param ratio Growth factor.
    @return numpy.ndarray Widths in m.
    """
    pts = sorted(set([0.0, L] + [s for s in breaks if 0 < s < L]))
    return np.concatenate([graded(b - a, h_min, h_max, ratio) for a, b in zip(pts[:-1], pts[1:])])


def solve(W, H, src, t_cu, d, hs, hf=10.0, P=2.0, h_min=2e-5, h_max=5e-4, ratio=1.3, nz_lam=24, k_cu=385.0, kxy=0.9, kz=0.3, sym=(False, False), amg=True):
    """!
    @brief Hottest rise of the top copper of a two-layer board (copper, laminate, copper) with a uniform square source on the top copper.
    @param W Width of the domain in m.
    @param H Height of the domain in m.
    @param src (x0, y0, x1, y1) of the source in m.
    @param t_cu Copper thickness in m (both layers).
    @param d Laminate thickness in m.
    @param hs Edge (side) film coefficient in W/m2K.
    @param hf Film coefficient of both faces in W/m2K (on the whole top face, also under the source).
    @param P Power in W (of the domain: a quarter of the board power with two symmetry planes).
    @param h_min Smallest in-plane cell in m.
    @param h_max Largest in-plane cell in m.
    @param ratio Growth factor of the in-plane cells.
    @param nz_lam Sub-slabs of the laminate.
    @param k_cu Copper conductivity in W/mK.
    @param kxy In-plane conductivity of the laminate in W/mK.
    @param kz Through conductivity of the laminate in W/mK.
    @param sym (x, y): True makes the plane x = 0 (y = 0) a symmetry plane (no film there).
    @param amg True: CG with a smoothed-aggregation AMG preconditioner (pyamg); False: sparse LU.
    @return dict rise (K), n (unknowns), balance (heat out over heat in), side (share of the heat that leaves through the edge).
    """
    dxs = axis(W, [src[0], src[2]], h_min, h_max, ratio)
    dys = axis(H, [src[1], src[3]], h_min, h_max, ratio)
    dz = np.concatenate([[t_cu], np.full(nz_lam, d / nz_lam), [t_cu]])
    kin = np.concatenate([[k_cu], np.full(nz_lam, kxy), [k_cu]])
    kth = np.concatenate([[k_cu], np.full(nz_lam, kz), [k_cu]])
    nx, ny, nz = len(dxs), len(dys), len(dz)
    n = nx * ny * nz
    idx = np.arange(n).reshape(nz, ny, nx)
    rows, cols, vals = [], [], []
    diag = np.zeros(n)

    def link(a, b, g):
        """!
        @brief Add the symmetric conductance g between node arrays a and b.
        @param a Node indices.
        @param b Node indices.
        @param g Conductance in W/K.
        @return None.
        """
        rows.extend([a.ravel(), b.ravel()])
        cols.extend([b.ravel(), a.ravel()])
        vals.extend([-g.ravel(), -g.ravel()])
        np.add.at(diag, a.ravel(), g.ravel())
        np.add.at(diag, b.ravel(), g.ravel())

    DX, DY, DZ = dxs[None, None, :], dys[None, :, None], dz[:, None, None]
    KI, KT = kin[:, None, None], kth[:, None, None]
    rx = np.broadcast_to(DX / (2 * KI * DY * DZ), (nz, ny, nx))          # half-cell resistances, K/W
    ry = np.broadcast_to(DY / (2 * KI * DX * DZ), (nz, ny, nx))
    rz = np.broadcast_to(DZ / (2 * KT * DX * DY), (nz, ny, nx))
    link(idx[:, :, :-1], idx[:, :, 1:], 1.0 / (rx[:, :, :-1] + rx[:, :, 1:]))
    link(idx[:, :-1, :], idx[:, 1:, :], 1.0 / (ry[:, :-1, :] + ry[:, 1:, :]))
    link(idx[:-1], idx[1:], 1.0 / (rz[:-1] + rz[1:]))
    A = dys[:, None] * dxs[None, :]
    gt = 1.0 / (rz[0] + 1.0 / (hf * A))                                   # face films behind half a cell
    gb = 1.0 / (rz[-1] + 1.0 / (hf * A))
    diag[idx[0].ravel()] += gt.ravel()
    diag[idx[-1].ravel()] += gb.ravel()
    gs = np.zeros((nz, ny, nx))
    if hs > 0:                                                            # side films behind half a cell of every slab
        gxl = 1.0 / (rx + 1.0 / (hs * np.broadcast_to(DY * DZ, (nz, ny, nx))))
        gyl = 1.0 / (ry + 1.0 / (hs * np.broadcast_to(DX * DZ, (nz, ny, nx))))
        if not sym[0]:
            gs[:, :, 0] += gxl[:, :, 0]
        gs[:, :, -1] += gxl[:, :, -1]
        if not sym[1]:
            gs[:, 0, :] += gyl[:, 0, :]
        gs[:, -1, :] += gyl[:, -1, :]
    diag += gs.ravel()
    xc, yc = np.cumsum(dxs) - dxs / 2, np.cumsum(dys) - dys / 2
    m = (xc[None, :] > src[0]) & (xc[None, :] < src[2]) & (yc[:, None] > src[1]) & (yc[:, None] < src[3])
    q = np.zeros(n)
    q[idx[0][m]] = P * A[m] / A[m].sum()                                  # uniform flux over the source
    K = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsr() + sp.diags(diag)
    if amg:
        import pyamg
        ml = pyamg.smoothed_aggregation_solver(K, symmetry="symmetric", max_coarse=2000)
        T = ml.solve(q, tol=1e-12, accel="cg", maxiter=2000).reshape(nz, ny, nx)
    else:
        T = spla.spsolve(K.tocsc(), q, permc_spec="MMD_AT_PLUS_A").reshape(nz, ny, nx)
    out = float((gt * T[0]).sum() + (gb * T[-1]).sum() + (gs * T).sum())
    return dict(rise=float(T[0].max()), n=n, balance=out / q.sum(), side=float((gs * T).sum()) / q.sum())


def case(t_mm, hs, pos, **kw):
    """!
    @brief The 30 x 20 mm, two-layer board of the study (35 um copper, 10 mm, 2 W part, faces 10 W/m2K), corner (full board) or centre (a quarter with two symmetry planes).
    @param t_mm Board thickness in mm.
    @param hs Edge coefficient in W/m2K.
    @param pos "corner" or "centre".
    @param kw Mesh options of solve().
    @return dict of solve().
    """
    t_cu = 35e-6
    d = t_mm * 1e-3 - 2 * t_cu
    if pos == "corner":
        return solve(30e-3, 20e-3, (0.0, 0.0, 10e-3, 10e-3), t_cu, d, hs, **kw)
    if pos == "centre":
        return solve(15e-3, 10e-3, (0.0, 0.0, 5e-3, 5e-3), t_cu, d, hs, P=0.5, sym=(True, True), **kw)
    raise ValueError(pos)
