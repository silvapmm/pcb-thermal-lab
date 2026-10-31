#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file cond2d.py
@brief Independent solver and closed forms for the effective conductivity of two-phase two-dimensional media (F4).
@details The solver is a cell-centred finite-volume solution of div(sigma grad u) = 0 on a periodic square cell with a unit mean gradient along x
(harmonic mean of the two cell conductivities on each face), so `sigma_eff = <j_x> / <e_x>`. It imports nothing from `pcbthermal`.
The closed forms are written from Milton, The Theory of Composites (2002): equations 7.9 and 7.10 (coated cylinders and the Hashin-Shtrikman bounds for d = 2 and 3),
3.9 and 3.11 (phase interchange and the checkerboard), 10.31 and 10.32 (Bruggeman for spheres) and the d-dimensional form of the self-consistency equation
(derived here from equation 7.9 in the same step Milton takes for spheres in section 10.5).
"""

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla


def effective_conductivity(sigma):
    """!
    @brief Effective conductivity along x of a periodic two-dimensional cell of cell-wise constant isotropic conductivity.
    @param sigma 2D array (ny, nx) of conductivities, rows along y and columns along x; the cell repeats periodically.
    @return float sigma_eff = <j_x>/<e_x> for a unit mean gradient along x.
    """
    ny, nx = sigma.shape
    n = nx * ny
    idx = np.arange(n).reshape(ny, nx)
    # Face conductances: harmonic mean of the two neighbours, unit spacing, periodic neighbours by np.roll
    gx = 2.0 * sigma * np.roll(sigma, -1, axis=1) / (sigma + np.roll(sigma, -1, axis=1))     # face between (j, i) and (j, i+1)
    gy = 2.0 * sigma * np.roll(sigma, -1, axis=0) / (sigma + np.roll(sigma, -1, axis=0))
    ii = np.concatenate([idx.ravel(), idx.ravel()])
    jj = np.concatenate([np.roll(idx, -1, axis=1).ravel(), np.roll(idx, -1, axis=0).ravel()])
    off = sp.coo_matrix((np.concatenate([-gx.ravel(), -gy.ravel()]), (ii, jj)), shape=(n, n))
    off = off + off.T
    diag = (gx + np.roll(gx, 1, axis=1) + gy + np.roll(gy, 1, axis=0)).ravel()
    # The potential is u = -x + v with v periodic, so the flux over the +x face is g (1 + v_i - v_{i+1}) and conservation gives K v = -(g_right - g_left)
    k = (sp.diags(diag) + off).tocsc() + sp.identity(n, format="csc") * 1e-12 * diag.mean()   # the tiny shift pins the free constant
    v = spla.spsolve(k, -(gx - np.roll(gx, 1, axis=1)).ravel()).reshape(ny, nx)
    flux = gx * (1.0 + v - np.roll(v, -1, axis=1))
    return float(flux.mean())


def checkerboard(n_sub, s1, s2, squares=2):
    """!
    @brief A periodic checkerboard cell.
    @param n_sub Cells per square side.
    @param s1 Conductivity of the first phase.
    @param s2 Conductivity of the second phase.
    @param squares Squares per side of the periodic cell (even).
    @return 2D array of conductivities.
    """
    i = (np.arange(squares * n_sub) // n_sub)
    mask = (i[:, None] + i[None, :]) % 2 == 0
    return np.where(mask, s1, s2).astype(float)


def disk_array(n, fraction, s1, s2):
    """!
    @brief A square array of circular inclusions of phase 1 with the given area fraction, one per cell, in a matrix of phase 2 (anti-aliased by 4x4 sub-sampling).
    @param n Cells per side.
    @param fraction Area fraction of phase 1.
    @param s1 Conductivity of the inclusion.
    @param s2 Conductivity of the matrix.
    @return 2D array of conductivities (the phase-1 area fraction of each cell is mixed with the arithmetic mean).
    """
    r = np.sqrt(fraction / np.pi) * n
    sub = 4
    g = (np.arange(n * sub) + 0.5) / sub - n / 2.0
    xx, yy = np.meshgrid(g, g)
    inside = (xx ** 2 + yy ** 2 <= r * r).astype(float)
    frac = inside.reshape(n, sub, n, sub).mean(axis=(1, 3))
    return frac * s1 + (1.0 - frac) * s2


def hs_bounds(f1, s1, s2, d):
    """!
    @brief Hashin-Shtrikman bounds, Milton equation 7.10 (phase labels with s1 > s2).
    @param f1 Volume fraction of phase 1 (the better conductor).
    @param s1 Conductivity of phase 1.
    @param s2 Conductivity of phase 2 (s2 < s1).
    @param d Dimension, 2 or 3.
    @return Tuple (lower, upper).
    """
    f2 = 1.0 - f1
    upper = s1 + d * f2 * s1 * (s2 - s1) / (d * s1 + f1 * (s2 - s1))
    lower = s2 + d * f1 * s2 * (s1 - s2) / (d * s2 + f2 * (s1 - s2))
    return lower, upper


def bruggeman(f1, s1, s2, d):
    """!
    @brief Bruggeman effective-medium conductivity, the positive root of f1 (s1 - s)/(s1 + (d - 1) s) + f2 (s2 - s)/(s2 + (d - 1) s) = 0.
    @details For d = 3 this is Milton equation 10.31 with solution 10.32; for d = 2 the same step applied to the dilute cylinders of equation 7.9.
    @param f1 Volume fraction of phase 1.
    @param s1 Conductivity of phase 1.
    @param s2 Conductivity of phase 2.
    @param d Dimension, 2 or 3.
    @return float effective conductivity.
    """
    f2 = 1.0 - f1
    m = d - 1.0
    # Multiplying by both denominators and collecting powers of s gives: f1 (s1 - s)(s2 + m s) + f2 (s2 - s)(s1 + m s) = 0  ->  -m s^2 + [f1 (m s1 - s2) + f2 (m s2 - s1)] s + s1 s2 = 0
    b = f1 * (m * s1 - s2) + f2 * (m * s2 - s1)
    roots = np.roots([-m, b, s1 * s2])
    return float(max(r.real for r in roots))
