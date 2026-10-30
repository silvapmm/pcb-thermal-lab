#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file graded3d.py
@brief The reviewer's independent 3D solver on a graded grid (imports nothing from pcbthermal nor from the other modules of this folder), used to extrapolate the reference to a converged value.
@details Written by the review from the physics, not from `resolved3d.py`: a quadrant of a square board (insulated sides, symmetry planes through the centre), a square part
         centred on the top face, a square copper-free window centred in chosen layers. Cell-centred finite volumes on a tensor-product grid whose cells are fine (`hf`) at the centre,
         the edge of the part and the edge of the window and grow linearly (slope `g`) to `hmax`; through the thickness each gap is graded towards both faces (`hz` to `dzmax`) and a
         layer with a window gets two sub-slabs. Zero-thickness face nodes on the top surface take the flux of the part and the film; the bottom film acts through the half bottom cell.
         The peak is the hottest face node under the part. `scale` multiplies every length of the grid, so a sequence of scales is a refinement study.
"""

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

# Stack-ups of the sweep: copper thicknesses and gaps in m (the simple 1.6 and 0.8 mm boards and the typical 4 and 6 layer templates of the program)
STACKS = {
    "2L 1.6 mm": ([35e-6, 35e-6], [1.6e-3 - 70e-6]),
    "2L 0.8 mm": ([35e-6, 35e-6], [0.8e-3 - 70e-6]),
    "4L typical": ([35e-6, 15.2e-6, 15.2e-6, 35e-6], [210.4e-6, 1065e-6, 210.4e-6]),
    "6L typical": ([35e-6] + [15.2e-6] * 4 + [35e-6], [115.2e-6, 519.4e-6, 200e-6, 519.4e-6, 115.2e-6]),
}


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
    # The number of cells is the integral of 1 / s; the edges are placed at equal steps of it
    cum = np.concatenate([[0.0], np.cumsum(0.5 * (1.0 / s[1:] + 1.0 / s[:-1]) * np.diff(xs))])
    n = max(1, int(np.ceil(cum[-1])))
    edges = np.interp(np.linspace(0.0, cum[-1], n + 1), cum, xs)
    return np.diff(edges)


def solve(stack, window, scale=1.0, board=30e-3, part=6e-3, power=1.0, h=10.0, k_cu=385.0, k_xy=0.9, k_z=0.3, window_layers=(0,),
          hf=0.04e-3, hmax=0.5e-3, g=0.25, hz=10e-6, dzmax=100e-6):
    """!
    @brief Peak rise of the face under the part.
    @param stack Key of STACKS.
    @param window Side of the centred copper-free window in m (0: full copper).
    @param scale Factor on every grid length (smaller is finer).
    @param board Board side in m.
    @param part Part side in m.
    @param power Power of the part in W.
    @param h Film coefficient of both faces in W/m2K (also under the part).
    @param k_cu Copper conductivity in W/mK.
    @param k_xy In-plane conductivity of the laminate in W/mK.
    @param k_z Through conductivity of the laminate in W/mK.
    @param window_layers 0-based layers that carry the window.
    @param hf Fine cell at the centre and at the edges of the part and of the window in m (before scale).
    @param hmax Largest cell in the plane in m (before scale).
    @param g Growth slope of the cell size.
    @param hz Finest sub-slab of a gap, at its faces, in m (before scale).
    @param dzmax Largest sub-slab of a gap in m (before scale).
    @return dict with peak (K), mean (K, area-weighted over the part), balance (heat out / heat in), unknowns, and lateral: the heat in W (whole board) that crosses the
            plane of the window edge x = window / 2 inside the window's extent, per sub-slab, with the sub-slab tops `z_top` in m (empty without a window).
    """
    hf, hmax, hz, dzmax = hf * scale, hmax * scale, hz * scale, dzmax * scale
    keys = sorted(set([0.0, part / 2, board / 2] + ([window / 2] if 0 < window < board else [])))
    widths = []
    for a, b in zip(keys[:-1], keys[1:]):
        # Fine at the centre and at the edges of the part and the window, coarse at the board edge
        widths.append(segment(a, b, hf, hf if b < board / 2 else hmax, hmax, g))
    wx = np.concatenate(widths)
    n = len(wx)
    xc = np.cumsum(wx) - wx / 2
    X, Y = np.meshgrid(xc, xc)
    in_window = (X < window / 2) & (Y < window / 2)
    in_part = (X < part / 2) & (Y < part / 2)
    t_cu, gaps = STACKS[stack]
    dz, KX, KZ = [], [], []
    for layer, t in enumerate(t_cu):
        bare = in_window if layer in window_layers else np.zeros((n, n), dtype=bool)
        m = 2 if layer in window_layers else 1                       # two sub-slabs where the layer has laminate showing
        for _ in range(m):
            dz.append(t / m)
            KX.append(np.where(bare, k_xy, k_cu))
            KZ.append(np.where(bare, k_z, k_cu))
        if layer < len(gaps):
            for s in segment(0.0, gaps[layer], hz, hz, dzmax, g):
                dz.append(s)
                KX.append(np.full((n, n), k_xy))
                KZ.append(np.full((n, n), k_z))
    dz, KX, KZ = np.array(dz), np.array(KX), np.array(KZ)
    nz = len(dz)
    N = nz * n * n + n * n                                           # cells plus the face nodes of the top surface
    idx = np.arange(nz * n * n).reshape(nz, n, n)
    face = nz * n * n + np.arange(n * n).reshape(n, n)
    area = wx[None, :] * wx[:, None]                                 # (y, x) area of every column
    rows, cols, vals = [], [], []
    diag = np.zeros(N)

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

    D = dz[:, None, None]
    # Half-cell resistances in series between neighbours (x, y, z)
    rx = (wx[None, None, :] / 2) / (KX * D * wx[None, :, None])
    link(idx[:, :, :-1], idx[:, :, 1:], 1.0 / (rx[:, :, :-1] + rx[:, :, 1:]))
    ry = (wx[None, :, None] / 2) / (KX * D * wx[None, None, :])
    link(idx[:, :-1, :], idx[:, 1:, :], 1.0 / (ry[:, :-1, :] + ry[:, 1:, :]))
    rz = (D / 2) / (KZ * area[None])
    link(idx[:-1], idx[1:], 1.0 / (rz[:-1] + rz[1:]))
    # The face nodes: half the top cell to the cell centre, the film to the ambient, the flux of the part
    link(face, idx[0], 1.0 / rz[0])
    diag[face.ravel()] += (h * area).ravel()
    g_bottom = 1.0 / (rz[-1] + 1.0 / (h * area))
    diag[idx[-1].ravel()] += g_bottom.ravel()
    q = np.zeros(N)
    a_part = area[in_part].sum()
    q[face[in_part]] = (power / 4) * area[in_part] / a_part           # a quadrant carries a quarter of the power
    K = sp.csc_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(N, N)) + sp.diags(diag)
    T = spla.spsolve(K, q)
    tf = T[face]
    out = float((h * area * tf).sum() + (g_bottom * T[idx[-1]]).sum())
    lateral, z_top = np.zeros(0), np.cumsum(dz) - dz
    if 0 < window < board:
        # Heat through the plane x = window / 2 for the rows inside the window (y < window / 2): eight half-sides of the quadrant make the four sides of the window
        i = int(np.argmin(np.abs(np.cumsum(wx) - window / 2)))
        rows_in = xc < window / 2
        Tc = T[: nz * n * n].reshape(nz, n, n)
        gx = 1.0 / (rx[:, :, i] + rx[:, :, i + 1])
        lateral = 8.0 * (gx[:, rows_in] * (Tc[:, rows_in, i] - Tc[:, rows_in, i + 1])).sum(axis=1)
    return {"peak": float(tf[in_part].max()), "mean": float((tf * area)[in_part].sum() / a_part), "balance": out / (power / 4), "unknowns": N,
            "lateral": lateral, "z_top": z_top}


def extrapolate(scales, values):
    """!
    @brief Limit of a refinement sequence by fitting v = v0 + C s^p to the three finest values.
    @param scales Grid scales, decreasing.
    @param values Peaks at those scales.
    @return Tuple (v0, p).
    """
    (s1, s2, s3), (v1, v2, v3) = scales[-3:], values[-3:]
    # Solve (v1 - v2) / (v2 - v3) = (s1^p - s2^p) / (s2^p - s3^p) for p by bisection
    target = (v1 - v2) / (v2 - v3)
    lo, hi = 0.2, 4.0
    for _ in range(100):
        p = 0.5 * (lo + hi)
        r = (s1 ** p - s2 ** p) / (s2 ** p - s3 ** p)
        lo, hi = (p, hi) if r < target else (lo, p)
    c = (v2 - v3) / (s2 ** p - s3 ** p)
    return v3 - c * s3 ** p, p
