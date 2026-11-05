#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file local_modal.py
@brief Prototype of the Analytic transient with vias and heatsinks kept LOCAL: a coupled modal system on the lowest K x K modes, the uniform board above them.

@details The program smears vias and heatsinks over the board in the transient and corrects one factor (analytic._calibrated_dynamics). Here the local conductances of
         the steady model (tile conductance matrix C of solve_steady) enter the modal equations through the same projection that the steady Woodbury step uses.
         With the coefficients a_mn of the board expansion theta_l = sum a_mn phi_m(x) phi_n(y), the Galerkin equations are

             Cap a' + ( A_mn + (D^2 / W H) P^T C P ) a = q,         D_mn = sqrt(e_m e_n),  e = L / norm  (the weights ex, ey of the program),

         with P[(r, l), (m, n, l)] = Ux[m, r] Uy[n, r] the average of the eigenfunctions over tile r (as in solve_steady). With a = D c the matrix is symmetric,
         Cap^(-1/2) [A + (D P^T C P D)/(W H)] Cap^(-1/2) = V diag(lam) V^T, and the step response of the point T is
         z(t) = sum_k (u_k g_k / lam_k)(1 - exp(-lam_k t)). Modes with m or n >= K keep the uniform diagonal system of the program (vias and heatsinks removed).
         The truncation loses the within-tile structure (the constriction of the barrel, the sink edge), so one factor s on C is bisected until the steady
         temperature at the heater's hottest point equals that of analytic.solve_steady (the locally corrected model, the reference of the program's own calibration).
         Prototype for the study: step responses only, no blocks, no edge coefficient.
"""

import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from pcbthermal import analytic, viaconstriction   # noqa: E402
from pcbthermal.geometry import coverage_fraction   # noqa: E402


def local_matrix(problem, sh, bx, by):
    """!
    @brief The tile conductance matrix C and the tile projections of the steady model (same construction as analytic.solve_steady, without blocks).
    @param problem A Problem.
    @param sh Dict from analytic._effective_sheet.
    @param bx Basis along x.
    @param by Basis along y.
    @return Tuple (C (Nt L, Nt L), PX (M, Nt), PY (N, Nt), tw, th, Nt).
    """
    b, m, W, H, L = sh["b"], sh["m"], sh["W"], sh["H"], sh["L"]
    ntx, nty, tw, th = analytic._tile_grid(W, H, sh["lam"])
    vs = viaconstriction.ViaSet(problem) if problem.vias and L > 1 else None
    if vs is not None:
        plan = viaconstriction.plan(problem, vs, (ntx, nty, tw, th), L)
        (ntx, nty, tw, th), weights = plan["grid"], plan["weights"]
    c_via = np.zeros((nty, ntx, max(L - 1, 0)))
    for iv, v in enumerate(problem.vias if vs is not None else []):
        cond = m.k_copper * v.thermal_area(b.via_plating, m.k_copper) / sh["d_diel"]
        for (row, col), w in weights[iv].items():
            c_via[row, col] += w * cond
    g_sink = np.zeros((L, nty, ntx))
    for s in problem.heatsinks:
        g_sink[s.layer] += s.h_extra * tw * th * coverage_fraction(s.polygon, ntx, nty, tw, th, 8)
    active = np.argwhere((c_via.sum(axis=2) > 0) | (g_sink.sum(axis=0) > 0))
    Nt = len(active)
    if Nt == 0:
        return np.zeros((0, 0)), np.zeros((bx.n, 0)), np.zeros((by.n, 0)), 0
    PX = np.stack([bx.project(c * tw, (c + 1) * tw) for _, c in active], axis=1) / tw
    PY = np.stack([by.project(r * th, (r + 1) * th) for r, _ in active], axis=1) / th
    C = np.zeros((Nt * L, Nt * L))
    for r, (row, col) in enumerate(active):
        for l in range(L - 1):
            cv = c_via[row, col, l]
            i1, i2 = r * L + l, r * L + l + 1
            C[i1, i1] += cv
            C[i2, i2] += cv
            C[i1, i2] -= cv
            C[i2, i1] -= cv
        for l in range(L):
            C[r * L + l, r * L + l] += g_sink[l, row, col]
    return C, PX, PY, Nt


class Reduced:
    """!
    @brief The coupled modal system of one heater and its step response.
    """

    def __init__(self, problem, cell_mm=1.0, n_terms=300, K=24, edge=False):
        """!
        @param problem A Problem with ONE heater (unit power is used).
        @param cell_mm Cell in mm.
        @param n_terms Modes per direction of the uniform system.
        @param K Modes per direction of the coupled block.
        @param edge True to add the per-layer edge mismatch S_l (beta_l - beta0) (closed integral of phi phi') to the coupled block (see the module description).
        """
        self.K = K
        d0 = analytic._modal_dynamics(problem, cell_mm, n_terms, via_scale=0.0, heatsink_scale=0.0)   # the board without vias and heatsinks
        sh = d0
        self.d0, self.sh = d0, sh
        L, W, H = sh["L"], sh["W"], sh["H"]
        bx, by = d0["bases"]
        self.L = L
        C, PX, PY, Nt = local_matrix(problem, analytic._effective_sheet(problem, cell_mm), bx, by)   # the sheet again: d0['lam'] is the array of decay rates
        self.C = C
        ex, ey = bx.weight[:K], by.weight[:K]
        D = np.sqrt(np.outer(ex, ey))                                           # (K, K)
        # P D: (Nt L, K K L); index of a mode-layer: ((m K + n) L + l)
        PD = np.zeros((Nt * L, K * K * L))
        for l in range(L):
            blk = (PX[:K, None, :] * PY[None, :K, :] * D[:, :, None]).reshape(K * K, Nt)        # (K K, Nt)
            for r in range(Nt):
                PD[r * L + l, l::L] = blk[:, r]
        self.PD = PD
        self.E = None
        if edge and d0["b"].h_side:
            # Edge mismatch in the symmetric c variables: S_l dbeta_l [ Gx (x) I + I (x) Gy ], G[m, m'] = sum_e phi_m(e) phi_m'(e) / sqrt(N_m N_m')
            sh0 = analytic._effective_sheet(problem, cell_mm)
            dbeta = sh0["h_eff"] * sh0["slab"] / sh0["S"] - sh0["beta"]
            Ex, Ey = bx.evaluate([0.0, W])[:, :K], by.evaluate([0.0, H])[:, :K]
            Gx = (Ex / np.sqrt(bx.norm[:K])).T @ (Ex / np.sqrt(bx.norm[:K]))
            Gy = (Ey / np.sqrt(by.norm[:K])).T @ (Ey / np.sqrt(by.norm[:K]))
            Eblk = np.kron(Gx, np.eye(K)) + np.kron(np.eye(K), Gy)                    # (K K, K K), mode index m K + n
            self.E = np.zeros((K * K * L, K * K * L))
            for l in range(L):
                self.E[l::L, l::L] = sh0["S"][l] * dbeta[l] * Eblk
        # Base matrix A of the uniform board for the coupled modes (no vias, no sinks): from the eigen-decomposition of d0 (back, lam), A = back^-T ... use the matrix directly
        A = analytic._modal_matrix(problem, sh, n_terms, 0.0, 0.0)[:K, :K]       # (K, K, L, L)
        self.A = A
        self.c_l = d0["c_l"]
        self.W, self.H = W, H
        # Source vector of the (single) heater and the output row, in the c variables
        q = analytic._heater_unit_sources(problem, bx, by)[0]                    # (M, N, L)
        self.q = q[:K, :K].reshape(K * K * L)
        lay, iy, ix = d0["points"][0]
        wx, wy = bx.at(sh["xs"][ix]), by.at(sh["ys"][iy])
        out = np.zeros((K, K, L))
        out[:, :, lay] = wx[:K, None] * wy[None, :K]
        self.out = (out * D[:, :, None]).reshape(K * K * L)                    # T = out . c
        self.D = np.repeat(D.reshape(-1), L)
        self.point = (lay, iy, ix)
        self.n_terms = n_terms
        self.mask = np.zeros((n_terms, n_terms), dtype=bool)
        self.mask[:K, :K] = True
        # Uniform part above K: coefficient U G of the program's system for the modes outside the block
        self.u_out = d0["U"][0]
        self.g_out = d0["G"][0]
        self.lam_out = d0["lam"]

    def _sym(self, s):
        """!
        @brief The symmetric matrix Cap^-1/2 (A + D P^T s C P D / W H) Cap^-1/2 on the coupled block.
        @param s Factor on the local conductances.
        @return Array (K K L, K K L).
        """
        K, L = self.K, self.L
        n = K * K * L
        M = np.zeros((n, n))
        Ablk = self.A.reshape(K * K, L, L)
        for i in range(K * K):
            M[i * L:(i + 1) * L, i * L:(i + 1) * L] = Ablk[i]
        if self.C.size:
            M += s * (self.PD.T @ self.C @ self.PD) / (self.W * self.H)
        if self.E is not None:
            M += s * self.E
        ci = np.tile(1.0 / np.sqrt(self.c_l), K * K)
        return M * ci[:, None] * ci[None, :]

    def steady_point(self, s):
        """!
        @brief Steady rise (K/W) at the point of the reduced system with the factor s.
        @param s Factor on C.
        @return float Rise per watt.
        """
        K, L = self.K, self.L
        ci = np.tile(1.0 / np.sqrt(self.c_l), K * K)
        Msym = self._sym(s)
        rhs = ci * self.q / self.D
        sol = np.linalg.solve(Msym, rhs)
        coupled = float(np.dot(self.out * ci, sol))
        rest = float(np.sum(self.u_out * self.g_out / self.lam_out * (~self.mask)[:, :, None]))
        return coupled + rest

    def calibrate(self, target):
        """!
        @brief Bisect the factor on C so that the steady rise at the point equals target.
        @param target Steady rise per watt in K/W.
        @return float The factor.
        """
        lo, hi = math.log(0.05), math.log(20.0)
        for _ in range(30):
            mid = 0.5 * (lo + hi)
            if self.steady_point(math.exp(mid)) > target:
                lo = mid
            else:
                hi = mid
        self.s = math.exp(0.5 * (lo + hi))
        return self.s

    def response(self, times):
        """!
        @brief Unit-step response of the point.
        @param times Array of times in seconds.
        @return Tuple (z (nt,), steady rise).
        """
        K, L = self.K, self.L
        ci = np.tile(1.0 / np.sqrt(self.c_l), K * K)
        lam, V = np.linalg.eigh(self._sym(self.s))
        g = V.T @ (ci * self.q / self.D)
        u = (self.out * ci) @ V
        coef = u * g
        rest_c = (self.u_out * self.g_out)[~self.mask[:, :, None].repeat(L, axis=2)]
        rest_l = self.lam_out[~self.mask[:, :, None].repeat(L, axis=2)]
        keep = np.abs(rest_c) > 1e-13 * np.abs(rest_c).max()
        rest_c, rest_l = rest_c[keep], rest_l[keep]
        z = np.array([(coef / lam) @ (1.0 - np.exp(-lam * t)) + (rest_c / rest_l) @ (1.0 - np.exp(-rest_l * t)) for t in times])
        return z, float(np.sum(coef / lam) + np.sum(rest_c / rest_l))


def step_local(problem, cell_mm=1.0, n_terms=300, K=24, times=None, calibrate=True, edge=False, target_solver=None):
    """!
    @brief Unit-step response of the single heater of a problem with the local modal system.
    @param problem A Problem with one heater.
    @param cell_mm Cell in mm.
    @param n_terms Modes of the uniform part.
    @param K Modes per direction of the coupled block.
    @param times Times in seconds (default: log-spaced up to ten board time constants).
    @param calibrate True to match the steady point value of the steady solution with one factor on C (and on the edge matrix).
    @param edge True to add the per-layer edge mismatch to the coupled block.
    @param target_solver Function (problem) -> (T field (L, ny, nx) in degC) giving the steady field to match (default analytic.solve_steady).
    @return Tuple (times, z (1, nt), rth (1,), factor).
    """
    if not (problem.vias or problem.heatsinks) and not edge:
        t, z, rth = analytic.step_responses(problem, cell_mm, n_terms)          # nothing local: the program's uniform system
        return t, z, rth, 1.0
    r = Reduced(problem, cell_mm, n_terms, K, edge)
    s = 1.0
    r.s = 1.0
    if calibrate:
        lay, iy, ix = r.point
        solo = problem
        T = target_solver(solo) if target_solver else analytic.solve_steady(solo, cell_mm=cell_mm, n_terms=n_terms).T
        target = float(T[lay, iy, ix] - problem.board.ambient) / problem.heaters[0].power
        s = r.calibrate(target)
    if times is None:
        tau = float(r.sh["tau"])
        times = np.geomspace(1e-5, 10.0 * tau, 100)
    z, rth = r.response(times)
    return times, z[None, :], np.array([rth]), s
