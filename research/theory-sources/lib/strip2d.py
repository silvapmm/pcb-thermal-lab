#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file strip2d.py
@brief Independent two-dimensional finite-volume solver for the trace cells of Lemczyk, Mack, Culham and Yovanovich (1992), Fig. 3 (a) and (b).
@details Cell of width L1 (x) and thickness t (z), conductivity k, adiabatic ends; the trace occupies 0 <= x <= w and is held at the contact temperature Tc (above the fluid) on the top
face (case a, c) or at the mid-plane of the double cell (case b, d); the rest of the top face has film coefficient h2 and the bottom face h1. The heat flow per metre of trace length
(L2 = 1 m) is Q = flux into the trace through the solid plus h2 w Tc for case (a) (equation 27 of the paper, the film also acts over the trace).
It imports nothing from `pcbthermal`.
"""

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla


def _grid(length, n, strength):
    """!
    @brief Cell edges on [0, length], geometrically refined towards 0 (strength 1 = uniform).
    @param length Length (m).
    @param n Number of cells.
    @param strength Ratio of the last to the first cell size (1 = uniform).
    @return Array of n + 1 edges.
    """
    if strength == 1.0:
        return np.linspace(0.0, length, n + 1)
    r = strength ** (1.0 / max(n - 1, 1))
    w = r ** np.arange(n)
    return np.concatenate([[0.0], np.cumsum(w) / w.sum() * length])


def trace_heat_flow(w, t, l1, k, h1, h2, tc=90.0, nx=300, nz=200, grade=8.0):
    """!
    @brief Heat flow Q_a of the surface trace (case a) per metre of trace length.
    @param w Trace width (m).
    @param t Thickness of the cell (m).
    @param l1 Cell width (m).
    @param k Conductivity (W/mK).
    @param h1 Bottom film coefficient (W/m2K).
    @param h2 Top film coefficient (W/m2K).
    @param tc Contact temperature above the fluid (K).
    @param nx Cells along x (refined towards the trace edge at x = w by the `grade` ratio on each side).
    @param nz Cells along z (refined towards the top face).
    @param grade Ratio of the coarsest to the finest cell size.
    @return float Q_a in W per metre of trace length (equation 27 of the paper).
    """
    # x edges: refine around x = w by joining two graded pieces; the trace edge is an edge of the mesh
    nx1 = max(int(nx * w / l1), 10)
    nx2 = max(nx - nx1, 10)
    xe1 = w - _grid(w, nx1, grade)[::-1]                          # fine at x = w, coarse at x = 0
    xe2 = w + _grid(l1 - w, nx2, grade)                           # fine at x = w, coarse at x = l1
    xe = np.concatenate([xe1[:-1], xe2]) if l1 > w else xe1
    ze = t - _grid(t, nz, grade)[::-1]                            # fine at the top face z = t
    dx, dz = np.diff(xe), np.diff(ze)
    nxc, nzc = len(dx), len(dz)
    n = nxc * nzc
    idx = np.arange(n).reshape(nzc, nxc)
    rows, cols, vals = [], [], []
    diag = np.zeros(n)
    rhs = np.zeros(n)
    # Horizontal faces between (j, i) and (j, i+1): conductance k dz / (dx_i/2 + dx_{i+1}/2)
    gh = k * dz[:, None] / (0.5 * dx[None, :-1] + 0.5 * dx[None, 1:])
    a, b = idx[:, :-1].ravel(), idx[:, 1:].ravel()
    rows += [a, b]
    cols += [b, a]
    vals += [-gh.ravel(), -gh.ravel()]
    np.add.at(diag, a, gh.ravel())
    np.add.at(diag, b, gh.ravel())
    gv = k * dx[None, :] / (0.5 * dz[:-1, None] + 0.5 * dz[1:, None])
    a, b = idx[:-1, :].ravel(), idx[1:, :].ravel()
    rows += [a, b]
    cols += [b, a]
    vals += [-gv.ravel(), -gv.ravel()]
    np.add.at(diag, a, gv.ravel())
    np.add.at(diag, b, gv.ravel())
    # Bottom film h1 in series with the half cell
    gb = 1.0 / (1.0 / h1 + 0.5 * dz[0] / k) * dx
    diag[idx[0, :]] += gb
    # Top face: trace cells held at Tc through the half cell, the rest with the film h2 in series with the half cell
    xc = 0.5 * (xe[1:] + xe[:-1])
    on_trace = xc < w
    g_trace = k * dx[on_trace] / (0.5 * dz[-1])
    diag[idx[-1, on_trace]] += g_trace
    rhs[idx[-1, on_trace]] += g_trace * tc
    g_film = 1.0 / (1.0 / h2 + 0.5 * dz[-1] / k) * dx[~on_trace]
    diag[idx[-1, ~on_trace]] += g_film
    m = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsr() + sp.diags(diag)
    temp = spla.spsolve(m.tocsc(), rhs)
    top = temp.reshape(nzc, nxc)[-1, on_trace]
    q_solid = float((g_trace * (tc - top)).sum())
    return q_solid + h2 * w * tc
