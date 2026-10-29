#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file channel_bl.py
@brief Independent numerical solution of the natural convection between two vertical isothermal parallel plates (the Elenbaas channel), by marching.

@details The solver imports nothing from `pcbthermal`. It solves the boundary-layer form of the steady, laminar, constant-property (Boussinesq) equations of the
         symmetric channel, the formulation of Bodoia and Osterle (1962) as described by Teertstra, Culham and Yovanovich ("Comprehensive review of natural and
         mixed convection heat transfer models for circuit board arrays", the group's report): with x up the plates, y across the half channel (y = 0 on the plane of
         symmetry, y = a = b/2 at the wall), theta = (T - T0)/(Tw - T0) and q = p'/rho the pressure minus the hydrostatic pressure of the ambient air over rho,

             du/dx + dv/dy = 0
             u du/dx + v du/dy = -dq/dx + nu d2u/dy2 + g beta dT theta
             u dtheta/dx + v dtheta/dy = alpha d2theta/dy2

         The inlet is at rest air at T0 with a uniform entrance speed u0 and the pressure drop of the Bernoulli equation, q(0) = -u0^2 / 2; the exit is at the
         ambient pressure, q(L) = 0. The pressure q(x) does not depend on y (boundary-layer approximation); at every station dq/dx is the number that makes the mass flow
         across the half channel equal to u0 a. The entrance speed u0 is the unknown of a shooting problem (the pressure at the exit must be zero).
         The result depends only on the Prandtl number and on the channel (Elenbaas) Rayleigh number Ra_b = g beta dT b^4 Pr / (nu^2 L), the mean Nusselt number is
         Nu_b = h b / k with h the mean coefficient of one wall, (Tw - T0) the driving difference.

         Checks that the module's tests make: the limit Ra_b -> 0 (fully developed flow, Nu_b = Ra_b / 24, Bodoia and Osterle), the energy balance between the heat
         given by the wall and the enthalpy gained by the air, grid refinement in y and x.
         The momentum and energy equations are marched implicitly (first order in x) with coefficients taken from the previous station and two refinement passes per station.
"""

import numpy as np
from scipy.linalg import solve_banded
from scipy.optimize import brentq


def _tridiag(a, b, c, d):
    """!
    @brief Solve a tridiagonal system (Thomas algorithm).
    @param a Sub-diagonal (length n, a[0] unused).
    @param b Diagonal (length n).
    @param c Super-diagonal (length n, c[-1] unused).
    @param d Right-hand side (length n).
    @return Solution vector of length n.
    """
    ab = np.zeros((3, len(d)))
    ab[0, 1:] = c[:-1]                        # super-diagonal
    ab[1, :] = b
    ab[2, :-1] = a[1:]                        # sub-diagonal
    return solve_banded((1, 1), ab, d, check_finite=False)


def _y_grid(n, a, stretch):
    """!
    @brief Grid across the half channel, clustered towards the wall.
    @param n Number of intervals.
    @param a Half width of the channel (the wall is at y = a).
    @param stretch Clustering strength (0 = uniform).
    @return Array of n + 1 coordinates from 0 (symmetry plane) to a (wall).
    """
    s = np.linspace(0.0, 1.0, n + 1)
    if stretch <= 0.0:
        return a * s
    # Hyperbolic-tangent clustering at the wall: spacing at the wall about a * (1 - tanh(stretch))-ish of the uniform one
    return a * (1.0 + np.tanh(stretch * (s - 1.0)) / np.tanh(stretch))


def _d1_d2(y):
    """!
    @brief Finite-difference weights on a non-uniform grid for the first and second derivative at the interior nodes (three points).
    @param y Node coordinates.
    @return Tuple of arrays (w1m, w1c, w1p, w2m, w2c, w2p) for nodes 1..n-1.
    """
    hm = y[1:-1] - y[:-2]
    hp = y[2:] - y[1:-1]
    w1m = -hp / (hm * (hm + hp))
    w1p = hm / (hp * (hm + hp))
    w1c = (hp - hm) / (hm * hp)
    w2m = 2.0 / (hm * (hm + hp))
    w2p = 2.0 / (hp * (hm + hp))
    w2c = -2.0 / (hm * hp)
    return w1m, w1c, w1p, w2m, w2c, w2p


def solve(ra_b, pr=0.71, n_y=120, n_x=400, stretch=2.0, x_ratio=1.04, u0_bracket=None, return_fields=False, u0_fixed=None, trace=None):
    """!
    @brief Solve the symmetric isothermal channel for a given channel Rayleigh number.
    @details Units are those of a nondimensional problem: width b = 1, kinematic viscosity nu = 1, g beta dT = 1 (so the length of the channel is L = Pr / Ra_b).
             The x grid is geometric (first step very small, because the boundary layers start with infinite gradients at the inlet).
    @param ra_b Channel Rayleigh number Ra_b = g beta dT b^4 Pr / (nu^2 L).
    @param pr Prandtl number.
    @param n_y Number of intervals across the half channel.
    @param n_x Number of steps along the channel.
    @param stretch Clustering of the y grid towards the wall.
    @param x_ratio Ratio of successive x steps (the first one is chosen so that the n_x steps add up to L).
    @param u0_bracket Optional (low, high) bracket of the entrance speed for the shooting.
    @param return_fields True to return also the fields at the exit and the local Nusselt number.
    @param u0_fixed If given, march with this entrance speed and skip the shooting (q_exit then shows the mismatch).
    @param trace Optional list that receives (x, cumulative wall heat, enthalpy, theta on the axis, theta at mid half-width) every 50 steps (debugging).
    @return Dict with nu_b (mean Nusselt number of one wall based on b), u0 (entrance speed), q_exit (pressure at exit, near 0), energy_residual (relative
            difference between the wall heat and the enthalpy gain), and, if asked, x, nu_local, y, u_exit, theta_exit.
    """
    nu, alpha = 1.0, 1.0 / pr
    b = 1.0
    a = 0.5 * b
    length = pr / ra_b                       # from Ra_b = g beta dT b^4 Pr / (nu^2 L) with b = nu = g beta dT = 1
    y = _y_grid(n_y, a, stretch)
    w1m, w1c, w1p, w2m, w2c, w2p = _d1_d2(y)
    dy = np.diff(y)
    # Geometric x grid: steps dx_k = dx0 r^k with the sum equal to L. The first step is the distance over which a boundary layer grows to about three wall cells
    # (delta^2 ~ alpha x / u0), so that the entrance region, where the wall flux is singular, is resolved; the ratio r is then found so that n_x steps reach L.
    h_wall = y[-1] - y[-2]
    u_ref = max(u0_bracket[1] if u0_bracket is not None else 0.1, 1e-3)
    dx0 = min(length / n_x, u_ref * (3.0 * h_wall) ** 2 / alpha * 0.05)
    if length / n_x <= dx0 * 1.0001:
        dxs = np.full(n_x, length / n_x)
    else:
        r = brentq(lambda rr: dx0 * np.expm1(n_x * np.log(rr)) / (rr - 1.0) - length, 1.0 + 1e-9, 1.5, xtol=1e-14)
        dxs = dx0 * r ** np.arange(n_x)

    def trap(f):
        """!
        @brief Trapezoid integral across the half channel.
        @param f Values at the nodes.
        @return Integral from y = 0 to the wall.
        """
        return float(np.sum(0.5 * (f[1:] + f[:-1]) * dy))

    def march(u0):
        """!
        @brief March from the inlet with the entrance speed u0 and give the exit pressure and the fields.
        @param u0 Entrance speed (uniform).
        @return Tuple (q_exit, x array, local Nusselt array, u at the exit, theta at the exit, wall heat integral, enthalpy gain).
        """
        nn = len(y)
        u = np.full(nn, u0)
        u[-1] = 0.0                          # no slip at the wall (the first station is the entrance plane itself)
        v = np.zeros(nn)
        th = np.zeros(nn)
        th[-1] = 1.0
        q = -0.5 * u0 * u0
        xs = [0.0]
        nus = []
        heat = 0.0
        flux_prev = None
        for k in range(n_x):
            dx = dxs[k]
            u_new, v_new, th_new = u.copy(), v.copy(), th.copy()
            p_grad = 0.0
            for _ in range(3):
                # ---- energy: u (th_new - th)/dx + v th_y = alpha th_yy, th(wall) = 1, symmetry at y = 0
                uu = u_new
                aa = np.zeros(nn)
                bb = np.ones(nn)
                cc = np.zeros(nn)
                dd = np.zeros(nn)
                # (coefficients of: u/dx th + v th_y - alpha th_yy = u/dx th_old)
                aa[1:-1] = -alpha * w2m + v_new[1:-1] * w1m
                cc[1:-1] = -alpha * w2p + v_new[1:-1] * w1p
                bb[1:-1] = uu[1:-1] / dx - alpha * w2c + v_new[1:-1] * w1c
                dd[1:-1] = uu[1:-1] / dx * th[1:-1]
                # symmetry: th_y = 0 via the mirror node: second-order one-sided with th[1]
                bb[0], cc[0], dd[0] = 1.0, -1.0, 0.0
                bb[-1], aa[-1], dd[-1] = 1.0, 0.0, 1.0
                th_new = _tridiag(aa, bb, cc, dd)
                # ---- momentum: u (u_new - u)/dx + v u_y = -P + nu u_yy + theta  (g beta dT = 1); solve for P = 0 and for the unit pressure gradient
                bb2 = np.ones(nn)
                aa2 = np.zeros(nn)
                cc2 = np.zeros(nn)
                aa2[1:-1] = -nu * w2m + v_new[1:-1] * w1m
                cc2[1:-1] = -nu * w2p + v_new[1:-1] * w1p
                bb2[1:-1] = u_new[1:-1] / dx - nu * w2c + v_new[1:-1] * w1c
                rhs_a = np.zeros(nn)
                rhs_a[1:-1] = u_new[1:-1] / dx * u[1:-1] + th_new[1:-1]
                rhs_b = np.zeros(nn)
                rhs_b[1:-1] = -1.0
                bb2[0], cc2[0] = 1.0, -1.0
                bb2[-1] = 1.0
                ua = _tridiag(aa2, bb2, cc2, rhs_a)
                ub = _tridiag(aa2, bb2, cc2, rhs_b)
                # mass flow of the half channel fixed at u0 a
                p_grad = (u0 * a - trap(ua)) / trap(ub)
                u_try = ua + p_grad * ub
                # continuity: v(y) = - integral_0^y du/dx dy'  (backward difference in x)
                dudx = (u_try - u) / dx
                v_try = np.zeros(nn)
                v_try[1:] = -np.cumsum(0.5 * (dudx[1:] + dudx[:-1]) * dy)
                u_new, v_new = u_try, v_try
            q += p_grad * dx
            # wall flux (one-sided second order) and local Nusselt number Nu_b(x) = b * (-th_y at the wall)
            h1, h2 = y[-1] - y[-2], y[-2] - y[-3]
            dth = (th_new[-1] - th_new[-2]) / h1 + h1 * ((th_new[-1] - th_new[-2]) / h1 - (th_new[-2] - th_new[-3]) / h2) / (h1 + h2)
            flux = dth                                                    # -th_y at the wall in the sense of heat leaving the wall into the air
            heat += (0.5 * (flux + flux_prev) * dx) if flux_prev is not None else flux * dx
            flux_prev = flux
            xs.append(xs[-1] + dx)
            nus.append(b * flux)
            if trace is not None and (k % 50 == 0 or k == n_x - 1):
                trace.append((xs[-1], heat, trap(u_new * th_new) / alpha, float(th_new[0]), float(th_new[len(th_new) // 2])))
            u, v, th = u_new, v_new, th_new
        enthalpy = trap(u * th) / alpha                                    # (1/alpha) integral u th dy = heat leaving the wall per unit k dT
        return q, np.array(xs[1:]), np.array(nus), u, th, heat, enthalpy

    lo, hi = u0_bracket if u0_bracket is not None else (1e-3 * np.sqrt(1.0 / (1.0 + ra_b)), 0.2)

    def f(u0):
        """!
        @brief Exit pressure for an entrance speed, the function whose root is sought.
        @param u0 Entrance speed.
        @return Exit pressure q(L).
        """
        with np.errstate(all="ignore"):
            q_exit = march(u0)[0]
        # A too small entrance speed makes the marching blow up (the flow would be driven by a pressure that is not there); that side has q > 0
        return q_exit if np.isfinite(q_exit) and abs(q_exit) < 1e12 else 1e12

    if u0_fixed is not None:
        u0 = u0_fixed                       # a given entrance speed: no shooting (used by the tests and to inspect the pressure curve)
    else:
        # q(L) < 0 for an entrance speed that is too high (the exit pressure falls below ambient), > 0 for one that is too low
        flo, fhi = f(lo), f(hi)
        if flo * fhi > 0:
            # widen the bracket outwards once
            lo, hi = lo * 0.1, hi * 2.0
            flo, fhi = f(lo), f(hi)
        u0 = brentq(f, lo, hi, xtol=1e-12, rtol=1e-10)
    q_exit, xs, nus, u_e, th_e, heat, enth = march(u0)
    # Mean Nusselt number from the enthalpy gained by the air (conservative, exact for the discrete mass flow) and, as a check, from the wall flux
    nu_enth = b * enth / xs[-1]
    nu_wall = b * heat / xs[-1]
    out = {"nu_b": nu_enth, "nu_b_wall": nu_wall, "u0": u0, "q_exit": q_exit, "energy_residual": (heat - enth) / enth, "length": length}
    if return_fields:
        out.update({"x": xs, "nu_local": nus, "y": y, "u_exit": u_e, "theta_exit": th_e})
    return out
