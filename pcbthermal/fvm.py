"""!
@file fvm.py
@brief Cell-centred finite-volume thermal solver for a multi-layer PCB (steady and transient).

@details Every copper layer is a 2D sheet of cells. A cell is a control volume of size
dx x dy and thickness t_pcb / layers. Heat flows

- sideways between neighbouring cells through the layer sheet conductance
  S = f * k_cu * t_cu + k_fr4_inplane * (slab - f * t_cu), where f is the copper fill,
- vertically between layers through the FR-4 dielectric (and the via barrels),
- to ambient through the top and bottom surfaces, the sinks and, optionally, the edges.

The steady problem is the sparse symmetric positive definite system K*theta = Q with
theta = T - T_ambient, solved directly (sparse LU) or with Conjugate Gradients. The transient
problem adds the heat capacity C and is advanced with the theta-method (implicit Euler or
Crank-Nicolson). Because the scheme is a finite-volume balance, the heat leaving the board
equals the injected power to solver precision, which the results report.
"""

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from .geometry import coverage_fraction, cell_index_of_point, polygon_centroid
from .results import SteadyResult, TransientResult


class Network:
    """!
    @brief Assembled thermal network: conductances, capacities, sources and the sparse matrix.
    """

    def __init__(self, problem, nx, ny):
        """!
        @brief Build the network of a problem on an nx x ny grid.
        @param problem A validated Problem.
        @param nx Number of cells along x.
        @param ny Number of cells along y.
        """
        problem.validate()
        self.problem = problem
        b = problem.board
        m = b.materials
        self.nx, self.ny, self.nl = nx, ny, b.layers
        self.dx, self.dy = b.width / nx, b.height / ny
        L, dx, dy = b.layers, self.dx, self.dy
        cell = dx * dy                       # Cell footprint area (m2)
        slab = b.thickness / L               # Thickness represented by one layer node (m)
        t_cu = np.asarray(b.copper_thickness)
        if np.any(t_cu >= slab):
            raise ValueError("copper thickness must be smaller than thickness / layers")

        # --- Copper fill fraction of every layer (union of its zones, hatching via 'fill')
        f = np.zeros((L, ny, nx))
        for z in problem.zones:
            cov = coverage_fraction(z.polygon, nx, ny, dx, dy, samples=4) * z.fill
            f[z.layer] = np.maximum(f[z.layer], cov)
        self.fill = f

        # --- Sheet conductance (W/K) and heat capacity (J/K) of every cell
        tc = t_cu[:, None, None]
        diel_t = slab - f * tc                         # FR-4 thickness left in the slab (m)
        self.S = f * m.k_copper * tc + m.k_fr4_inplane * diel_t
        self.C = (f * m.rho_copper * m.cp_copper * tc + diel_t * m.rho_fr4 * m.cp_fr4) * cell

        # --- Vertical conductance between layer l and l+1 (W/K)
        self.gz = np.zeros((max(L - 1, 0), ny, nx))
        if L > 1:
            d = b.dielectric_thickness()
            self.gz[:] = m.k_fr4_through * cell / d    # Dielectric alone
            for v in problem.vias:
                i, j = cell_index_of_point(v.x, v.y, nx, ny, dx, dy)
                # The barrel conducts in parallel with the dielectric, across every gap
                self.gz[:, i, j] += m.k_copper * v.copper_area(b.via_plating) / d

        # --- Conductance to ambient (W/K): top, bottom, sinks and edges are kept separate
        self.g_top = np.zeros((L, ny, nx))
        self.g_bottom = np.zeros((L, ny, nx))
        self.g_sink = np.zeros((L, ny, nx))
        self.g_side = np.zeros((L, ny, nx))
        self.g_top[0] = b.h_top * cell
        self.g_bottom[L - 1] = b.h_bottom * cell       # For one layer top and bottom share layer 0
        for s in problem.sinks:
            cov = coverage_fraction(s.polygon, nx, ny, dx, dy, samples=4)
            self.g_sink[s.layer] += s.h_extra * cell * cov
        if b.h_side:
            # Each edge cell exposes a face of (cell edge length) x (slab thickness)
            self.g_side[:, :, 0] += b.h_side * dy * slab
            self.g_side[:, :, -1] += b.h_side * dy * slab
            self.g_side[:, 0, :] += b.h_side * dx * slab
            self.g_side[:, -1, :] += b.h_side * dx * slab
        self.g_amb = self.g_top + self.g_bottom + self.g_sink + self.g_side

        # --- Heat sources (W): the requested power is spread exactly over the covered cells
        self.Q = np.zeros((L, ny, nx))
        for h in problem.heaters:
            cov = coverage_fraction(h.polygon, nx, ny, dx, dy, samples=8)
            if cov.sum() <= 0:
                # Footprint smaller than the sampling: put all the power in the centroid cell
                cx, cy = polygon_centroid(h.polygon)
                i, j = cell_index_of_point(cx, cy, nx, ny, dx, dy)
                cov[i, j] = 1.0
            self.Q[h.layer] += h.power * cov / cov.sum()

        self.K = self._assemble()

    # ------------------------------------------------------------------ assembly
    @staticmethod
    def _harmonic(a, b):
        """!
        @brief Harmonic mean of two conductances (series combination of the half cells).
        @param a First array.
        @param b Second array.
        @return Array with 2ab/(a+b), zero where both are zero.
        """
        s = a + b
        out = np.zeros_like(s)
        np.divide(2.0 * a * b, s, out=out, where=s > 0)
        return out

    def _assemble(self):
        """!
        @brief Assemble the sparse conductance matrix K (W/K).
        @return scipy.sparse.csr_matrix of shape (N, N), N = layers * ny * nx.
        """
        L, ny, nx = self.nl, self.ny, self.nx
        idx = np.arange(L * ny * nx).reshape(L, ny, nx)
        rows, cols, vals = [], [], []

        def couple(a_idx, b_idx, g):
            # A symmetric coupling g between nodes a and b adds +g to both diagonals and -g off diagonal
            a, bb, gg = a_idx.ravel(), b_idx.ravel(), g.ravel()
            keep = gg > 0
            a, bb, gg = a[keep], bb[keep], gg[keep]
            rows.extend([a, bb, a, bb])
            cols.extend([a, bb, bb, a])
            vals.extend([gg, gg, -gg, -gg])

        # Lateral couplings: face width / distance gives dy/dx (x) and dx/dy (y)
        gx = self._harmonic(self.S[:, :, :-1], self.S[:, :, 1:]) * self.dy / self.dx
        gy = self._harmonic(self.S[:, :-1, :], self.S[:, 1:, :]) * self.dx / self.dy
        couple(idx[:, :, :-1], idx[:, :, 1:], gx)
        couple(idx[:, :-1, :], idx[:, 1:, :], gy)
        if L > 1:
            couple(idx[:-1], idx[1:], self.gz)
        # Conductance to ambient only adds to the diagonal
        n = L * ny * nx
        diag = self.g_amb.ravel()
        rows.append(np.arange(n))
        cols.append(np.arange(n))
        vals.append(diag)
        K = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))),
                          shape=(n, n)).tocsr()
        return K

    # ------------------------------------------------------------------ solving
    def solve_steady(self, method="direct", rtol=1e-12):
        """!
        @brief Solve K*theta = Q for the steady temperature rise.
        @param method "direct" (sparse LU) or "cg" (Conjugate Gradients, Jacobi preconditioned).
        @param rtol Relative tolerance for "cg".
        @return Tuple (theta, residual): rise array of shape (layers, ny, nx) and relative residual.
        @throws RuntimeError If the iterative solver does not converge.
        """
        q = self.Q.ravel()
        if method == "direct":
            theta = spla.spsolve(self.K.tocsc(), q)
        elif method == "cg":
            # Jacobi (diagonal) preconditioner keeps CG cheap and robust for SPD thermal matrices
            dinv = 1.0 / self.K.diagonal()
            M = spla.LinearOperator(self.K.shape, matvec=lambda x: dinv * x)
            theta, info = spla.cg(self.K, q, rtol=rtol, atol=0.0, maxiter=20000, M=M)
            if info != 0:
                raise RuntimeError(f"CG did not converge (info={info})")
        else:
            raise ValueError("method must be 'direct' or 'cg'")
        res = np.linalg.norm(self.K @ theta - q) / max(np.linalg.norm(q), 1e-300)
        return theta.reshape(self.nl, self.ny, self.nx), float(res)

    def power_out(self, theta):
        """!
        @brief Heat leaving the board through every path for a given temperature rise.
        @param theta Rise array of shape (layers, ny, nx).
        @return Dict with keys top, bottom, sinks, sides in watts.
        """
        return {
            "top": float((self.g_top * theta).sum()),
            "bottom": float((self.g_bottom * theta).sum()),
            "sinks": float((self.g_sink * theta).sum()),
            "sides": float((self.g_side * theta).sum()),
        }


def _result_from_theta(net, theta, residual, model="fvm"):
    """!
    @brief Package a temperature-rise field as a SteadyResult.
    @param net The Network that produced it.
    @param theta Rise array (layers, ny, nx) in kelvin.
    @param residual Relative residual of the linear solve.
    @param model Model name to store.
    @return SteadyResult with absolute temperatures.
    """
    amb = net.problem.board.ambient
    T = theta + amb
    L = net.nl
    k = int(np.argmax(T))
    l, i, j = np.unravel_index(k, T.shape)
    return SteadyResult(
        model=model, ambient=amb, power_in=float(net.Q.sum()),
        t_max=float(T.max()), t_min=float(T.min()), t_mean=float(T.mean()),
        layer_mean=[float(T[n].mean()) for n in range(L)],
        t_max_location=(int(l), (j + 0.5) * net.dx, (i + 0.5) * net.dy),
        T=T, dx=net.dx, dy=net.dy, power_out=net.power_out(theta), residual=residual,
        extras={"cells": float(T.size)},
    )


def solve_steady(problem, cell_mm=2.0, method="direct"):
    """!
    @brief Steady-state FVM solution of a problem.
    @param problem A Problem.
    @param cell_mm Target cell size in millimetres (the grid is nx = round(width / cell)).
    @param method "direct" or "cg".
    @return SteadyResult.
    """
    b = problem.board
    nx = max(int(round(b.width * 1000.0 / cell_mm)), 2)
    ny = max(int(round(b.height * 1000.0 / cell_mm)), 2)
    net = Network(problem, nx, ny)
    theta, res = net.solve_steady(method=method)
    return _result_from_theta(net, theta, res)


def solve_transient(problem, t_end, n_out=40, cell_mm=2.0, substeps=4, theta_scheme=1.0,
                    log_times=True):
    """!
    @brief Transient response to a power step starting from a board at ambient temperature.
    @details Uses the theta-method: (C/dt + theta*K) x1 = (C/dt - (1-theta)*K) x0 + Q.
             theta = 1 is implicit Euler (robust), theta = 0.5 is Crank-Nicolson (more accurate).
             Both are unconditionally stable for the diffusion equation.
    @param problem A Problem.
    @param t_end Final time in seconds.
    @param n_out Number of output times (excluding t = 0).
    @param cell_mm Target cell size in millimetres.
    @param substeps Implicit steps taken between two output times.
    @param theta_scheme 1.0 for implicit Euler, 0.5 for Crank-Nicolson.
    @param log_times If True the output times are logarithmically spaced (resolves fast and slow parts).
    @return TransientResult.
    """
    b = problem.board
    nx = max(int(round(b.width * 1000.0 / cell_mm)), 2)
    ny = max(int(round(b.height * 1000.0 / cell_mm)), 2)
    net = Network(problem, nx, ny)
    steady_theta, _ = net.solve_steady()
    if log_times:
        times = np.concatenate([[0.0], np.geomspace(t_end / 1e4, t_end, n_out)])
    else:
        times = np.linspace(0.0, t_end, n_out + 1)

    N = net.nl * ny * nx
    Cd = net.C.ravel()
    q = net.Q.ravel()
    x = np.zeros(N)                                    # Rise above ambient, starts at zero
    frames = [x.reshape(net.nl, ny, nx) + b.ambient]
    factor_cache = {}
    for k in range(1, len(times)):
        dt = (times[k] - times[k - 1]) / substeps
        key = round(dt, 12)
        if key not in factor_cache:
            # One LU factorisation per distinct step size, reused for all substeps
            A = (sp.diags(Cd / dt) + theta_scheme * net.K).tocsc()
            B = (sp.diags(Cd / dt) - (1.0 - theta_scheme) * net.K).tocsr()
            factor_cache[key] = (spla.splu(A), B)
        lu, B = factor_cache[key]
        for _ in range(substeps):
            x = lu.solve(B @ x + q)
        frames.append(x.reshape(net.nl, ny, nx) + b.ambient)
    frames = np.asarray(frames)
    return TransientResult(
        times=times, t_max=frames.reshape(len(times), -1).max(axis=1),
        t_mean=frames.reshape(len(times), -1).mean(axis=1), frames=frames,
        steady_t_max=float(steady_theta.max() + b.ambient), ambient=b.ambient,
    )
