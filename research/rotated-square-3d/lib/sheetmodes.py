#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file sheetmodes.py
@brief Closed-form (cosine series) solution of the layered idealisation on a rectangle with insulated edges, the exact reference for the cut-cell prototype.
@details The continuum problem behind the layered FVM is, for L full-copper layers with sheet conductance S_l (W/K per square), vertical
         conductance per area g_l = k_gap / d between layer l and l + 1, coefficients h_top and h_bottom on the outer layers and a heat source q on one layer:

             -S_l laplacian(theta_l) + g_{l-1} (theta_l - theta_{l-1}) + g_l (theta_l - theta_{l+1}) + h_l theta_l = q_l

         On the rectangle [x0, x0 + W] x [y0, y0 + H] with insulated edges every term is diagonal in the cosine modes cos(m pi x / W) cos(n pi y / H):
         each mode is an L x L tridiagonal system. The source is a uniform rectangle of total power P. This is independent of the program (the program's
         constants are only read to take the same numbers); the series is summed to `n_modes` per direction.
"""

import numpy as np


def layer_constants(problem):
    """!
    @brief Sheet conductance, vertical conductance per area and face coefficients of a full-copper board, as the FVM builds them.
    @param problem Problem whose zones are full copper on every layer (checked only by the caller).
    @return dict with S (L,), gz (L-1,), h_top, h_bottom.
    """
    b = problem.board
    m = b.materials
    slab = b.slab_thicknesses()
    k_lam, _ = b.layer_laminate()
    t = np.asarray(b.copper_thickness, dtype=float)
    s = m.k_copper * t + k_lam * (slab - t)
    k_gap = b.gap_properties()[0]
    gz = k_gap / b.gap_thicknesses() if b.layers > 1 else np.zeros(0)
    return {"S": s, "gz": gz, "h_top": b.h_top, "h_bottom": b.h_bottom}


def _cos_mean(m, a, b, length):
    """!
    @brief Mean of cos(m pi x / length) over [a, b] (m = 0 gives one).
    @param m Mode numbers (array).
    @param a Lower end.
    @param b Upper end.
    @param length Period parameter (the board side).
    @return Array like m.
    """
    m = np.asarray(m, dtype=float)
    k = m * np.pi / length
    out = np.ones_like(k)
    nz = k > 0
    out[nz] = (np.sin(k[nz] * b) - np.sin(k[nz] * a)) / (k[nz] * (b - a))
    return out


def rectangle_mean(const, size, src_layer, power, src_rect, read_rect, read_layer, n_modes=600):
    """!
    @brief Mean temperature rise over a rectangle for a uniform rectangular source, on a rectangular board with insulated edges.
    @param const Dict from `layer_constants`.
    @param size (W, H) of the board in metres, its lower-left corner at the origin of the coordinates used below.
    @param src_layer Index (0-based) of the layer that carries the source.
    @param power Source power in W.
    @param src_rect (x0, y0, x1, y1) of the source in metres.
    @param read_rect (x0, y0, x1, y1) of the rectangle whose mean is wanted.
    @param read_layer Index of the layer read.
    @param n_modes Modes per direction (the series converges like 1 / n for a patch mean over a finite rectangle).
    @return Mean rise in kelvin.
    """
    W, H = size
    s, gz = const["S"], const["gz"]
    nl = len(s)
    m = np.arange(n_modes + 1)
    lam_x = (m * np.pi / W) ** 2
    lam_y = (m * np.pi / H) ** 2
    # Source coefficients: q = P / A_src on the patch; q_mn = eps_m eps_n * mean-of-cos-products * (P / (W H)), eps_0 = 1, eps_m = 2
    ax = _cos_mean(m, src_rect[0], src_rect[2], W)
    ay = _cos_mean(m, src_rect[1], src_rect[3], H)
    rx = _cos_mean(m, read_rect[0], read_rect[2], W)
    ry = _cos_mean(m, read_rect[1], read_rect[3], H)
    eps = np.where(m == 0, 1.0, 2.0)
    wx, wy = eps * ax * rx, eps * ay * ry
    total = 0.0
    # One L x L system per (m, n); vectorised over n for each m
    for i in range(n_modes + 1):
        lam = lam_x[i] + lam_y                                              # array over n
        # Build the tridiagonal matrices for all n at once: shape (n, L, L)
        mat = np.zeros((len(lam), nl, nl))
        for l in range(nl):
            mat[:, l, l] += s[l] * lam
            if l == 0:
                mat[:, l, l] += const["h_top"]
            if l == nl - 1:
                mat[:, l, l] += const["h_bottom"]
            if l > 0:
                mat[:, l, l] += gz[l - 1]
                mat[:, l, l - 1] -= gz[l - 1]
            if l < nl - 1:
                mat[:, l, l] += gz[l]
                mat[:, l, l + 1] -= gz[l]
        rhs = np.zeros((len(lam), nl, 1))
        rhs[:, src_layer, 0] = 1.0
        sol = np.linalg.solve(mat, rhs)[:, read_layer, 0]                  # response of the read layer to a unit source on src_layer
        total += (wx[i] * wy * sol).sum()
    return float(power / (W * H) * total)
