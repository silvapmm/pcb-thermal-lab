#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file column1d.py
@brief An independent one-dimensional transient solver through the thickness of a stack, with the thick layers resolved (the reference of the transient surface read-out).
@details Finite volumes in z on a stack of layers (thickness, conductivity, volumetric heat capacity, number of cells with a geometric grading towards both faces of the layer), a heat flux q(t)
         entering the top face, a film h to the ambient under the bottom face and an insulated top outside the flux (the flux covers the whole face: the problem is exactly one-dimensional). Time:
         BDF2 (second order, damps the ringing that Crank-Nicolson keeps after a jump of the flux) with a constant step, the first step implicit Euler, the matrices factored once (tridiagonal). The surface temperature is the first cell plus q dz / (2 k) (the flux crosses half a cell); the layer mean is the
         thickness-weighted mean of its cells. Imports nothing from pcbthermal. Check: tests/test_column1d.py (steady state against the series resistance, the half-space short-time law, energy balance).
"""

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla


def grid(stack):
    """!
    @brief Cells of the stack.
    @param stack List of (thickness m, k W/mK, rho c J/m3K, cells) from the top down.
    @return tuple (dz, k, rc, layer index of every cell) as arrays.
    """
    dz, k, rc, lid = [], [], [], []
    for i, (t, kk, c, n) in enumerate(stack):
        # Geometric grading: the cells are smallest at the two faces (ratio 1.15 from each face towards the middle), summing to t
        m = n // 2
        w = np.array([1.15 ** j for j in range(m)] + ([1.15 ** (m - 1)] if n % 2 else []) + [1.15 ** j for j in range(m - 1, -1, -1)])
        w = w if n > 1 else np.array([1.0])
        d = t * w / w.sum()
        dz += list(d)
        k += [kk] * len(d)
        rc += [c] * len(d)
        lid += [i] * len(d)
    return np.array(dz), np.array(k), np.array(rc), np.array(lid)


def solve(stack, h_bottom, q_of_t, t_end, dt):
    """!
    @brief Integrate the stack in time.
    @param stack List of (thickness m, k W/mK, rho c J/m3K, cells).
    @param h_bottom Film under the bottom face in W/m2K (a series of the half bottom cell is included).
    @param q_of_t Function of time returning the flux in W/m2 entering the top face.
    @param t_end Final time in s.
    @param dt Constant time step in s.
    @return dict with t (steps+1), surf (top face rise), mean (list per layer of the thickness-weighted mean rise), bottom (bottom face rise), q (the flux at every step), balance (energy residual, relative), z (cell centres, m), x_end (rise of the cells at the end), dz.
    """
    dz, k, rc, lid = grid(stack)
    n = len(dz)
    # Conductance between the cell i and i+1 (per m2): the two half cells in series
    g = 1.0 / (dz[:-1] / (2 * k[:-1]) + dz[1:] / (2 * k[1:]))
    gb = 1.0 / (1.0 / h_bottom + dz[-1] / (2 * k[-1]))
    main = np.zeros(n)
    main[:-1] += g
    main[1:] += g
    main[-1] += gb
    K = sp.diags([-g, main, -g], [-1, 0, 1], format="csc")
    C = sp.diags(rc * dz, format="csc")
    steps = int(round(t_end / dt))
    lu1 = spla.splu((C / dt + K).tocsc())                  # first step: implicit Euler
    lu2 = spla.splu((1.5 * C / dt + K).tocsc())            # then BDF2: (3 C x_{n+1} - 4 C x_n + C x_{n-1}) / (2 dt) + K x_{n+1} = q_{n+1}
    x = np.zeros(n)
    x_old = np.zeros(n)
    t = np.arange(steps + 1) * dt
    q = np.array([q_of_t(tt) for tt in t])
    surf, bottom = np.zeros(steps + 1), np.zeros(steps + 1)
    means = [np.zeros(steps + 1) for _ in stack]
    weights = [(dz * (lid == i)) / (dz * (lid == i)).sum() for i in range(len(stack))]
    e_in = 0.0
    e_out = 0.0
    cdz = rc * dz
    for s in range(steps):
        rhs_q = np.zeros(n)
        rhs_q[0] = q[s + 1]
        if s == 0:
            x_new = lu1.solve(cdz * x / dt + rhs_q)
        else:
            x_new = lu2.solve(cdz * (4.0 * x - x_old) / (2.0 * dt) + rhs_q)
        e_in += 0.5 * (q[s] + q[s + 1]) * dt
        e_out += 0.5 * gb * (x[-1] + x_new[-1]) * dt
        x_old, x = x, x_new
        surf[s + 1] = x[0] + q[s + 1] * dz[0] / (2 * k[0])
        bottom[s + 1] = x[-1]
        for i in range(len(stack)):
            means[i][s + 1] = weights[i] @ x
    stored_end = float((rc * dz * x).sum())
    return {"t": t, "surf": surf, "mean": means, "bottom": bottom, "q": q, "balance": abs(e_in - e_out - stored_end) / max(e_in, 1e-300), "z": np.cumsum(dz) - dz / 2.0, "x_end": x, "dz": dz, "k": [s[1] for s in stack], "t_layer": [s[0] for s in stack]}
