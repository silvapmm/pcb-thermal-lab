#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file graded_pad3d.py
@brief Independent 3D finite-volume solver on a graded grid for a laminated board with copper pads (imports nothing from pcbthermal): the converged reference of the pad boards.
@details A quadrant of a square board (insulated sides, symmetry planes through the centre), a square source centred on the top face, and in every copper layer either full copper, no
         copper, or copper only inside a centred square pad (laminate elsewhere in that layer). Cell-centred finite volumes on a tensor-product grid: in the plane the cells are fine
         (`hf`) at the centre, at the edge of the source, of the pad and of the model cell, and grow linearly (slope `g`) to `hmax` towards the board edge; through the thickness each dielectric gap
         is graded towards both faces (`hz` to `dzmax`) and a copper layer that has laminate showing is cut into two sub-slabs. Conductances between neighbours are the series of the half-cell
         resistances. Zero-thickness face nodes on the top surface take the flux of the source and the film (also under the source, as the program does); the bottom film acts through the
         half bottom cell. The peak read is the mean of the face over the model cell that touches the centre (what a program cell gives), and the mean over the source.
         `scale` multiplies every length of the grid so that a sequence of scales is a refinement study (`extrapolate`). The design follows the reviewer's solver of
         research/bare-spot-under-source/lib/graded3d.py (window boards), generalised here to pads, any stack and any films; tests/test_graded_pad3d.py checks it against the exact series.
"""

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla


def segment(a, b, h_a, h_b, hmax, g):
    """!
    @brief Cell widths on [a, b]: h_a at a and h_b at b, growing linearly with slope g away from each end, capped at hmax.
    @param a Start in m.
    @param b End in m.
    @param h_a Cell size at a in m.
    @param h_b Cell size at b in m.
    @param hmax Largest cell in m.
    @param g Growth of the cell size per unit length.
    @return numpy.ndarray of widths summing to b - a.
    """
    span = b - a
    xs = np.linspace(0.0, span, 20001)
    s = np.minimum(hmax, np.minimum(h_a + g * xs, h_b + g * (span - xs)))
    # The number of cells is the integral of 1 / s; the edges sit at equal steps of that integral
    cum = np.concatenate([[0.0], np.cumsum((1.0 / s[1:] + 1.0 / s[:-1]) / 2 * np.diff(xs))])
    n = max(int(round(cum[-1])), 1)
    edges = np.interp(np.linspace(0.0, cum[-1], n + 1), cum, xs)
    return np.diff(edges)


def solve(layers, copper, gaps, board, source, pad_sides, cell, power=1.0, h_top=10.0, h_bottom=10.0, k_cu=385.0, k_xy=0.9, k_z=0.3,
          scale=1.0, hf=0.06e-3, hmax=0.6e-3, g=0.25, hz=10e-6, dzmax=120e-6):
    """!
    @brief Peak rise of the face under the source on a board with pads.
    @param layers Number of copper layers.
    @param copper List of copper thicknesses in m (one per layer).
    @param gaps List of gap thicknesses in m (layers - 1).
    @param board Board side in m.
    @param source Source side in m (centred square on the top face).
    @param pad_sides Per layer: None for full copper, 0 for no copper, or the side in m of the centred copper pad (laminate outside it).
    @param cell Cell size in m of the model to compare with (an even number of cells across the board): the peak is the mean over the cell [0, cell]^2 of the quadrant.
    @param power Power in W.
    @param h_top Top film in W/m2K.
    @param h_bottom Bottom film in W/m2K.
    @param k_cu Copper conductivity in W/mK.
    @param k_xy In-plane conductivity of the laminate in W/mK (one value for every gap).
    @param k_z Through conductivity of the laminate in W/mK.
    @param scale Factor on every grid length (smaller is finer).
    @param hf Fine in-plane cell in m (before scale).
    @param hmax Largest in-plane cell in m (before scale).
    @param g Growth slope of the cell size.
    @param hz Finest sub-slab of a gap in m, at its faces (before scale).
    @param dzmax Largest sub-slab of a gap in m (before scale).
    @return dict with peak (K), mean (K, over the source), balance (heat out / heat in), unknowns.
    """
    hf, hmax, hz, dzmax = hf * scale, hmax * scale, hz * scale, dzmax * scale
    pads = [p for p in pad_sides if p]
    keys = sorted(set([0.0, source / 2, cell, board / 2] + [p / 2 for p in pads if p < board]))
    widths = [segment(a, b, hf, hf if b < board / 2 else hmax, hmax, g) for a, b in zip(keys[:-1], keys[1:])]
    wx = np.concatenate(widths)
    n = len(wx)
    edges = np.concatenate([[0.0], np.cumsum(wx)])
    xc = edges[:-1] + wx / 2
    xx, yy = np.meshgrid(xc, xc)
    in_src = (xx < source / 2) & (yy < source / 2)
    dz, kx, kz = [], [], []
    for l in range(layers):
        side = pad_sides[l]
        if side is None:
            copper_map = np.ones((n, n), dtype=bool)
        elif side == 0:
            copper_map = np.zeros((n, n), dtype=bool)
        else:
            copper_map = (xx < side / 2) & (yy < side / 2)
        mixed = not copper_map.all()
        for _ in range(2 if mixed else 1):
            dz.append(copper[l] / (2 if mixed else 1))
            kx.append(np.where(copper_map, k_cu, k_xy))
            kz.append(np.where(copper_map, k_cu, k_z))
        if l < layers - 1:
            for s in segment(0.0, gaps[l], hz, hz, dzmax, g):
                dz.append(s)
                kx.append(np.full((n, n), k_xy))
                kz.append(np.full((n, n), k_z))
    dz, kx, kz = np.array(dz), np.array(kx), np.array(kz)
    nz = len(dz)
    big_n = nz * n * n + n * n                                       # cells plus the face nodes of the top surface
    idx = np.arange(nz * n * n).reshape(nz, n, n)
    face = nz * n * n + np.arange(n * n).reshape(n, n)
    area = wx[None, :] * wx[:, None]
    rows, cols, vals = [], [], []
    diag = np.zeros(big_n)

    def link(a, b, gg):
        """!
        @brief Add a conductance between two sets of unknowns.
        @param a Indices of the first set.
        @param b Indices of the second set.
        @param gg Conductances in W/K (broadcast to the shape of a).
        @return None.
        """
        gg = np.broadcast_to(gg, a.shape).ravel()
        a, b = a.ravel(), b.ravel()
        rows.extend([a, b])
        cols.extend([b, a])
        vals.extend([-gg, -gg])
        np.add.at(diag, a, gg)
        np.add.at(diag, b, gg)

    d = dz[:, None, None]
    # Half-cell resistances in series between neighbours (x, y, z)
    rx = (wx[None, None, :] / 2) / (kx * d * wx[None, :, None])
    link(idx[:, :, :-1], idx[:, :, 1:], 1.0 / (rx[:, :, :-1] + rx[:, :, 1:]))
    ry = (wx[None, :, None] / 2) / (kx * d * wx[None, None, :])
    link(idx[:, :-1, :], idx[:, 1:, :], 1.0 / (ry[:, :-1, :] + ry[:, 1:, :]))
    rz = (d / 2) / (kz * area[None])
    link(idx[:-1], idx[1:], 1.0 / (rz[:-1] + rz[1:]))
    # The face nodes: half the top cell to the cell centre, the film to the ambient, the flux of the source
    link(face, idx[0], 1.0 / rz[0])
    diag[face.ravel()] += (h_top * area).ravel()
    g_bottom = 1.0 / (rz[-1] + 1.0 / (h_bottom * area))
    diag[idx[-1].ravel()] += g_bottom.ravel()
    q = np.zeros(big_n)
    a_src = area[in_src].sum()
    q[face[in_src]] = (power / 4) * area[in_src] / a_src               # a quadrant carries a quarter of the power
    k_mat = sp.csc_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(big_n, big_n)) + sp.diags(diag)
    t = spla.spsolve(k_mat, q)
    tf = t[face]
    out = float((h_top * area * tf).sum() + (g_bottom * t[idx[-1]]).sum())
    blk = (xx < cell) & (yy < cell)
    return {"peak": float((tf * area)[blk].sum() / area[blk].sum()), "mean": float((tf * area)[in_src].sum() / a_src), "balance": out / (power / 4), "unknowns": big_n}


def extrapolate(scales, values):
    """!
    @brief Limit of a refinement sequence by fitting v = v0 + C s^p to the three finest values.
    @param scales Grid scales, decreasing.
    @param values Peaks at those scales.
    @return Tuple (v0, p).
    """
    (s1, s2, s3), (v1, v2, v3) = scales[-3:], values[-3:]
    target = (v1 - v2) / (v2 - v3)
    lo, hi = 0.2, 4.0
    for _ in range(100):
        p = 0.5 * (lo + hi)
        r = (s1 ** p - s2 ** p) / (s2 ** p - s3 ** p)
        lo, hi = (p, hi) if r < target else (lo, p)
    c = (v2 - v3) / (s2 ** p - s3 ** p)
    return v3 - c * s3 ** p, p
