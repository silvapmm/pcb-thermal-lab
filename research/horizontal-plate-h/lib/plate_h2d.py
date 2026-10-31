#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file plate_h2d.py
@brief Natural convection of a thin isothermal HORIZONTAL strip in open air, solved as the full two-dimensional Boussinesq problem (stream function and vorticity), upper and lower face at once.
@details Imports nothing from pcbthermal. Independent of the program and written for this investigation (the vertical solver of `research/plate-h-level/lib/plate2d.py`
         is the model of the numerics, not reused as code because the plate there lies on the symmetry line and here it lies across the buoyancy direction).

         * The strip has width 2 a and zero thickness, lies on y = 0 for |x| <= a and is isothermal at Tw. Lengths are scaled by L = a = A/P of the strip (area over perimeter of one
           face of a long board of width 2 a), temperature by (Tw - Tinf), velocities by alpha / L; the Rayleigh number is Ra = g beta (Tw - Tinf) L^3 / (nu alpha), so the Nusselt
           number Nu = h L / k is the one of the program's characteristic length A/P. The flow is taken as symmetric about x = 0 (half domain x >= 0): a steady symmetric
           solution may not be the physical one at high Ra (the plume of the upper face is unstable in reality), see the study.
         * u = d psi/dy, v = -d psi/dx, omega = dv/dx - du/dy, Laplacian(psi) = -omega,

               omega_t + u omega_x + v omega_y = Pr Laplacian(omega) + Ra Pr dT/dx,        T_t + u T_x + v T_y = Laplacian(T)

           (gravity along -y: the buoyancy term is the same as in the vertical solver, the plate is rotated instead of the gravity).
         * The plate nodes have psi = 0, T = 1 and two wall vorticities, one for the upper and one for the lower face (Thom: omega_w = -2 psi_1 / dy1^2), under-relaxed; the node at
           the tip of the plate gives the mean of the two to its neighbour on the plane y = 0.
         * Far boundaries: ambient T = 0 and omega = 0 at the side and the bottom, zero normal derivative of psi on all of them (free entrainment), zero normal derivative of T and omega at the
           top (outflow of the plume).
         * Stretched grids clustered at the plate (both faces) and at its tip; pseudo-time marching: implicit diffusion with factorised matrices, explicit central convection. The result is a
           steady state when the history converges, otherwise the mean over the last window of the march (the run reports the amplitude).
"""

import numpy as np
import scipy.sparse as sp
from scipy.optimize import brentq
from scipy.sparse.linalg import splu


def stretch(n, length, first):
    """!
    @brief Geometric grid from 0 to `length` with the first cell equal to `first`.
    @param n Number of cells.
    @param length Total length.
    @param first Size of the first cell (must be below length / n for growth).
    @return numpy.ndarray of n+1 nodes starting at 0.
    """
    if first >= length / n:
        return np.linspace(0.0, length, n + 1)
    f = lambda r: first * (r ** n - 1.0) / (r - 1.0) - length
    r = brentq(f, 1.0 + 1e-9, 3.0)
    return np.concatenate([[0.0], np.cumsum(first * r ** np.arange(n))])


def make_grid(n_in, n_out, n_up, n_dn, width, up, down, dx_tip, dy0):
    """!
    @brief The grid: x clustered at the tip of the plate (x = 1), y clustered at the plate on both sides.
    @param n_in Cells along the half plate (0 to 1).
    @param n_out Cells from the tip to the side boundary.
    @param n_up Cells above the plate.
    @param n_dn Cells below the plate.
    @param width Domain half width (in L).
    @param up Extent above the plate (in L).
    @param down Extent below the plate (in L).
    @param dx_tip Size of the cells at the tip.
    @param dy0 Size of the first cells above and below the plate.
    @return tuple (x, y, ip, j0): node arrays and the indices of the tip (x = 1) and of the plate row (y = 0).
    """
    xin = 1.0 - stretch(n_in, 1.0, dx_tip)[::-1]
    xout = 1.0 + stretch(n_out, width - 1.0, dx_tip)[1:]
    x = np.concatenate([xin, xout])
    ya = stretch(n_up, up, dy0)[1:]
    yb = -stretch(n_dn, down, dy0)[1:][::-1]
    y = np.concatenate([yb, [0.0], ya])
    return x, y, n_in, n_dn


def _w2(hm, hp):
    """!
    @brief Three-point second-derivative weights on a nonuniform grid.
    @param hm Distance to the previous node.
    @param hp Distance to the next node.
    @return tuple (w_minus, w_zero, w_plus).
    """
    s = hm + hp
    return 2.0 / (hm * s), -2.0 / (hm * hp), 2.0 / (hp * s)


def _w1(hm, hp):
    """!
    @brief Three-point first-derivative weights on a nonuniform grid.
    @param hm Distance to the previous node.
    @param hp Distance to the next node.
    @return tuple (w_minus, w_zero, w_plus).
    """
    s = hm + hp
    return -hp / (hm * s), (hp - hm) / (hm * hp), hm / (hp * s)


def one_sided(h1, h2):
    """!
    @brief Second-order one-sided first-derivative weights at a node with two further nodes at distances h1 and h1 + h2.
    @param h1 First step.
    @param h2 Second step.
    @return tuple of three weights (for f0, f1, f2).
    """
    return -(2 * h1 + h2) / (h1 * (h1 + h2)), (h1 + h2) / (h1 * h2), -h1 / (h2 * (h1 + h2))


class HorizontalStrip:
    """!
    @brief The steady 2D problem of a thin isothermal horizontal strip, marched in pseudo-time.
    """

    def __init__(self, ra, pr=0.71, n_in=48, n_out=32, n_up=56, n_dn=44, width=5.0, up=7.0, down=3.5, dx_tip=6e-3, dy0=2e-3, axisym=False, hot_up=True, hot_down=True):
        """!
        @brief Build the grid and the static operators.
        @param ra Rayleigh number of L = half width.
        @param pr Prandtl number.
        @param n_in Cells along the half plate.
        @param n_out Cells from the tip to the side boundary.
        @param n_up Cells above the plate.
        @param n_dn Cells below the plate.
        @param width Domain half width in L.
        @param up Extent above the plate in L.
        @param down Extent below the plate in L.
        @param dx_tip Cell size at the tip in L.
        @param dy0 First cell off the plate in L.
        @param axisym False: a strip of half width 1 (planar flow); True: a disc of radius 1 with axisymmetric flow about x = 0 (x is the radius).
        @param hot_up Upper face isothermal (False: insulated, a thin plate heated on the lower face only).
        @param hot_down Lower face isothermal (False: insulated).
        @return None.
        """
        self.hot_up, self.hot_down = bool(hot_up), bool(hot_down)
        self.axisym = bool(axisym)
        self.ra, self.pr = float(ra), float(pr)
        self.x, self.y, self.ip, self.j0 = make_grid(n_in, n_out, n_up, n_dn, width, up, down, dx_tip, dy0)
        self.nx, self.ny = len(self.x), len(self.y)
        nx, ny = self.nx, self.ny
        self.psi = np.zeros((nx, ny)); self.om = np.zeros((nx, ny)); self.T = np.zeros((nx, ny))
        self.plate = np.zeros((nx, ny), dtype=bool)
        self.plate[:self.ip + 1, self.j0] = True
        self.T[self.plate] = 1.0
        self.wu = np.zeros(self.ip + 1)                    # wall vorticity of the upper face
        self.wd = np.zeros(self.ip + 1)                    # wall vorticity of the lower face
        self.relax = 0.3
        hxm, hxp = np.diff(self.x)[:-1], np.diff(self.x)[1:]
        hym, hyp = np.diff(self.y)[:-1], np.diff(self.y)[1:]
        self.wx1, self.wx2 = np.array(_w1(hxm, hxp)), np.array(_w2(hxm, hxp))
        self.wy1, self.wy2 = np.array(_w1(hym, hyp)), np.array(_w2(hym, hyp))
        self.dt = None
        self._poisson = self._assemble_poisson()

    def idx(self, i, j):
        """!
        @brief Flat index of node (i, j).
        @param i Index in x.
        @param j Index in y.
        @return int or array.
        """
        return i * self.ny + j

    def _lap(self, rows, cols, vals, I, J, scale, skip_j0_below=False, skip_j0_above=False, kind="T", adiab_below=False, adiab_above=False):
        """!
        @brief Append the 5-point Laplacian stencil of the interior nodes (I, J) to coordinate lists.
        @param rows Row list of arrays.
        @param cols Column list of arrays.
        @param vals Value list of arrays.
        @param I Array of x indices (1..nx-2).
        @param J Array of y indices (1..ny-2).
        @param scale Multiplier of the stencil.
        @param skip_j0_below Drop the coupling of a node at j0 + 1 to the plate row (its value goes to the right-hand side).
        @param skip_j0_above Drop the coupling of a node at j0 - 1 to the plate row.
        @param adiab_below For T: the face under a node at j0 + 1 is insulated, the plate row is a mirror (zero flux) instead of a Dirichlet value.
        @param adiab_above Same for a node at j0 - 1.
        @param kind "psi", "T" or "om": the axisymmetric operator adds -psi_x/x (psi), T_x/x (T) or omega_x/x - omega/x^2 (om) to the planar Laplacian.
        @return None.
        """
        r = self.idx(I, J)
        a, b, c = self.wx2[:, I - 1]
        d, e, f = self.wy2[:, J - 1]
        rows += [r, r, r, r, r]
        cols += [self.idx(I - 1, J), self.idx(I + 1, J), self.idx(I, J - 1), self.idx(I, J + 1), r]
        if self.axisym:
            k = (-1.0 if kind == "psi" else 1.0) / self.x[I]
            w = self.wx1[:, I - 1]
            a = a + k * w[0]; b = b + k * w[1]; c = c + k * w[2]
            if kind == "om":
                b = b - 1.0 / self.x[I] ** 2
        dd, ff = d.copy(), f.copy()
        if skip_j0_below:
            dd[:] = 0.0
        if skip_j0_above:
            ff[:] = 0.0
        diag = b + e
        if adiab_below:                                     # mirror: the neighbour on the plate takes the value of the node itself
            diag = diag + d; dd[:] = 0.0
        if adiab_above:
            diag = diag + f; ff[:] = 0.0
        vals += [scale * a, scale * c, scale * dd, scale * ff, scale * diag]

    def _assemble(self, kind, diff=1.0, dt=1.0):
        """!
        @brief LU factorisation of the Poisson problem (kind "psi") or of (I - dt diff Laplacian) for T ("T") and omega ("om").
        @param kind "psi", "T" or "om".
        @param diff Diffusivity in plate units (1 for T, Pr for omega).
        @param dt Time step.
        @return SuperLU object.
        """
        nx, ny, j0, ip = self.nx, self.ny, self.j0, self.ip
        I, J = np.meshgrid(np.arange(nx), np.arange(ny), indexing="ij")
        I, J = I.ravel(), J.ravel()
        plate = self.plate.ravel()
        rows, cols, vals = [], [], []
        ident = lambda m: (rows.append(self.idx(I[m], J[m])), cols.append(self.idx(I[m], J[m])), vals.append(np.ones(m.sum())))
        neumann = lambda m, di, dj: (rows.extend([self.idx(I[m], J[m])] * 2), cols.extend([self.idx(I[m], J[m]), self.idx(I[m] + di, J[m] + dj)]), vals.extend([np.ones(m.sum()), -np.ones(m.sum())]))
        done = np.zeros(nx * ny, dtype=bool)
        if kind == "psi":
            m = (I == 0) | plate; ident(m); done |= m
            m = ~done & (I == nx - 1); neumann(m, -1, 0); done |= m
            m = ~done & (J == 0); neumann(m, 0, 1); done |= m
            m = ~done & (J == ny - 1); neumann(m, 0, -1); done |= m
            scale = 1.0
        elif kind == "T":
            m = plate; ident(m); done |= m
            m = ~done & (I == 0) & (J > 0) & (J < ny - 1); neumann(m, 1, 0); done |= m
            m = ~done & ((I == nx - 1) | (J == 0)); ident(m); done |= m
            m = ~done & (J == ny - 1); neumann(m, 0, -1); done |= m
            scale = -dt * diff
        else:
            m = plate | (I == 0) | (I == nx - 1) | (J == 0); ident(m); done |= m
            m = ~done & (J == ny - 1); neumann(m, 0, -1); done |= m
            scale = -dt * diff
        # Interior nodes
        free = ~done
        if kind != "psi":
            diagonal = free
            rows.append(self.idx(I[diagonal], J[diagonal])); cols.append(self.idx(I[diagonal], J[diagonal])); vals.append(np.ones(diagonal.sum()))
        for sel, below, above in ((free & ~((J == j0 + 1) & (I <= ip) & (I >= 1)) & ~((J == j0 - 1) & (I <= ip) & (I >= 1)), False, False),
                                  (free & (J == j0 + 1) & (I <= ip) & (I >= 1), True, False),
                                  (free & (J == j0 - 1) & (I <= ip) & (I >= 1), False, True)):
            if not sel.any():
                continue
            if kind == "om":
                self._lap(rows, cols, vals, I[sel], J[sel], scale, skip_j0_below=below, skip_j0_above=above, kind="om")
            else:
                self._lap(rows, cols, vals, I[sel], J[sel], scale, kind=kind, adiab_below=(below and kind == "T" and not self.hot_up), adiab_above=(above and kind == "T" and not self.hot_down))
        R = np.concatenate(rows); C = np.concatenate(cols); V = np.concatenate(vals)
        return splu(sp.csc_matrix((V, (R, C)), shape=(nx * ny, nx * ny)))

    def _assemble_poisson(self):
        """!
        @brief LU of the Poisson problem with psi = 0 on the plate and on x = 0.
        @return SuperLU object.
        """
        return self._assemble("psi")

    def set_dt(self, dt):
        """!
        @brief Choose the pseudo-time step and factorise the implicit operators.
        @param dt Time step.
        @return None.
        """
        self.dt = dt
        self._lu_T = self._assemble("T", 1.0, dt)
        self._lu_om = self._assemble("om", self.pr, dt)

    def _ddx(self, f):
        """!
        @brief Interior first derivative in x.
        @param f Array (nx, ny).
        @return Array (nx-2, ny).
        """
        w = self.wx1
        return w[0][:, None] * f[:-2] + w[1][:, None] * f[1:-1] + w[2][:, None] * f[2:]

    def _ddy(self, f):
        """!
        @brief Interior first derivative in y.
        @param f Array (nx, ny).
        @return Array (nx, ny-2).
        """
        w = self.wy1
        return w[0][None, :] * f[:, :-2] + w[1][None, :] * f[:, 1:-1] + w[2][None, :] * f[:, 2:]

    def velocities(self):
        """!
        @brief u = dpsi/dy and v = -dpsi/dx at every node (zero at the edges of the arrays where not computed).
        @return tuple (u, v).
        """
        u = np.zeros_like(self.psi); v = np.zeros_like(self.psi)
        u[:, 1:-1] = self._ddy(self.psi)
        v[1:-1, :] = -self._ddx(self.psi)
        if self.axisym:                                     # u = psi_y / r, v = -psi_x / r (the axis row stays zero: it is never used)
            u[1:, :] /= self.x[1:, None]; v[1:, :] /= self.x[1:, None]
            u[0, :] = 0.0; v[0, :] = 0.0
        return u, v

    def step(self):
        """!
        @brief One pseudo-time step: explicit convection and buoyancy, implicit diffusion, Poisson solve, wall vorticities.
        @return float, largest change of T in the step.
        """
        nx, ny, dt, j0, ip = self.nx, self.ny, self.dt, self.j0, self.ip
        u, v = self.velocities()
        T, om = self.T, self.om
        Tx = np.zeros_like(T); Ty = np.zeros_like(T); ox = np.zeros_like(T); oy = np.zeros_like(T)
        Tx[1:-1, :] = self._ddx(T); Ty[:, 1:-1] = self._ddy(T)
        ox[1:-1, :] = self._ddx(om); oy[:, 1:-1] = self._ddy(om)
        # The rows next to the plate use the wall vorticity of their own face in the y-derivative
        i1 = slice(1, ip + 1)
        w_ = self.wy1
        oy[i1, j0 + 1] = w_[0][j0] * self.wu[1:] + w_[1][j0] * om[i1, j0 + 1] + w_[2][j0] * om[i1, j0 + 2]
        oy[i1, j0 - 1] = w_[0][j0 - 2] * om[i1, j0 - 2] + w_[1][j0 - 2] * om[i1, j0 - 1] + w_[2][j0 - 2] * self.wd[1:]
        inner = (slice(1, nx - 1), slice(1, ny - 1))
        rhs_T = T.copy(); rhs_om = om.copy()
        rhs_T[inner] = T[inner] - dt * (u * Tx + v * Ty)[inner]
        rhs_om[inner] = om[inner] - dt * (u * ox + v * oy)[inner] + dt * self.ra * self.pr * Tx[inner]
        if self.axisym:                                     # vortex stretching u omega / r
            rhs_om[inner] += (dt * u * om / self.x[:, None])[inner]
        # Wall terms of the diffusion on the rows next to the plate (explicit, lagged wall vorticity)
        a_up = self.wy2[0][j0]                       # coupling of row j0 + 1 to row j0
        a_dn = self.wy2[2][j0 - 2]                   # coupling of row j0 - 1 to row j0
        rhs_om[i1, j0 + 1] += dt * self.pr * a_up * self.wu[1:]
        rhs_om[i1, j0 - 1] += dt * self.pr * a_dn * self.wd[1:]
        # Boundary values
        rhs_T[self.plate] = 1.0
        rhs_T[0, :j0] = 0.0; rhs_T[0, j0 + 1:] = 0.0
        rhs_T[-1, :] = 0.0; rhs_T[:, 0] = 0.0; rhs_T[:, -1] = 0.0
        rhs_om[0, :] = 0.0; rhs_om[-1, :] = 0.0; rhs_om[:, 0] = 0.0; rhs_om[:, -1] = 0.0
        rhs_om[self.plate] = 0.5 * (self.wu + self.wd)
        Tn = self._lu_T.solve(rhs_T.ravel()).reshape(nx, ny)
        omn = self._lu_om.solve(rhs_om.ravel()).reshape(nx, ny)
        rhs_psi = -omn.copy()
        if self.axisym:
            rhs_psi = -omn * self.x[:, None]
        rhs_psi[0, :] = 0.0; rhs_psi[self.plate] = 0.0
        rhs_psi[-1, :] = 0.0; rhs_psi[:, 0] = 0.0; rhs_psi[:, -1] = 0.0
        self.psi = self._poisson.solve(rhs_psi.ravel()).reshape(nx, ny)
        dyu = self.y[j0 + 1] - self.y[j0]; dyd = self.y[j0] - self.y[j0 - 1]
        fu = -2.0 * self.psi[:ip + 1, j0 + 1] / dyu ** 2
        fd = -2.0 * self.psi[:ip + 1, j0 - 1] / dyd ** 2
        if self.axisym:
            fu[1:] /= self.x[1:ip + 1]; fd[1:] /= self.x[1:ip + 1]
            fu[0] = 0.0; fd[0] = 0.0
        self.wu = self.relax * fu + (1 - self.relax) * self.wu
        self.wd = self.relax * fd + (1 - self.relax) * self.wd
        change = float(np.max(np.abs(Tn - T)))
        self.T, self.om = Tn, omn
        return change

    def nusselt_local(self):
        """!
        @brief Local Nusselt number (-dT/dn at the plate, second-order one-sided) of the upper and lower faces along x in [0, 1].
        @return tuple (x, nu_up, nu_down).
        """
        j0, ip, y, T = self.j0, self.ip, self.y, self.T
        wu = one_sided(y[j0 + 1] - y[j0], y[j0 + 2] - y[j0 + 1])
        wd = one_sided(y[j0] - y[j0 - 1], y[j0 - 1] - y[j0 - 2])
        nu_u = -(wu[0] * T[:ip + 1, j0] + wu[1] * T[:ip + 1, j0 + 1] + wu[2] * T[:ip + 1, j0 + 2])
        nu_d = -(wd[0] * T[:ip + 1, j0] + wd[1] * T[:ip + 1, j0 - 1] + wd[2] * T[:ip + 1, j0 - 2])
        return self.x[:ip + 1], nu_u, nu_d

    def nusselt(self):
        """!
        @brief Mean Nusselt numbers (L = half width) of the upper and the lower face.
        @return tuple (nu_up, nu_down).
        """
        x, nu_u, nu_d = self.nusselt_local()
        nu_u = nu_u if self.hot_up else 0.0 * nu_u
        nu_d = nu_d if self.hot_down else 0.0 * nu_d
        w = 2.0 * x if self.axisym else np.ones_like(x)     # area weight of the disc (mean over pi R^2 of the flux 2 pi r dr)
        return float(np.trapezoid(nu_u * w, x)), float(np.trapezoid(nu_d * w, x))

    def energy_balance(self):
        """!
        @brief Heat leaving through the outer boundaries divided by the heat leaving the plate (1 for a conservative converged solution).
        @details Top: integral of (v T - dT/dy) dx; side: (u T - dT/dx) dy; bottom: -(v T - dT/dy) dx, with second-order one-sided derivatives.
        @return float.
        """
        u, v = self.velocities()
        x, y, T = self.x, self.y, self.T
        nx, ny = self.nx, self.ny
        wt = one_sided(y[-1] - y[-2], y[-2] - y[-3])
        top = v[:, -1] * T[:, -1] + (wt[0] * T[:, -1] + wt[1] * T[:, -2] + wt[2] * T[:, -3])
        ws = one_sided(x[-1] - x[-2], x[-2] - x[-3])
        side = u[-1, :] * T[-1, :] + (ws[0] * T[-1, :] + ws[1] * T[-2, :] + ws[2] * T[-3, :])
        wb = one_sided(y[1] - y[0], y[2] - y[1])
        bot = -(v[:, 0] * T[:, 0] - (wb[0] * T[:, 0] + wb[1] * T[:, 1] + wb[2] * T[:, 2]))
        if self.axisym:                                     # fluxes through rings: weight 2 r (the common factor pi cancels against the plate)
            q = np.trapezoid(2 * x * top, x) + 2 * x[-1] * np.trapezoid(side, y) + np.trapezoid(2 * x * bot, x)
        else:
            q = np.trapezoid(top, x) + np.trapezoid(side, y) + np.trapezoid(bot, x)
        nu_u, nu_d = self.nusselt()
        return float(q / (nu_u + nu_d))

    def heat_through_box(self, x_side, y_top, y_bottom):
        """!
        @brief Heat crossing a closed box around the plate (the half domain from the axis to x_side, from y_bottom to y_top), divided by the heat the plate's wall gradient gives.
        @details Added by the review: the plate's Nu comes from a one-sided wall gradient that under-resolves the singular flux at the edge of a zero-thickness plate, and the convection
                 is not conservative, so the heat crossing boxes of different sizes tells which of the two is the larger error. Convective plus conductive flux (v T - T_y on the top and
                 bottom lines, u T - T_x on the side line), central differences at the nearest node lines, trapezoid rule, the weight 2 r for the disc.
        @param x_side Side of the box (in L; taken at the nearest node line, must lie beyond the edge x = 1).
        @param y_top Top of the box (in L, above the plate).
        @param y_bottom Bottom of the box (in L, below the plate, negative).
        @return float, heat through the box over the heat of the plate (1 for a conservative field and an exact wall flux).
        """
        u, v = self.velocities()
        x, y, T = self.x, self.y, self.T
        i = int(np.argmin(abs(x - x_side))); jt = int(np.argmin(abs(y - y_top))); jb = int(np.argmin(abs(y - y_bottom)))
        tx = np.zeros_like(T); ty = np.zeros_like(T)
        tx[1:-1, :] = self._ddx(T); ty[:, 1:-1] = self._ddy(T)
        w = 2.0 * x if self.axisym else np.ones_like(x)       # rings of the disc (pi cancels against the plate)
        top = np.trapezoid(w[:i + 1] * (v[:i + 1, jt] * T[:i + 1, jt] - ty[:i + 1, jt]), x[:i + 1])
        bot = -np.trapezoid(w[:i + 1] * (v[:i + 1, jb] * T[:i + 1, jb] - ty[:i + 1, jb]), x[:i + 1])
        side = (2.0 * x[i] if self.axisym else 1.0) * np.trapezoid(u[i, jb:jt + 1] * T[i, jb:jt + 1] - tx[i, jb:jt + 1], y[jb:jt + 1])
        nu_u, nu_d = self.nusselt()
        return float((top + bot + side) / (nu_u + nu_d))

    def run(self, max_steps=200000, check=2500, tol=2e-5, dt=None, window=6):
        """!
        @brief March to the steady state; if the history does not settle, report the mean over the last `window` checks and the amplitude.
        @param max_steps Maximum number of steps.
        @param check Steps between the records of the Nusselt numbers.
        @param tol Relative change of both Nusselt numbers between two records that counts as converged.
        @param dt Time step (default from the buoyancy velocity scale and the smallest cell).
        @param window Number of records of the final average.
        @return dict with nu_up, nu_down, converged, steps, amp_up, amp_down (half range over the window, relative) and the history.
        """
        if dt is None:
            vscale = 0.3 * np.sqrt(self.ra * self.pr)
            hmin = min(np.diff(self.x).min(), np.diff(self.y).min())
            dt = min(3.0 * (self.y[self.j0 + 1] - self.y[self.j0]) ** 2, 0.35 * hmin / max(vscale, 1.0))
        self.set_dt(dt)
        hist = []
        for k in range(1, max_steps + 1):
            self.step()
            if k % check == 0:
                hist.append((k,) + self.nusselt())
                if not np.all(np.isfinite(hist[-1][1:])):                              # the explicit convection blew up: stop, the result carries nan
                    return self._result(hist, False, k, 1)
                if len(hist) >= 2:
                    a, b = np.array(hist[-1][1:]), np.array(hist[-2][1:])
                    if np.all(np.abs(a - b) <= tol * np.abs(a) + 1e-12):          # an insulated face has Nu = 0 and counts as settled
                        return self._result(hist, True, k, 1)
        return self._result(hist, False, max_steps, window)

    def _result(self, hist, converged, steps, window):
        """!
        @brief Summarise the history.
        @param hist List of (step, nu_up, nu_down).
        @param converged Whether the settling criterion was met.
        @param steps Steps taken.
        @param window Records averaged.
        @return dict.
        """
        h = np.array(hist)[-window:, 1:]
        mean = h.mean(axis=0)
        amp = 0.5 * (h.max(axis=0) - h.min(axis=0)) / np.where(mean == 0.0, 1.0, mean)
        return {"nu_up": float(mean[0]), "nu_down": float(mean[1]), "converged": converged, "steps": steps, "amp_up": float(amp[0]), "amp_down": float(amp[1]), "history": hist}
