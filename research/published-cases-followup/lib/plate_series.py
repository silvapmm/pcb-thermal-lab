#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file plate_series.py
@brief Exact (cosine double series) solution of the thin square plate with insulated edges, a film on one face and an isoflux rectangular source: the independent closed form for a source near an edge or a corner.
@details The thin plate (conductance g = k t, film h on the whole face) obeys g laplacian(theta) - h theta = -q on [0, L]^2 with insulated edges. The Neumann eigenfunctions cos(m pi x / L) cos(n pi y / L)
         diagonalise it: theta_mn = q_mn / (g lambda_mn + h), lambda_mn = (pi / L)^2 (m^2 + n^2), q_mn = eps_m eps_n q0 I_x I_y / L^2 with I = integral of the cosine over the source side
         (eps_0 = 1, eps_m = 2). The mean temperature of the plate is theta_00 = P / (h L^2) = R0 P (the film term). This is the method of images summed in the eigenfunction form (an insulated edge is the mirror,
         a corner the double mirror); it imports nothing from the program and is the continuum limit of the thin-plate finite-volume models, so a difference from it is the model, not the grid.
"""

import numpy as np


def _cos_integrals(side, a, b, n):
    """!
    @brief Integrals of cos(m pi x / side) over [a, b] for m = 0 .. n-1.
    @param side Plate side in m.
    @param a Start of the interval in m.
    @param b End of the interval in m.
    @param n Number of terms.
    @return numpy.ndarray Integrals in m.
    """
    m = np.arange(n)
    out = np.empty(n)
    out[0] = b - a
    out[1:] = side / (m[1:] * np.pi) * (np.sin(m[1:] * np.pi * b / side) - np.sin(m[1:] * np.pi * a / side))
    return out


def source_rise(side, g, h, rect, power=1.0, n_terms=600, n_probe=41):
    """!
    @brief Temperature rise of the thin plate for an isoflux rectangular source.
    @param side Plate side in m (square plate).
    @param g Sheet conductance k t in W/K.
    @param h Film coefficient of the whole face in W/m2K.
    @param rect Source (x0, y0, x1, y1) in m.
    @param power Power in W.
    @param n_terms Terms of the series in each direction.
    @param n_probe Points per side of the lattice that samples the source for the maximum and the mean.
    @return dict with t_max (maximum over the source), t_mean (mean over the source), t_film (mean over the plate = P / (h L^2)), rc (t_max - t_film), rc_mean (t_mean - t_film).
    """
    x0, y0, x1, y1 = rect
    q0 = power / ((x1 - x0) * (y1 - y0))
    ix = _cos_integrals(side, x0, x1, n_terms)
    iy = _cos_integrals(side, y0, y1, n_terms)
    eps = np.where(np.arange(n_terms) == 0, 1.0, 2.0)
    qmn = q0 / side ** 2 * np.outer(eps * ix, eps * iy)
    m = np.arange(n_terms)
    lam = (np.pi / side) ** 2 * (m[:, None] ** 2 + m[None, :] ** 2)
    c = qmn / (g * lam + h)
    xs = np.linspace(x0, x1, n_probe)
    ys = np.linspace(y0, y1, n_probe)
    cx = np.cos(np.outer(xs, m) * np.pi / side)             # (probe, m)
    cy = np.cos(np.outer(ys, m) * np.pi / side)
    theta = cy @ c.T @ cx.T                                  # (y, x): sum_mn c_mn cos(m x) cos(n y)
    # mean over the source by the exact integral of the cosines (not the lattice): <cos> = I / width
    t_mean = float((np.outer(ix / (x1 - x0), iy / (y1 - y0)) * c).sum())
    t_film = float(c[0, 0])
    return {"t_max": float(theta.max()), "t_mean": t_mean, "t_film": t_film, "rc": float(theta.max() - t_film), "rc_mean": t_mean - t_film}
