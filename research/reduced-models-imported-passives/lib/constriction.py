#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file constriction.py
@brief In-plane resistance, in squares of copper, between the pad of a part and the frame of a window of the copper mask: a measure of how the real copper pattern throttles the heat leaving the pad.
@details The conductance of the link between two neighbouring pixels is the harmonic mean of their coverages (a series of two half pixels); the pad pixels are one node; the
         frame of the window is held at zero. R is in "squares" (R = ln(b/a)/(2 pi) for a disc pad of radius a in a disc of radius b; R = L/W for a strip). The constriction factor kappa
         is R of the real mask divided by R of the same window and pad filled with copper. Only one copper layer is read (the heat that goes down through the vias and the
         laminate is not in it: the factor is a measure, not a model). Independent checks in tests/test_constriction.py (strip, disc).
"""

import numpy as np
import scipy.sparse as sp
import scipy.sparse.csgraph as csgraph
import scipy.sparse.linalg as spla


def resistance(cov, pad, fixed, leak=0.0):
    """!
    @brief Resistance in squares between the pad node and the fixed pixels.
    @param cov 2D float array, copper coverage 0..1 of every pixel (conductance weight of the pixel).
    @param pad 2D bool array, the pixels that form the source node (their own coverage is irrelevant).
    @param fixed 2D bool array, the pixels held at zero (the sink); must not overlap the pad.
    @param leak Conductance of every pixel to the ambient in units of the sheet conductance of a full pixel (a fin: lambda^2 = 1 / leak pixels^2); scalar or array; 0 for none.
    @return float R (inf when the pad is cut off from the sink by bare laminate).
    """
    ny, nx = cov.shape
    idx = np.arange(ny * nx).reshape(ny, nx)
    c = np.where(pad, 1.0, cov)                                    # The pad is solid copper for the link weights
    rows, cols, vals = [], [], []
    for a, b, ca, cb in ((idx[:, :-1], idx[:, 1:], c[:, :-1], c[:, 1:]), (idx[:-1, :], idx[1:, :], c[:-1, :], c[1:, :])):
        g = np.where(ca + cb > 0, 2 * ca * cb / np.maximum(ca + cb, 1e-30), 0.0)    # Harmonic mean of the two pixels
        m = g > 0
        rows.append(a[m]); cols.append(b[m]); vals.append(g[m])
    r = np.concatenate(rows); q = np.concatenate(cols); g = np.concatenate(vals)
    n = ny * nx
    L = sp.coo_matrix((np.concatenate([g, g, -g, -g]), (np.concatenate([r, q, r, q]), np.concatenate([r, q, q, r]))), shape=(n, n)).tocsr()
    # Reduced unknowns: free pixels (one each) plus one node for the whole pad; the fixed pixels drop out
    free = ~fixed.ravel() & ~pad.ravel()
    red = -np.ones(n, dtype=int)
    red[free] = np.arange(free.sum())
    red[pad.ravel()] = free.sum()                                  # All pad pixels -> the last unknown
    m_red = free.sum() + 1
    keep = red >= 0
    P = sp.coo_matrix((np.ones(keep.sum()), (np.nonzero(keep)[0], red[keep])), shape=(n, m_red)).tocsr()
    A = (P.T @ L @ P).tocsc()
    if np.any(np.asarray(leak) > 0):
        # The vertical leak of every pixel (the pad pixels add up in the pad node); the copper-free pixels keep the leak too (the laminate under them)
        lk = np.broadcast_to(np.asarray(leak, dtype=float), cov.shape).ravel()
        A = (A + sp.diags(np.bincount(red[keep], weights=lk[keep], minlength=m_red))).tocsc()
    b = np.zeros(m_red); b[-1] = 1.0                                # 1 unit of current into the pad
    # Only the connected component of the pad matters; if it has no link to the fixed pixels (row sums all zero) the pad is cut off
    ncomp, lab = csgraph.connected_components(A, directed=False)
    comp = np.nonzero(lab == lab[-1])[0]
    Ac = A[comp][:, comp].tocsc()
    if abs(Ac.sum()) < 1e-9 * max(1.0, abs(Ac.diagonal()).max()):
        return float("inf")
    bc = b[comp]
    try:
        vc = spla.spsolve(Ac, bc)
    except Exception:
        return float("inf")
    v = np.zeros(m_red); v[comp] = vc
    R = float(v[-1])
    return R if np.isfinite(R) and R < 1e9 else float("inf")


def kappa(cov, pad, half_side_px):
    """!
    @brief Constriction factor of a square window around the pad: R(real copper) / R(full copper).
    @param cov 2D float array, coverage of the layer in the window.
    @param pad 2D bool array, the pad pixels inside the window.
    @param half_side_px Unused size hint kept for the callers' record (the window is the array).
    @return (kappa, R_real, R_full); kappa is inf when the pad is cut off.
    """
    ny, nx = cov.shape
    fixed = np.zeros((ny, nx), dtype=bool)
    fixed[0, :] = fixed[-1, :] = fixed[:, 0] = fixed[:, -1] = True
    pad = pad & ~fixed
    R = resistance(cov, pad, fixed)
    Rf = resistance(np.ones_like(cov), pad, fixed)
    return (R / Rf if np.isfinite(R) else float("inf")), R, Rf
