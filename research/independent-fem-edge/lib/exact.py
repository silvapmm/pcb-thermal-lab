#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file exact.py
@brief Closed-form solutions the finite-element solver is checked against: the 1D series stack with a source in one slab, the 1D fin with a
       Robin end, and the 2D thin sheet with Robin walls on two sides and a rectangular source (own derivations, independent of pcbthermal).
@details Nothing here imports the program: the eigenvalues of the Robin walls are found by bisection in this file, the series are summed here.
         SI units.
"""

import numpy as np


def series_stack(t, k, h_top, h_bottom, q_area):
    """!
    @brief 1D stack of slabs with a uniform volumetric source in the first slab and films on both faces (ambient 0).
    @details Heat flux in +z (downwards) `phi(z) = -q_u + g z` inside the source slab (g = q_area / t[0]); the top surface is at `q_u / h_top`, the
             bottom at `q_d / h_bottom`, with `q_u + q_d = q_area` and the series resistance of the slabs below the source in between.
    @param t Slab thicknesses from the top (m).
    @param k Slab conductivities (W/mK).
    @param h_top Top film W/m2K.
    @param h_bottom Bottom film W/m2K.
    @param q_area Heat generated in the first slab per unit area, W/m2.
    @return dict: z (interface depths, m), T (temperature at every interface, K, from the top surface down), q_up, q_down (W/m2), T_of (callable z -> T).
    """
    t, k = np.asarray(t, float), np.asarray(k, float)
    r_below = float((t[1:] / k[1:]).sum())
    g = q_area / t[0]
    # q_u / h_top + (q_u t0 - g t0^2 / 2) / k0 = (q - q_u) (r_below + 1 / h_bottom)
    rb = r_below + 1.0 / h_bottom
    q_u = (q_area * rb + g * t[0] ** 2 / (2 * k[0])) / (1.0 / h_top + t[0] / k[0] + rb)
    q_d = q_area - q_u
    z = np.concatenate([[0.0], np.cumsum(t)])
    T = np.empty(z.size)
    T[0] = q_u / h_top
    T[1] = T[0] + (q_u * t[0] - g * t[0] ** 2 / 2) / k[0]
    for i in range(1, t.size):
        T[i + 1] = T[i] - q_d * t[i] / k[i]

    def T_of(zz):
        """!
        @brief Temperature at depth zz.
        @param zz Depth (m), scalar or array.
        @return Temperature.
        """
        zz = np.asarray(zz, float)
        out = np.interp(zz, z, T)
        inside = zz <= t[0]
        out = np.where(inside, T[0] + (q_u * zz - g * zz ** 2 / 2) / k[0], out)
        return out
    return {"z": z, "T": T, "q_up": q_u, "q_down": q_d, "T_of": T_of}


def fin_robin(S, H, L, a, q0, h_end):
    """!
    @brief 1D sheet (fin) of conductance S with uniform loss H per area, insulated at x = 0, a Robin end at x = L, a uniform source q0 (W/m2) on [0, a].
    @details `S T'' - H T = -q0` on [0, a], `S T'' - H T = 0` on [a, L]; T'(0) = 0; `-S T'(L) = h_end T(L)` (h_end in W/mK: film times the edge
             thickness). m = sqrt(H / S).
    @param S Sheet conductance W/K (k t).
    @param H Loss per unit area W/m2K (h_top + h_bottom).
    @param L Length (m).
    @param a End of the source (m).
    @param q0 Source per unit area W/m2.
    @param h_end Edge conductance per unit length W/mK (h_side times the sheet thickness).
    @return callable x -> T (x scalar or array).
    """
    m = np.sqrt(H / S)
    p = q0 / H
    # scaled forms that never overflow: region 1 T = A (e^{-m(a-x)} + e^{-m(a+x)}) + p; region 2 T = C (e^{-m(x-a)} + rho e^{-m(2L-a-x)}) with the
    # reflection coefficient of the Robin end rho = (S m - h_end) / (S m + h_end)
    rho = (S * m - h_end) / (S * m + h_end)
    ea, eb = np.exp(-2 * m * a), np.exp(-2 * m * (L - a))
    # continuity of T and T' at x = a
    M = np.array([[1 + ea, -(1 + rho * eb)], [m * (1 - ea), m * (1 - rho * eb)]])
    A, C = np.linalg.solve(M, np.array([-p, 0.0]))

    def T(x):
        """!
        @brief Temperature at x.
        @param x Coordinate (m).
        @return Temperature.
        """
        x = np.asarray(x, float)
        r1 = A * (np.exp(-m * np.abs(a - x)) + np.exp(-m * (a + x))) + p
        r2 = C * (np.exp(-m * np.abs(x - a)) + rho * np.exp(-m * (2 * L - a - x)))
        return np.where(x <= a, r1, r2)
    return T


def robin_eigen(W, beta, n_modes):
    """!
    @brief Eigenvalues mu_n of cos(mu y) on [0, W] with an insulated wall at y = 0 and a Robin wall at y = W: mu tan(mu W) = beta.
    @param W Width (m).
    @param beta Robin parameter h_end / S (1/m); 0 gives the cosines n pi / W.
    @param n_modes Number of modes.
    @return numpy.ndarray of mu_n (1/m), n = 0 .. n_modes - 1.
    """
    if beta <= 0:
        return np.arange(n_modes) * np.pi / W
    mu = np.empty(n_modes)
    for n in range(n_modes):
        lo, hi = n * np.pi / W + 1e-14, (n + 0.5) * np.pi / W - 1e-14      # one root per branch of tan
        f = lambda x: x * np.tan(x * W) - beta                             # noqa: E731
        for _ in range(200):
            mid = 0.5 * (lo + hi)
            if f(mid) > 0:
                hi = mid
            else:
                lo = mid
        mu[n] = 0.5 * (lo + hi)
    return mu


def sheet_robin_2d(S, H, L, W, rect, q0, h_end_x, h_end_y, n_modes=400):
    """!
    @brief 2D thin sheet [0, L] x [0, W]: insulated at x = 0 and y = 0, Robin walls at x = L and y = W, a uniform source q0 on a rectangle.
    @details Expansion in the Robin eigenfunctions cos(mu_n y) of the y direction (norm N_n = W/2 + sin(2 mu W)/(4 mu)); every mode is the 1D
             problem of `fin_robin` with the loss H replaced by H + S mu_n^2 and the source scaled by the projection of the source window
             [y0, y1]: (sin(mu y1) - sin(mu y0)) / mu / N_n (mode 0 with mu = 0: (y1 - y0) / W when beta_y = 0).
    @param S Sheet conductance W/K.
    @param H Loss per unit area W/m2K.
    @param L Length in x (m).
    @param W Width in y (m).
    @param rect Source rectangle (x0, y0, x1, y1) with x0 = 0 (m).
    @param q0 Source per unit area W/m2.
    @param h_end_x Edge conductance per unit length at x = L (W/mK).
    @param h_end_y Edge conductance per unit length at y = W (W/mK).
    @param n_modes Modes in y.
    @return callable (x, y) -> T, arrays broadcast.
    """
    x0, y0, x1, y1 = rect
    assert abs(x0) < 1e-15, "the source must start at x = 0"
    mu = robin_eigen(W, h_end_y / S, n_modes)
    parts = []
    for n, mn in enumerate(mu):
        if mn == 0.0:
            coef = (y1 - y0) / W
        else:
            norm = W / 2 + np.sin(2 * mn * W) / (4 * mn)
            coef = (np.sin(mn * y1) - np.sin(mn * y0)) / mn / norm
        parts.append((mn, fin_robin(S, H + S * mn ** 2, L, x1, q0 * coef, h_end_x)))

    def T(x, y):
        """!
        @brief Temperature at (x, y).
        @param x Coordinate (m).
        @param y Coordinate (m).
        @return Temperature.
        """
        x, y = np.broadcast_arrays(np.asarray(x, float), np.asarray(y, float))
        out = np.zeros(x.shape)
        for mn, f in parts:
            out += f(x) * np.cos(mn * y)
        return out
    return T
