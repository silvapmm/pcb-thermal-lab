#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file mac2d.py
@brief Independent 2D Boussinesq solver in primitive variables (staggered MAC grid, incremental pressure correction) for natural convection in a closed box, with an optional thin isothermal plate inside.
@details Written for research/convection-laws; imports nothing from the program and nothing from the other plate solvers of the repository (those are stream function and
         vorticity solvers: this one has another formulation, another grid arrangement and other boundary conditions, so that an agreement is not a repeat of the same code).

         Non-dimensional equations (lengths in L, time in L^2/alpha, velocity in alpha/L, T = (Tdim - Tref)/dT, gravity along -y):
             u_t + div(u u) = -grad p + Pr lap(u) + Ra Pr T e_y,      T_t + div(u T) = lap(T),      div u = 0.
         Grid: tensor product of stretched 1D grids; T and p in cell centres, u on vertical faces, v on horizontal faces. Convection by second-order central fluxes (explicit
         Euler), diffusion implicit (one factorised sparse matrix per field), incremental pressure-correction projection (Poisson matrix factorised once, one cell pinned).
         Boundaries: the four sides of the box are `wall` (no slip; T fixed or adiabatic) or `sym` (free slip, adiabatic); a thin plate (zero thickness, no slip, T fixed)
         may lie on the grid line y = 0 for 0 <= x <= x_end (the half domain x >= 0 with a symmetry line at x = 0 is the strip of half width x_end, so that L = A/P = x_end).
         Usage: see scripts/study_cavity.py and scripts/study_plate_mac.py.
"""

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla


def graded(segments):
    """!
    @brief Cell faces of a 1D grid made of geometric segments.
    @param segments List of (length, n_cells, ratio): the cells of the segment grow by `ratio` from one to the next (ratio < 1 shrinks them), in the direction of increasing coordinate.
    @return numpy array of the faces, starting at 0.
    """
    faces = [0.0]
    for length, n, r in segments:
        if abs(r - 1.0) < 1e-12:
            w = np.full(n, length / n)
        else:
            first = length * (r - 1.0) / (r ** n - 1.0)
            w = first * r ** np.arange(n)
        faces.extend(faces[-1] + np.cumsum(w))
    return np.array(faces)


def _assemble(cvw, cvh, distx, disty, west, east, south, north, cut=None, free=None):
    """!
    @brief Sparse operator A and vector b of the diffusion of one field on a rectangular set of control volumes: d(phi)/dt = A phi + b.
    @param cvw Widths of the control volumes (nx).
    @param cvh Heights of the control volumes (ny).
    @param distx Centre-to-centre distances in x (nx-1).
    @param disty Centre-to-centre distances in y (ny-1).
    @param west Boundary at i = 0: None (zero flux) or (dist, value) with dist the distance from the centre to the wall, array (ny) or float.
    @param east Boundary at i = nx-1, same form.
    @param south Boundary at j = 0, same form (dist array (nx) or float).
    @param north Boundary at j = ny-1, same form.
    @param cut Optional internal wall in y: (jp, cols, value, dist_lo, dist_hi[, hot_lo, hot_hi]): the link between rows jp-1 and jp is cut for the columns `cols` (bool array, nx), both sides see a wall of the given value at the given distances (arrays of nx).
    @param free Optional bool array (nx, ny): unknowns that are kept (the others are fixed at zero and removed).
    @return (A, b, idx) with A sparse, b the constant vector and idx the flat indices of the free unknowns.
    """
    nx, ny = len(cvw), len(cvh)
    n = nx * ny
    area = np.outer(cvw, cvh)
    rows, cols_, vals = [], [], []
    diag = np.zeros((nx, ny))
    b = np.zeros((nx, ny))
    flat = np.arange(n).reshape(nx, ny)

    # x links between (i, j) and (i+1, j)
    gx = np.outer(1.0 / np.asarray(distx), cvh)
    a_, b_ = flat[:-1, :], flat[1:, :]
    rows += [a_.ravel(), b_.ravel()]
    cols_ += [b_.ravel(), a_.ravel()]
    vals += [(gx / area[:-1, :]).ravel(), (gx / area[1:, :]).ravel()]
    diag[:-1, :] -= gx / area[:-1, :]
    diag[1:, :] -= gx / area[1:, :]

    # y links between (i, j) and (i, j+1), minus the cut ones
    gy = np.outer(cvw, 1.0 / np.asarray(disty))
    if cut is not None:
        jp, cmask = cut[0], cut[1]
        gy = gy.copy()
        gy[cmask, jp - 1] = 0.0
    a_, b_ = flat[:, :-1], flat[:, 1:]
    rows += [a_.ravel(), b_.ravel()]
    cols_ += [b_.ravel(), a_.ravel()]
    vals += [(gy / area[:, :-1]).ravel(), (gy / area[:, 1:]).ravel()]
    diag[:, :-1] -= gy / area[:, :-1]
    diag[:, 1:] -= gy / area[:, 1:]

    def dirichlet(sel, g, value):
        """!
        @brief Add a link to a wall of fixed value.
        @param sel Index tuple of the control volumes.
        @param g Conductances (width over distance).
        @param value Wall value.
        @return None.
        """
        diag[sel] -= g / area[sel]
        b[sel] += g * value / area[sel]

    if west is not None:
        dirichlet((0, slice(None)), cvh / np.broadcast_to(west[0], (ny,)), west[1])
    if east is not None:
        dirichlet((nx - 1, slice(None)), cvh / np.broadcast_to(east[0], (ny,)), east[1])
    if south is not None:
        dirichlet((slice(None), 0), cvw / np.broadcast_to(south[0], (nx,)), south[1])
    if north is not None:
        dirichlet((slice(None), ny - 1), cvw / np.broadcast_to(north[0], (nx,)), north[1])
    if cut is not None:
        jp, cmask, tw, dlo, dhi = cut[:5]
        hot_lo, hot_hi = (cut[5], cut[6]) if len(cut) > 5 else (True, True)       # a face that is not hot is insulated (zero flux)
        ii = np.where(cmask)[0]
        if hot_hi:
            dirichlet((ii, jp), cvw[ii] / dhi[ii], tw)      # the cells above the wall
        if hot_lo:
            dirichlet((ii, jp - 1), cvw[ii] / dlo[ii], tw)  # the cells below the wall

    A = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols_))), shape=(n, n)).tocsr() + sp.diags(diag.ravel())
    idx = np.arange(n) if free is None else np.where(free.ravel())[0]
    return A[idx][:, idx].tocsc(), b.ravel()[idx], idx


class Box:
    """!
    @brief Closed box (or half box with a symmetry line) with Boussinesq flow, an optional thin isothermal plate, steady state by pseudo-time marching.
    """

    def __init__(self, xf, yf, ra, pr=0.71, west=("wall", 1.0), east=("wall", 0.0), south=("wall", None), north=("wall", None), plate=None, faces="both"):
        """!
        @brief Build the grid, the operators and the factorisations.
        @param xf Cell faces in x (increasing, starting at 0).
        @param yf Cell faces in y (increasing; the plate, when present, lies on the face y = 0, which yf must contain).
        @param ra Rayleigh number of the length scale (the cavity width, or the plate half width).
        @param pr Prandtl number.
        @param west Side x = xf[0]: ("wall", T) with T a number (fixed) or None (adiabatic), or ("sym", None).
        @param east Side x = xf[-1], same form.
        @param south Side y = yf[0], same form.
        @param north Side y = yf[-1], same form.
        @param plate None or (x_end, T): thin plate on y = 0 from x = 0 to x_end (x_end must be a face of xf), temperature T.
        @param faces Which faces of the plate are hot: "both", "up" (the lower face is insulated) or "down" (the upper face is insulated).
        @return None.
        """
        self.xf, self.yf = np.asarray(xf, float), np.asarray(yf, float)
        self.nx, self.ny = len(xf) - 1, len(yf) - 1
        self.dx, self.dy = np.diff(self.xf), np.diff(self.yf)
        self.xc, self.yc = 0.5 * (self.xf[1:] + self.xf[:-1]), 0.5 * (self.yf[1:] + self.yf[:-1])
        self.ra, self.pr = float(ra), float(pr)
        self.sides = {"W": west, "E": east, "S": south, "N": north}
        self.plate = plate
        self.faces = faces
        nx, ny = self.nx, self.ny
        self.jp = self.npl = None
        self.tplate = None
        if plate is not None:
            self.jp = int(np.argmin(np.abs(self.yf)))
            assert abs(self.yf[self.jp]) < 1e-9, "the plate needs a grid face at y = 0"
            self.npl = int(np.argmin(np.abs(self.xf - plate[0])))
            assert abs(self.xf[self.npl] - plate[0]) < 1e-9, "the plate end must be a face of xf"
            self.tplate = float(plate[1])
        self._build_operators()
        self.u = np.zeros((nx + 1, ny))
        self.v = np.zeros((nx, ny + 1))
        self.T = np.zeros((nx, ny))
        self.p = np.zeros((nx, ny))
        self.t = 0.0
        self.converged = False
        self._dt_factored = None

    def _wall_T(self, side):
        """!
        @brief Temperature boundary of a side as accepted by `_assemble`.
        @param side "W", "E", "S" or "N".
        @return None (adiabatic or symmetry) or (distance, value).
        """
        kind, val = self.sides[side]
        if kind == "sym" or val is None:
            return None
        half = {"W": self.dx[0] / 2, "E": self.dx[-1] / 2, "S": self.dy[0] / 2, "N": self.dy[-1] / 2}[side]
        return (half, val)

    def _build_operators(self):
        """!
        @brief Diffusion matrices of T, u and v and the pressure Poisson matrix (factorised).
        @return None.
        """
        nx, ny, dx, dy, xc, yc = self.nx, self.ny, self.dx, self.dy, self.xc, self.yc
        cut = None
        if self.plate is not None:
            cm = np.zeros(nx, bool)
            cm[:self.npl] = True
            cut = (self.jp, cm, self.tplate, dy[self.jp - 1] / 2 * np.ones(nx), dy[self.jp] / 2 * np.ones(nx), self.faces in ("both", "down"), self.faces in ("both", "up"))
        # temperature
        self.AT, self.bT, self.idxT = _assemble(dx, dy, np.diff(xc), np.diff(yc), self._wall_T("W"), self._wall_T("E"), self._wall_T("S"), self._wall_T("N"), cut=cut)
        # u on the interior vertical faces i = 1 .. nx-1; the control volume spans the centres xc[i-1], xc[i]; faces 0 and nx are impermeable walls (u = 0)
        cutu = None
        if self.plate is not None:
            cmu = np.zeros(nx - 1, bool)
            cmu[:self.npl - 1] = True                       # faces 1 .. npl-1 lie inside the plate span
            cutu = (self.jp, cmu, 0.0, dy[self.jp - 1] / 2 * np.ones(nx - 1), dy[self.jp] / 2 * np.ones(nx - 1))
        su = None if self.sides["S"][0] == "sym" else (dy[0] / 2, 0.0)       # no slip on a wall, free slip on a symmetry line
        nu_ = None if self.sides["N"][0] == "sym" else (dy[-1] / 2, 0.0)
        self.Au, _, self.idxu = _assemble(np.diff(xc), dy, dx[1:-1], np.diff(yc), (dx[0], 0.0), (dx[-1], 0.0), su, nu_, cut=cutu)
        self.Au = self.Au * self.pr
        # v on the interior horizontal faces j = 1 .. ny-1; the faces under the plate are fixed at zero
        free = np.ones((nx, ny - 1), bool)
        if self.plate is not None:
            free[:self.npl, self.jp - 1] = False
        wv = None if self.sides["W"][0] == "sym" else (dx[0] / 2, 0.0)
        ev = None if self.sides["E"][0] == "sym" else (dx[-1] / 2, 0.0)
        self.Av, _, self.idxv = _assemble(dx, np.diff(yc), np.diff(xc), dy[1:-1], wv, ev, (dy[0], 0.0), (dy[-1], 0.0), free=free)
        self.Av = self.Av * self.pr
        # pressure Poisson: links across the u faces (all open) and the v faces (closed under the plate)
        n = nx * ny
        flat = np.arange(n).reshape(nx, ny)
        area = np.outer(dx, dy)
        gx = np.outer(1.0 / np.diff(xc), dy)
        gy = np.outer(dx, 1.0 / np.diff(yc))
        if self.plate is not None:
            gy[:self.npl, self.jp - 1] = 0.0
        diag = np.zeros((nx, ny))
        r, c, v = [], [], []
        for a_, b_, g, aa, ab in ((flat[:-1, :], flat[1:, :], gx, area[:-1, :], area[1:, :]), (flat[:, :-1], flat[:, 1:], gy, area[:, :-1], area[:, 1:])):
            ga, gb = g / aa, g / ab
            r += [a_.ravel(), b_.ravel()]
            c += [b_.ravel(), a_.ravel()]
            v += [ga.ravel(), gb.ravel()]
            if g.shape == gx.shape and a_.shape[0] == nx - 1:
                diag[:-1, :] -= ga
                diag[1:, :] -= gb
            else:
                diag[:, :-1] -= ga
                diag[:, 1:] -= gb
        L = (sp.coo_matrix((np.concatenate(v), (np.concatenate(r), np.concatenate(c))), shape=(n, n)).tocsr() + sp.diags(diag.ravel())).tolil()
        L[0, :] = 0.0                                          # pin the pressure level in the first cell
        L[0, 0] = 1.0
        self.poisson = spla.splu(L.tocsc())

    def _factor(self, dt):
        """!
        @brief Factorise the implicit diffusion matrices for a time step (reused while the step does not change).
        @param dt Time step.
        @return None.
        """
        if self._dt_factored is not None and abs(dt - self._dt_factored) < 1e-12:
            return
        eye = lambda m: sp.identity(m, format="csc")
        self.luT = spla.splu(eye(self.AT.shape[0]) - dt * self.AT)
        self.luu = spla.splu(eye(self.Au.shape[0]) - dt * self.Au)
        self.luv = spla.splu(eye(self.Av.shape[0]) - dt * self.Av)
        self._dt_factored = dt

    def _convection(self):
        """!
        @brief Central-flux convection terms of T, u and v at the current state.
        @return (cT, cu, cv): arrays at the T cells (nx, ny), the interior u faces (nx-1, ny) and the interior v faces (nx, ny-1).
        """
        u, v, T, xf, yf, xc, yc, dx, dy = self.u, self.v, self.T, self.xf, self.yf, self.xc, self.yc, self.dx, self.dy
        nx, ny = self.nx, self.ny
        # temperature: fluxes through the vertical faces (u T) and the horizontal faces (v T); the walls and the plate carry none
        wx = ((xf[1:-1] - xc[:-1]) / np.diff(xc))[:, None]
        Tx = T[:-1] + wx * (T[1:] - T[:-1])
        Fx = np.zeros((nx + 1, ny))
        Fx[1:-1] = u[1:-1] * Tx
        wy = ((yf[1:-1] - yc[:-1]) / np.diff(yc))[None, :]
        Ty = T[:, :-1] + wy * (T[:, 1:] - T[:, :-1])
        Fy = np.zeros((nx, ny + 1))
        Fy[:, 1:-1] = v[:, 1:-1] * Ty
        cT = -(Fx[1:] - Fx[:-1]) / dx[:, None] - (Fy[:, 1:] - Fy[:, :-1]) / dy[None, :]
        # u momentum at the interior vertical faces i = 1 .. nx-1
        uc = u[:-1] * ((xf[1:] - xc) / dx)[:, None] + u[1:] * ((xc - xf[:-1]) / dx)[:, None]      # u at the cell centres (nx, ny)
        cu_x = -(uc[1:] ** 2 - uc[:-1] ** 2) / np.diff(xc)[:, None]
        wl = ((xc[1:] - xf[1:-1]) / np.diff(xc))[:, None]                                         # v interpolated to the face x
        vcorn = v[:-1, :] * wl + v[1:, :] * (1.0 - wl)                                            # (nx-1, ny+1)
        wu = ((yc[1:] - yf[1:-1]) / np.diff(yc))[None, :]
        ucorn = u[1:-1, :-1] * wu + u[1:-1, 1:] * (1.0 - wu)                                      # (nx-1, ny-1) at the interior corners
        Fn = np.zeros((nx - 1, ny + 1))
        Fn[:, 1:-1] = vcorn[:, 1:-1] * ucorn
        cu_y = -(Fn[:, 1:] - Fn[:, :-1]) / dy[None, :]
        # v momentum at the interior horizontal faces j = 1 .. ny-1
        vc = v[:, :-1] * ((yf[1:] - yc) / dy)[None, :] + v[:, 1:] * ((yc - yf[:-1]) / dy)[None, :]
        cv_y = -(vc[:, 1:] ** 2 - vc[:, :-1] ** 2) / np.diff(yc)[None, :]
        wv_ = ((yc[1:] - yf[1:-1]) / np.diff(yc))[None, :]
        ucv = u[:, :-1] * wv_ + u[:, 1:] * (1.0 - wv_)                                            # u at (xf, interior yf): (nx+1, ny-1)
        vcx = v[:-1, 1:-1] + wx * (v[1:, 1:-1] - v[:-1, 1:-1])                                    # v at the interior corners (nx-1, ny-1)
        Fe = np.zeros((nx + 1, ny - 1))
        Fe[1:-1] = ucv[1:-1] * vcx
        cv_x = -(Fe[1:] - Fe[:-1]) / dx[:, None]
        return cT, cu_x + cu_y, cv_y + cv_x

    def step(self, dt):
        """!
        @brief One time step: explicit convection, implicit diffusion, incremental pressure correction.
        @param dt Time step.
        @return Largest change of T per unit time over the step.
        """
        self._factor(dt)
        nx, ny, pr, ra = self.nx, self.ny, self.pr, self.ra
        cT, cu, cv = self._convection()
        told = self.T.copy()
        tn = told.ravel().copy()
        tn[self.idxT] = self.luT.solve(told.ravel()[self.idxT] + dt * (cT.ravel()[self.idxT] + self.bT))
        self.T = tn.reshape(nx, ny)
        # pressure gradient and buoyancy (the temperature of the old step) at the faces
        gpx = (self.p[1:] - self.p[:-1]) / np.diff(self.xc)[:, None]
        gpy = (self.p[:, 1:] - self.p[:, :-1]) / np.diff(self.yc)[None, :]
        wy = ((self.yf[1:-1] - self.yc[:-1]) / np.diff(self.yc))[None, :]
        tf = told[:, :-1] + wy * (told[:, 1:] - told[:, :-1])
        ru = self.u[1:-1].ravel()[self.idxu] + dt * (cu.ravel()[self.idxu] - gpx.ravel()[self.idxu])
        rv = self.v[:, 1:-1].ravel()[self.idxv] + dt * (cv.ravel()[self.idxv] - gpy.ravel()[self.idxv] + ra * pr * tf.ravel()[self.idxv])
        us = np.zeros((nx - 1) * ny)
        us[self.idxu] = self.luu.solve(ru)
        vs = np.zeros(nx * (ny - 1))
        vs[self.idxv] = self.luv.solve(rv)
        us, vs = us.reshape(nx - 1, ny), vs.reshape(nx, ny - 1)
        # projection onto div u = 0
        div = (np.diff(np.vstack([np.zeros((1, ny)), us, np.zeros((1, ny))]), axis=0) / self.dx[:, None]
               + np.diff(np.hstack([np.zeros((nx, 1)), vs, np.zeros((nx, 1))]), axis=1) / self.dy[None, :])
        rhs_p = (div / dt).ravel()
        rhs_p[0] = 0.0
        phi = self.poisson.solve(rhs_p).reshape(nx, ny)
        self.u[1:-1] = us - dt * (phi[1:] - phi[:-1]) / np.diff(self.xc)[:, None]
        dv = dt * (phi[:, 1:] - phi[:, :-1]) / np.diff(self.yc)[None, :]
        if self.plate is not None:
            dv[:self.npl, self.jp - 1] = 0.0
        self.v[:, 1:-1] = vs - dv
        self.p += phi
        self.t += dt
        return float(np.abs(self.T - told).max() / dt)

    def run(self, t_end=50.0, tol=1e-7, cfl=0.4, dt_max=2e-3, dt_min=2e-5, max_steps=400000, verbose=False):
        """!
        @brief March to the steady state.
        @param t_end Maximum non-dimensional time.
        @param tol Stop when the largest dT/dt (in dT per L^2/alpha) is below it.
        @param cfl Courant number of the convective step (the diffusive stability bound is dt < 1/umax^2).
        @param dt_max Largest step.
        @param dt_min Smallest step.
        @param max_steps Step cap.
        @param verbose Print the progress.
        @return Number of steps taken; `self.converged` tells whether the tolerance was met.
        """
        n = 0
        self.converged = False
        dmin = min(self.dx.min(), self.dy.min())
        while self.t < t_end and n < max_steps:
            umax = max(np.abs(self.u).max(), np.abs(self.v).max(), 1e-9)
            dt = min(dt_max, max(dt_min, min(cfl * dmin / umax, 1.0 / (umax * umax))))
            dt = float(np.round(dt, 7))
            if self._dt_factored is not None and abs(dt - self._dt_factored) < 0.25 * dt:
                dt = self._dt_factored                  # reuse the factorisation while the step stays within 25 %
            rate = self.step(dt)
            n += 1
            if verbose and n % 2000 == 0:
                print(f"t={self.t:.3f} dt={dt:.2e} dT/dt={rate:.2e} umax={umax:.2f}", flush=True)
            if rate < tol and n > 50:
                self.converged = True
                break
        return n

    def wall_gradient(self, side):
        """!
        @brief Heat flux from a fixed-temperature side into the fluid, -dT/dn with n pointing into the fluid, second order from the first two cells.
        @param side "W", "E", "S" or "N".
        @return Array of the flux along the side (positive when the wall is hotter than the fluid).
        """
        tw = self.sides[side][1]
        T = self.T
        if side == "W":
            d1, d2, t0, t1 = self.xc[0] - self.xf[0], self.xc[1] - self.xf[0], T[0], T[1]
        elif side == "E":
            d1, d2, t0, t1 = self.xf[-1] - self.xc[-1], self.xf[-1] - self.xc[-2], T[-1], T[-2]
        elif side == "S":
            d1, d2, t0, t1 = self.yc[0] - self.yf[0], self.yc[1] - self.yf[0], T[:, 0], T[:, 1]
        else:
            d1, d2, t0, t1 = self.yf[-1] - self.yc[-1], self.yf[-1] - self.yc[-2], T[:, -1], T[:, -2]
        a = ((t0 - tw) * d2 ** 2 - (t1 - tw) * d1 ** 2) / (d1 * d2 ** 2 - d2 * d1 ** 2)      # dT/dn
        return -a

    def plate_nusselt(self):
        """!
        @brief Mean Nusselt number of the two faces of the plate (L = plate half width, dT = plate temperature minus the cold walls), second-order wall gradient.
        @return (Nu_up, Nu_down, q_up(x), q_down(x)) with the local flux on the cells of the plate.
        """
        jp, npl, T, tp = self.jp, self.npl, self.T, self.tplate
        out = []
        for sgn in (+1, -1):
            if sgn > 0:
                d1, d2 = self.dy[jp] / 2, self.dy[jp] + self.dy[jp + 1] / 2
                t0, t1 = T[:npl, jp], T[:npl, jp + 1]
            else:
                d1, d2 = self.dy[jp - 1] / 2, self.dy[jp - 1] + self.dy[jp - 2] / 2
                t0, t1 = T[:npl, jp - 1], T[:npl, jp - 2]
            out.append(-((t0 - tp) * d2 ** 2 - (t1 - tp) * d1 ** 2) / (d1 * d2 ** 2 - d2 * d1 ** 2))
        w = self.dx[:npl]
        return float((out[0] * w).sum() / w.sum()), float((out[1] * w).sum() / w.sum()), out[0], out[1]

    def heat_into_walls(self):
        """!
        @brief Heat taken from the fluid by each fixed-temperature side (per unit depth, non-dimensional; negative flux of `wall_gradient` summed over the side).
        @return dict side -> heat leaving the fluid into the wall (positive for a cold wall).
        """
        res = {}
        for s, (kind, val) in self.sides.items():
            if kind == "wall" and val is not None:
                w = self.dy if s in "WE" else self.dx
                res[s] = float(-(self.wall_gradient(s) * w).sum())
        return res
