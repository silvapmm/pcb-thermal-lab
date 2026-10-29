#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file plate2d.py
@brief Steady laminar natural convection of a finite isothermal vertical plate in open air, solved as the full two-dimensional Boussinesq problem (stream function and vorticity).
@details Imports nothing from pcbthermal. An independent check of the finite-height behaviour of the plate correlations, with no leading-edge or turbulence model:

         * the plate (height L, zero thickness, isothermal at Tw) lies on the symmetry plane x = 0 of the half domain x >= 0; the plane outside the plate is a symmetry plane
           (psi = 0, vorticity 0, dT/dx = 0), so the problem is a thin plate with both faces identical and the air free to enter from the side, from below and to leave at the top;
         * lengths are scaled by L, temperature by (Tw - Tinf), velocities by alpha/L. u = dpsi/dy, v = -dpsi/dx, omega = dv/dx - du/dy, so Laplacian(psi) = -omega, and

               omega_t + u omega_x + v omega_y = Pr Laplacian(omega) + Ra Pr dT/dx,        T_t + u T_x + v T_y = Laplacian(T);

         * wall vorticity by Thom's formula omega_w = -2 psi_1 / dx1^2; far boundaries: T = 0, omega = 0 at the side and the bottom (inflow), zero normal derivative of psi
           everywhere on them (the entrained air is free), zero normal derivative of T and omega at the top (outflow);
         * stretched grids (clustered at the plate and at its two ends), pseudo-time marching to the steady state: implicit diffusion with factorised matrices, explicit
           central convection.

         The mean Nusselt number is Nu = integral over the plate of -dT/dx dy (one-sided second-order derivative at the wall), h = Nu k / L.
"""

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import splu


def stretch_wall(n, length, first):
    """!
    @brief Geometric grid from 0 to `length` with the first cell equal to `first` (clustered at 0).
    @param n Number of cells.
    @param length Total length.
    @param first Size of the first cell.
    @return numpy.ndarray of n+1 nodes.
    """
    from scipy.optimize import brentq
    # ratio r: first * (r^n - 1)/(r - 1) = length
    f = lambda r: first * (r ** n - 1.0) / (r - 1.0) - length
    r = brentq(f, 1.0 + 1e-9, 2.0) if f(1.0 + 1e-9) < 0 else 1.0 + 1e-9
    return np.concatenate([[0.0], np.cumsum(first * r ** np.arange(n))])


def make_grid(nx, ny_plate, ny_below, ny_above, width, below, above, dx0, dy_end):
    """!
    @brief The nonuniform grid: x clustered at the plate, y clustered at the two ends of the plate.
    @param nx Cells in x (0 to width).
    @param ny_plate Cells along the plate (0 to 1).
    @param ny_below Cells below the plate.
    @param ny_above Cells above the plate.
    @param width Domain width (in plate heights).
    @param below Domain extent below the leading edge.
    @param above Domain extent above the top edge.
    @param dx0 First cell off the plate.
    @param dy_end Cell size at the two ends of the plate.
    @return tuple (x, y, j0, j1): node arrays and the indices of y = 0 and y = 1.
    """
    x = stretch_wall(nx, width, dx0)
    yp = 0.5 * (1.0 + np.tanh(1.7 * (np.linspace(0, 1, ny_plate + 1) * 2 - 1)) / np.tanh(1.7))
    yb = -stretch_wall(ny_below, below, max(dy_end, yp[1]))[::-1][:-1]
    ya = 1.0 + stretch_wall(ny_above, above, max(dy_end, yp[-1] - yp[-2]))[1:]
    y = np.concatenate([yb, yp, ya])
    return x, y, len(yb), len(yb) + ny_plate


def _d2_weights(h_minus, h_plus):
    """!
    @brief Three-point second-derivative weights on a nonuniform grid.
    @param h_minus Distance to the previous node.
    @param h_plus Distance to the next node.
    @return tuple (w_minus, w_zero, w_plus).
    """
    s = h_minus + h_plus
    return 2.0 / (h_minus * s), -2.0 / (h_minus * h_plus), 2.0 / (h_plus * s)


def _d1_weights(h_minus, h_plus):
    """!
    @brief Three-point first-derivative weights on a nonuniform grid.
    @param h_minus Distance to the previous node.
    @param h_plus Distance to the next node.
    @return tuple (w_minus, w_zero, w_plus).
    """
    s = h_minus + h_plus
    return -h_plus / (h_minus * s), (h_plus - h_minus) / (h_minus * h_plus), h_minus / (h_plus * s)


class Plate2D:
    """!
    @brief The steady 2D plate problem on a fixed grid, marched in pseudo-time.
    """

    def __init__(self, ra, pr=0.71, nx=90, ny_plate=80, ny_below=30, ny_above=60, width=3.0, below=1.5, above=3.0, dx0=1.5e-3, dy_end=2e-3):
        """!
        @brief Build the grid and the factorised implicit operators.
        @param ra Rayleigh number of the plate height.
        @param pr Prandtl number.
        @param nx Cells in x.
        @param ny_plate Cells along the plate.
        @param ny_below Cells below the plate.
        @param ny_above Cells above the plate.
        @param width Domain width in plate heights.
        @param below Extent below the plate in plate heights.
        @param above Extent above the plate in plate heights.
        @param dx0 First cell off the plate (plate heights).
        @param dy_end Cell size at the ends of the plate (plate heights).
        @return None.
        """
        self.ra, self.pr = float(ra), float(pr)
        self.x, self.y, self.j0, self.j1 = make_grid(nx, ny_plate, ny_below, ny_above, width, below, above, dx0, dy_end)
        self.nx, self.ny = len(self.x), len(self.y)
        n = self.nx * self.ny
        self.psi = np.zeros((self.nx, self.ny))
        self.om = np.zeros((self.nx, self.ny))
        self.T = np.zeros((self.nx, self.ny))
        self.T[0, self.j0:self.j1 + 1] = 1.0
        self.dt = None
        self.relax = 0.3                                                          # under-relaxation of the wall vorticity
        self._build_static()
        self.n = n

    def idx(self, i, j):
        """!
        @brief Flat index of node (i, j).
        @param i Index in x.
        @param j Index in y.
        @return int.
        """
        return i * self.ny + j

    def _build_static(self):
        """!
        @brief Precompute the derivative weights and factorise the stream-function Poisson matrix.
        @return None.
        """
        x, y, nx, ny = self.x, self.y, self.nx, self.ny
        self.hx_m = np.diff(x)[:-1]; self.hx_p = np.diff(x)[1:]
        self.hy_m = np.diff(y)[:-1]; self.hy_p = np.diff(y)[1:]
        self.wx1 = np.array(_d1_weights(self.hx_m, self.hx_p)); self.wx2 = np.array(_d2_weights(self.hx_m, self.hx_p))
        self.wy1 = np.array(_d1_weights(self.hy_m, self.hy_p)); self.wy2 = np.array(_d2_weights(self.hy_m, self.hy_p))
        self._poisson = self._assemble_poisson()

    def _laplacian_rows(self, rows, cols, vals, i, j, scale=1.0):
        """!
        @brief Append the 5-point Laplacian stencil of interior node (i, j) to coordinate lists.
        @param rows Row list.
        @param cols Column list.
        @param vals Value list.
        @param i Index in x (1..nx-2).
        @param j Index in y (1..ny-2).
        @param scale Multiplier of the stencil.
        @return None.
        """
        r = self.idx(i, j)
        a, b, c = self.wx2[:, i - 1]
        d, e, f = self.wy2[:, j - 1]
        rows += [r, r, r, r, r]
        cols += [self.idx(i - 1, j), self.idx(i + 1, j), self.idx(i, j - 1), self.idx(i, j + 1), r]
        vals += [scale * a, scale * c, scale * d, scale * f, scale * (b + e)]

    def _assemble_poisson(self):
        """!
        @brief LU factorisation of the Poisson problem Laplacian(psi) = -omega with psi = 0 on x = 0 and zero normal derivative on the other sides.
        @return SuperLU object.
        """
        nx, ny = self.nx, self.ny
        rows, cols, vals = [], [], []
        for i in range(nx):
            for j in range(ny):
                r = self.idx(i, j)
                if i == 0:
                    rows.append(r); cols.append(r); vals.append(1.0)                  # psi = 0 on the plate and on the symmetry plane
                elif i == nx - 1:
                    rows += [r, r]; cols += [r, self.idx(i - 1, j)]; vals += [1.0, -1.0]   # dpsi/dx = 0 at the side
                elif j == 0:
                    rows += [r, r]; cols += [r, self.idx(i, j + 1)]; vals += [1.0, -1.0]   # dpsi/dy = 0 at the bottom
                elif j == ny - 1:
                    rows += [r, r]; cols += [r, self.idx(i, j - 1)]; vals += [1.0, -1.0]   # dpsi/dy = 0 at the top
                else:
                    self._laplacian_rows(rows, cols, vals, i, j)
        return splu(sp.csc_matrix((vals, (rows, cols)), shape=(nx * ny, nx * ny)))

    def _assemble_implicit(self, diff, dt, kind):
        """!
        @brief LU factorisation of (I - dt diff Laplacian) with the boundary rows of the field.
        @param diff Diffusivity in plate units (1 for T, Pr for omega).
        @param dt Time step.
        @param kind "T" or "om".
        @return SuperLU object.
        """
        nx, ny, j0, j1 = self.nx, self.ny, self.j0, self.j1
        rows, cols, vals = [], [], []
        for i in range(nx):
            for j in range(ny):
                r = self.idx(i, j)
                if i == 0:
                    on_plate = j0 <= j <= j1
                    if kind == "T" and not on_plate:                                  # symmetry plane: dT/dx = 0
                        rows += [r, r]; cols += [r, self.idx(1, j)]; vals += [1.0, -1.0]
                    else:                                                             # plate T = 1, wall vorticity from psi, symmetry omega = 0
                        rows.append(r); cols.append(r); vals.append(1.0)
                elif i == nx - 1 or j == 0:
                    rows.append(r); cols.append(r); vals.append(1.0)                  # inflow: ambient T, no vorticity
                elif j == ny - 1:
                    rows += [r, r]; cols += [r, self.idx(i, j - 1)]; vals += [1.0, -1.0]   # outflow: zero normal derivative
                else:
                    rows.append(r); cols.append(r); vals.append(1.0)
                    self._laplacian_rows(rows, cols, vals, i, j, scale=-dt * diff)
        return splu(sp.csc_matrix((vals, (rows, cols)), shape=(nx * ny, nx * ny)))

    def _ddx(self, f):
        """!
        @brief Interior first derivative in x of a field.
        @param f Array (nx, ny).
        @return Array of the interior (nx-2, ny).
        """
        w = self.wx1
        return w[0][:, None] * f[:-2] + w[1][:, None] * f[1:-1] + w[2][:, None] * f[2:]

    def _ddy(self, f):
        """!
        @brief Interior first derivative in y of a field.
        @param f Array (nx, ny).
        @return Array of the interior (nx, ny-2).
        """
        w = self.wy1
        return w[0][None, :] * f[:, :-2] + w[1][None, :] * f[:, 1:-1] + w[2][None, :] * f[:, 2:]

    def _velocities(self):
        """!
        @brief u = dpsi/dy and v = -dpsi/dx at every node (one-sided at the edges).
        @return tuple (u, v).
        """
        psi = self.psi
        u = np.zeros_like(psi); v = np.zeros_like(psi)
        u[:, 1:-1] = self._ddy(psi)
        v[1:-1, :] = -self._ddx(psi)
        return u, v

    def set_dt(self, dt):
        """!
        @brief Choose the pseudo-time step and factorise the implicit operators.
        @param dt Time step.
        @return None.
        """
        self.dt = dt
        self._lu_T = self._assemble_implicit(1.0, dt, "T")
        self._lu_om = self._assemble_implicit(self.pr, dt, "om")

    def step(self):
        """!
        @brief One pseudo-time step: explicit convection and buoyancy, implicit diffusion, then the Poisson solve for psi and the wall vorticity.
        @return float, largest change of T in the step.
        """
        nx, ny, dt = self.nx, self.ny, self.dt
        u, v = self._velocities()
        T, om = self.T, self.om
        # Convection and buoyancy on interior nodes (central differences)
        rhs_T = T.copy(); rhs_om = om.copy()
        Tx = np.zeros_like(T); Ty = np.zeros_like(T); ox = np.zeros_like(T); oy = np.zeros_like(T)
        Tx[1:-1, :] = self._ddx(T); Ty[:, 1:-1] = self._ddy(T)
        ox[1:-1, :] = self._ddx(om); oy[:, 1:-1] = self._ddy(om)
        inner = (slice(1, nx - 1), slice(1, ny - 1))
        rhs_T[inner] = T[inner] - dt * (u * Tx + v * Ty)[inner]
        rhs_om[inner] = om[inner] - dt * (u * ox + v * oy)[inner] + dt * self.ra * self.pr * Tx[inner]
        # Boundary values of the right-hand sides
        rhs_T[0, self.j0:self.j1 + 1] = 1.0
        rhs_T[0, :self.j0] = 0.0; rhs_T[0, self.j1 + 1:] = 0.0
        rhs_T[-1, :] = 0.0; rhs_T[:, 0] = 0.0; rhs_T[:, -1] = 0.0
        rhs_om[0, :] = 0.0; rhs_om[-1, :] = 0.0; rhs_om[:, 0] = 0.0; rhs_om[:, -1] = 0.0
        wall = -2.0 * self.psi[1, self.j0:self.j1 + 1] / (self.x[1] - self.x[0]) ** 2                      # Thom
        rhs_om[0, self.j0:self.j1 + 1] = self.relax * wall + (1.0 - self.relax) * om[0, self.j0:self.j1 + 1]   # under-relaxed: the lagged wall vorticity is unstable otherwise
        Tn = self._lu_T.solve(rhs_T.ravel()).reshape(nx, ny)
        omn = self._lu_om.solve(rhs_om.ravel()).reshape(nx, ny)
        rhs_psi = -omn.copy()
        rhs_psi[0, :] = 0.0; rhs_psi[-1, :] = 0.0; rhs_psi[:, 0] = 0.0; rhs_psi[:, -1] = 0.0
        self.psi = self._poisson.solve(rhs_psi.ravel()).reshape(nx, ny)
        change = float(np.max(np.abs(Tn - T)))
        self.T, self.om = Tn, omn
        return change

    def nusselt_local(self):
        """!
        @brief Local Nusselt number -dT/dx on the plate nodes, second-order one-sided.
        @return tuple (y on the plate, Nu local).
        """
        x = self.x
        h1, h2 = x[1] - x[0], x[2] - x[1]
        # second-order one-sided derivative at x = 0 on a nonuniform grid
        w0 = -(2.0 * h1 + h2) / (h1 * (h1 + h2)); w1 = (h1 + h2) / (h1 * h2); w2 = -h1 / (h2 * (h1 + h2))
        g = w0 * self.T[0] + w1 * self.T[1] + w2 * self.T[2]
        return self.y[self.j0:self.j1 + 1], -g[self.j0:self.j1 + 1]

    def nusselt_mean(self):
        """!
        @brief Mean Nusselt number of the plate (trapezoid rule over the local values).
        @return float.
        """
        y, nu = self.nusselt_local()
        return float(np.trapezoid(nu, y))

    def energy_balance(self):
        """!
        @brief Heat leaving through the outer boundaries of the domain (convective plus conductive) divided by the heat leaving the plate: 1 for a conservative converged solution.
        @details top: integral of (v T - dT/dy) dx; side: integral of (u T - dT/dx) dy; bottom: integral of -(v T - dT/dy) dx (all one-sided second-order differences at the boundary).
        @return float ratio (outer boundaries / plate).
        """
        u, v = self._velocities()
        x, y, T = self.x, self.y, self.T
        # one-sided second-order normal derivatives
        def onesided(f, h1, h2):
            """!
            @brief Second-order derivative at the end node of a nonuniform line, pointing into the domain (f[0], f[1], f[2], steps h1 then h2).
            @param f Array of three values.
            @param h1 First step.
            @param h2 Second step.
            @return float.
            """
            return -(2 * h1 + h2) / (h1 * (h1 + h2)) * f[0] + (h1 + h2) / (h1 * h2) * f[1] - h1 / (h2 * (h1 + h2)) * f[2]
        ny, nx = self.ny, self.nx
        dy1, dy2 = y[-1] - y[-2], y[-2] - y[-3]
        top = np.array([v[i, -1] * T[i, -1] - (-onesided(T[i, ::-1][:3], dy1, dy2)) for i in range(nx)])    # dT/dy at the top, outward derivative reversed
        side = np.array([u[-1, j] * T[-1, j] - (-onesided(T[::-1, j][:3], x[-1] - x[-2], x[-2] - x[-3])) for j in range(ny)])
        bot = np.array([-(v[i, 0] * T[i, 0] - onesided(T[i, :3], y[1] - y[0], y[2] - y[1])) for i in range(nx)])
        q = np.trapezoid(top, x) + np.trapezoid(side, y) + np.trapezoid(bot, x)
        return float(q / self.nusselt_mean())

    def run(self, max_steps=60000, check=500, tol=2e-5, dt=None, verbose=False):
        """!
        @brief March to the steady state.
        @param max_steps Maximum number of steps.
        @param check Steps between convergence checks of the mean Nusselt number.
        @param tol Relative change of the mean Nusselt number between two checks that counts as converged.
        @param dt Time step (default from the buoyancy velocity scale).
        @param verbose Print the history.
        @return dict with nu, steps, converged and the history.
        """
        if dt is None:
            vscale = np.sqrt(self.ra / self.pr) * 0.5                               # velocity scale alpha/L * sqrt(Ra/Pr), times a typical 0.3-0.5
            dt = 0.4 * min(self.x[1] - self.x[0], self.y[self.j0 + 1] - self.y[self.j0]) / max(vscale, 1.0)
        self.set_dt(dt)
        hist = []
        last = None
        for k in range(1, max_steps + 1):
            self.step()
            if k % check == 0:
                nu = self.nusselt_mean()
                hist.append((k, nu))
                if verbose:
                    print(k, nu)
                if last is not None and abs(nu - last) < tol * abs(nu):
                    return {"nu": nu, "steps": k, "converged": True, "history": hist}
                last = nu
        return {"nu": self.nusselt_mean(), "steps": max_steps, "converged": False, "history": hist}
