#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file vertical_plate.py
@brief Independent solver of the conjugate problem of Lee and Yovanovich (1989): a thin vertical plate with flush strip heat sources, conduction along the plate, laminar natural convection
       on the face and radiation to the surroundings. Nothing of the program is imported (NumPy and SciPy only).
@details Solid side (the paper's section "Solid-Side Model", equations 7 to 11): the plate is symmetric about its mid-plane and thin (Biot number 0.016 at most, equation 14), so one half
         thickness t carries a one-dimensional conduction along the height z,
             k_s t T'' = q_conv(z) + q_rad(z) - q_p(z),      T'(0) = T'(L) = 0,
         q_p being the heat flux that enters the front face under a strip (the half of the generation of the whole plate), q_rad = eps sigma (T^4 - T_inf^4).
         Fluid side: the paper uses the integral model of Lee (1988), which was not obtained. Here the boundary layer equations (1) to (3) of the paper (continuity, momentum with the
         Boussinesq term, energy; constant properties) are solved by a marching finite-difference scheme from the leading edge z = 0 (bottom) for the wall temperature T_w(z) of the
         solid iteration, so that the fluid side is an independent numerical solution of the same equations and not a copy of the paper's model.
         The coupling is the paper's iteration (steps 4 to 7): h_i = q_conv / (T_w - T_f) from the fluid side, the solid solved with that h and the radiation, repeated until the wall
         temperature settles.
         Tests (tests/): the boundary layer against the isothermal similarity solution (Nusselt), the solid with a uniform h against the closed form, the energy balance of the whole.
"""

import numpy as np
from scipy.linalg import solve_banded

SIGMA = 5.670374419e-8      # W/(m2 K4)
G = 9.80665                 # m/s2


def thomas(a, b, c, d):
    """!
    @brief Solve a tridiagonal system.
    @param a Sub-diagonal (a[0] unused).
    @param b Diagonal.
    @param c Super-diagonal (c[-1] unused).
    @param d Right-hand side.
    @return numpy.ndarray The solution.
    """
    ab = np.zeros((3, len(b)))
    ab[0, 1:] = c[:-1]
    ab[1] = b
    ab[2, :-1] = a[1:]
    return solve_banded((1, 1), ab, d)


class Fluid:
    """!
    @brief Constant-property air for the boundary layer (the properties the paper prints on p 265).
    """

    def __init__(self, nu=15.614e-6, k=0.0258, pr=0.72, t_inf=298.0):
        """!
        @brief Store the properties.
        @param nu Kinematic viscosity in m2/s.
        @param k Thermal conductivity in W/(m K).
        @param pr Prandtl number.
        @param t_inf Ambient fluid temperature in K (beta = 1 / t_inf, ideal gas).
        @return None.
        """
        self.nu, self.k, self.pr, self.t_inf = nu, k, pr, t_inf
        self.alpha = nu / pr
        self.beta = 1.0 / t_inf


def boundary_layer_flux(z, t_wall, fl, ny=260, y_max=0.06, stretch=7.0):
    """!
    @brief Local convective heat flux from the laminar natural-convection boundary layer on a vertical wall of given temperature, by marching from the leading edge.
    @param z Heights of the stations in m, increasing, z[0] > 0 (the leading edge is z = 0).
    @param t_wall Wall temperature at the stations in K.
    @param fl Fluid properties.
    @param ny Number of nodes across the layer.
    @param y_max Outer edge of the computational domain in m (the layer is a few mm thick).
    @param stretch Exponential clustering of the nodes at the wall.
    @return numpy.ndarray Heat flux from the wall to the fluid in W/m2 at the stations.
    """
    # a pre-march from the leading edge with geometrically spaced stations (wall at the temperature of the first station) removes the error of the starting profile, which a uniform
    # step of 0.25 mm would otherwise carry downstream (2 to 7 % low in the Nusselt number against the similarity solution)
    z = np.asarray(z, float)
    t_wall = np.asarray(t_wall, float)
    n_pre = 60
    z_pre = z[0] * np.geomspace(1e-4, 1.0, n_pre + 1)[:-1]
    z_all = np.r_[z_pre, z]
    t_all = np.r_[np.full(n_pre, t_wall[0]), t_wall]
    return _march(z_all, t_all, fl, ny, y_max, stretch)[n_pre:]


def _march(z, t_wall, fl, ny, y_max, stretch):
    """!
    @brief The marching itself (see boundary_layer_flux, which adds the geometric pre-march).
    @param z Stations in m.
    @param t_wall Wall temperature at the stations in K.
    @param fl Fluid properties.
    @param ny Nodes across the layer.
    @param y_max Outer edge in m.
    @param stretch Wall clustering.
    @return numpy.ndarray Wall heat flux in W/m2 at the stations.
    """
    s = np.linspace(0.0, 1.0, ny)
    y = y_max * (np.exp(stretch * s) - 1.0) / (np.exp(stretch) - 1.0)
    dy = np.diff(y)
    # starting profiles at the first station: a thin similarity-like exponential layer (the downstream solution forgets it; the first station is not used by the caller)
    z_prev = 0.0
    th0 = t_wall[0] - fl.t_inf
    delta0 = max(4.0 * (4.0 * fl.nu ** 2 * z[0] / (G * fl.beta * max(abs(th0), 1e-3) * fl.pr ** 0.5)) ** 0.25, 5 * y[1])
    u_old = 0.2 * np.sqrt(G * fl.beta * abs(th0) * z[0]) * (y / delta0) * np.exp(1.0 - y / delta0)
    u_old[0] = 0.0
    th_old = th0 * np.exp(-3.0 * y / delta0)
    v_old = np.zeros(ny)
    q = np.zeros(len(z))
    for i, zi in enumerate(z):
        dz = zi - z_prev
        th_w = t_wall[i] - fl.t_inf
        hm, hp = dy[:-1], dy[1:]
        wm = 2.0 / (hm * (hm + hp))
        wp = 2.0 / (hp * (hm + hp))
        first_m = -hp / (hm * (hm + hp))
        first_p = hm / (hp * (hm + hp))
        first_c = (hp - hm) / (hm * hp)
        # Patankar-Spalding marching: the convective coefficients come from the previous station (u_old, v_old), so each station is two linear tridiagonal solves, with no inner iteration
        # (an inner iteration on u and v at the station converged to a spurious thin-layer state, 5 to 9 times the Nusselt number, in a trial of this solver)
        uc, vc = u_old[1:-1], v_old[1:-1]
        a = vc * first_m - fl.alpha * wm
        b = uc / dz + vc * first_c + fl.alpha * (wm + wp)
        c = vc * first_p - fl.alpha * wp
        rhs = uc / dz * th_old[1:-1]
        rhs[0] -= a[0] * th_w
        th = np.zeros(ny)
        th[0] = th_w
        th[1:-1] = thomas(np.r_[0.0, a[1:]], b, np.r_[c[:-1], 0.0], rhs)
        a = vc * first_m - fl.nu * wm
        b = uc / dz + vc * first_c + fl.nu * (wm + wp)
        c = vc * first_p - fl.nu * wp
        rhs = uc / dz * u_old[1:-1] + G * fl.beta * th[1:-1]
        u = np.zeros(ny)
        u[1:-1] = thomas(np.r_[0.0, a[1:]], b, np.r_[c[:-1], 0.0], rhs)
        dudz = (u - u_old) / dz
        v = np.zeros(ny)
        v[1:] = -np.cumsum(0.5 * (dudz[1:] + dudz[:-1]) * dy)
        # wall flux from a three-point one-sided derivative on the non-uniform grid
        h1, h2 = dy[0], dy[1]
        dth = (-(2 * h1 + h2) / (h1 * (h1 + h2)) * th[0] + (h1 + h2) / (h1 * h2) * th[1] - h1 / (h2 * (h1 + h2)) * th[2])
        q[i] = -fl.k * dth
        u_old, th_old, v_old, z_prev = u, th, v, zi
    return q


def solve_plate(l_plate, t_half, k_s, strips, q_p, eps, fl, nz=386, tol=1e-3, relax=0.6, max_iter=200, two_faces=True):
    """!
    @brief The conjugate solution: wall temperature, convective and radiative flux along the plate.
    @param l_plate Plate height L in m.
    @param t_half Half thickness t in m.
    @param k_s Plate conductivity in W/(m K).
    @param strips List of (z_centre, width) in m of the flush strip sources.
    @param q_p Heat flux entering the front face under a strip in W/m2 (the half of the generation of the symmetric plate).
    @param eps Emissivity of the face (0 for no radiation).
    @param fl Fluid properties.
    @param nz Number of nodes along the plate.
    @param tol Convergence on the maximum change of the wall temperature in K.
    @param relax Under-relaxation of the temperature update.
    @param max_iter Outer iterations.
    @param two_faces Unused flag kept for clarity: the half plate is solved (symmetry), both faces behave alike.
    @return dict with z, t_wall (K), q_conv, q_rad, q_in (W/m2), iterations and the heat balance (strip input and the convective plus radiative output per unit width, W/m).
    """
    dz = l_plate / nz
    z = (np.arange(nz) + 0.5) * dz
    q_in = np.zeros(nz)
    for zc, w in strips:
        q_in[(z >= zc - w / 2.0) & (z <= zc + w / 2.0)] = q_p
    tw = fl.t_inf + 10.0 * np.ones(nz)
    kt = k_s * t_half / dz ** 2                      # conduction coefficient per node (W/m2/K)
    for it in range(max_iter):
        qc = boundary_layer_flux(z, tw, fl)
        h_c = qc / np.maximum(tw - fl.t_inf, 1e-6)
        h_r = eps * SIGMA * (tw ** 2 + fl.t_inf ** 2) * (tw + fl.t_inf)
        # solid: -kt (T_{i-1} - 2 T_i + T_{i+1}) + (h_c + h_r)(T_i - T_inf) = q_in
        main = (h_c + h_r) + 2.0 * kt
        main[0] -= kt
        main[-1] -= kt
        a = -kt * np.ones(nz)
        c = -kt * np.ones(nz)
        rhs = q_in + (h_c + h_r) * fl.t_inf
        new = thomas(a, main, c, rhs)
        diff = np.max(np.abs(new - tw))
        tw = tw + relax * (new - tw)
        if diff < tol:
            break
    qc = boundary_layer_flux(z, tw, fl)
    qr = eps * SIGMA * (tw ** 4 - fl.t_inf ** 4)
    return {"z": z, "t_wall": tw, "q_conv": qc, "q_rad": qr, "q_in": q_in, "iterations": it + 1, "last_change": diff,
            "heat_in": float(np.sum(q_in) * dz), "heat_out": float(np.sum(qc + qr) * dz)}
