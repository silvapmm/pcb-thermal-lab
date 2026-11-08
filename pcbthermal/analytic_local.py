#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file analytic_local.py
@brief The Analytic transient with vias and heatsinks kept local: a coupled modal block on the lowest K x K modes, the uniform board above them.

@details The steady Analytic model puts the vias and heatsinks back through a Green-function step on tiles (analytic.solve_steady). In time that step has no counterpart, and
         smearing the elements over the board gives wrong dynamics (docs/validation.md 4.1). Here the tile conductance matrix C of the steady model enters the modal
         equations through the same projection the steady step uses. With the coefficients a_mn of theta_l = sum a_mn phi_m(x) phi_n(y), the Galerkin equations are

             Cap a' + ( A_mn + (D^2 / W H) P^T C P ) a = q,        D_mn = sqrt(e_m e_n),  e = L / norm  (the weights of the series),

         P[(r, l), (m, n, l)] = Ux[m, r] Uy[n, r] the average of the eigenfunctions over tile r. With a = D c the matrix is symmetric and, scaled by Cap^(-1/2), is
         V diag(lam) V^T on the K x K x L unknowns of the block; the step response of a point T is z(t) = sum_k (u_k g_k / lam_k)(1 - exp(-lam_k t)). The modes with m or n
         at or above K keep the diagonal system of the uniform board (the board without vias and heatsinks), so the block eigenvalues, sources and output rows can be
         stored in the same (M, N, L) arrays as the uniform modes and every consumer of the modal state (step responses, profile propagator, animation frames) is unchanged.

         The truncation to K x K modes cannot hold the constriction of the heat on a barrel, which the steady model has through its self-term. One factor s on the VIA
         couplings of C is therefore bisected until the steady rise at the heater's own point equals that of analytic.solve_steady (the heatsink conductances h_extra x tile
         area enter as built: they are exact tile means and have no constriction). With one factor on the whole of C the vias stay too strong and the heatsink too weak when
         both are present (time to 63 % +5 to +32 % of the FVM); on the vias only it is -9 to +1 % (research/analytic-2-6 README 6.3).
"""

import math

import numpy as np
from scipy.optimize import brentq


FACTOR_BRACKET = (0.05, 20.0)      # Range of the calibration factor on the via couplings (a wider need means the truncation is far from the steady model)


class LocalSystem:
    """!
    @brief The coupled modal system of one board with local vias and heatsinks, for any number of sources and output points.
    """

    def __init__(self, A, c_l, ex, ey, PX, PY, Cv, cs, W, H):
        """!
        @param A Uniform modal matrices of the block modes (K, K, L, L) in W/(m2 K) (the board without vias and heatsinks).
        @param c_l Heat capacity per area of every layer in J/(m2 K).
        @param ex Weights e_m = L / norm of the first K modes along x.
        @param ey Weights along y (K,).
        @param PX Average of the first K eigenfunctions along x over each active tile (K, Nt).
        @param PY Average of the first K eigenfunctions along y over each active tile (K, Nt).
        @param Cv Via part of the tile conductance matrix (Nt L, Nt L) in W/K, tile r layer l at row r L + l.
        @param cs Heatsink part of the tile conductance matrix, the diagonal (Nt L,) in W/K.
        @param W Board width in metres.
        @param H Board height in metres.
        """
        K, L = A.shape[0], A.shape[2]
        self.K, self.L = K, L
        self.c_l = np.asarray(c_l, dtype=float)
        n = K * K * L
        self.D = np.repeat(np.sqrt(np.outer(ex, ey)).reshape(-1), L)         # (n,) weight of each mode-layer (a = D c)
        self.ci = np.tile(1.0 / np.sqrt(self.c_l), K * K)                    # (n,) Cap^(-1/2)
        Nt = PX.shape[1]
        # P D: (Nt L, K K L); the column of mode (m, n) and layer l is (m K + n) L + l
        PD = np.zeros((Nt * L, n))
        blk = (PX[:, None, :] * PY[None, :, :] * np.sqrt(np.outer(ex, ey))[:, :, None]).reshape(K * K, Nt)        # (K K, Nt)
        for l in range(L):
            PD[l::L, l::L] = blk.T
        base = np.zeros((n, n))
        Ablk = A.reshape(K * K, L, L)
        for i in range(K * K):
            base[i * L:(i + 1) * L, i * L:(i + 1) * L] = Ablk[i]
        # The projections of the via part and of the heatsink part are formed once, so that the calibration only adds s Qv to the base
        self.Qv = (PD.T @ (Cv @ PD)) / (W * H)
        self.Qs = ((PD * cs[:, None]).T @ PD) / (W * H)
        self.base = base + self.Qs
        self.has_vias = bool(np.any(Cv))
        self.s = 1.0
        self.lam = self.V = None

    def _sym(self, s):
        """!
        @brief The symmetric matrix Cap^-1/2 (A + D P^T (s C_via + C_sink) P D / W H) Cap^-1/2 of the block.
        @param s Factor on the via couplings.
        @return Array (K K L, K K L).
        @throws RuntimeError After release().
        """
        self._require_matrices()
        return (self.base + s * self.Qv) * self.ci[:, None] * self.ci[None, :]

    def steady_point(self, s, q, out):
        """!
        @brief Steady rise at an output point of the coupled block alone (the modes outside it are not included).
        @param s Factor on the via couplings.
        @param q Source of 1 W on the block modes (K, K, L), as heater_unit_sources.
        @param out Output row of the point (K, K, L): the eigenfunctions at the point times D, on the layer of the point.
        @return float Rise per watt in K/W.
        """
        rhs = self.ci * q.reshape(-1) / self.D
        sol = np.linalg.solve(self._sym(s), rhs)
        return float(np.dot(out.reshape(-1) * self.ci, sol))

    def calibrate(self, q, out, target):
        """!
        @brief Choose the factor s on the via couplings so that the block's steady rise at the point equals a target.
        @details The rise falls with s, so a root-finding on log s inside FACTOR_BRACKET; a target outside the bracket takes the end of the bracket and says so (the
                 one-sided calibration of the earlier smeared transient returned silently, docs/validation.md 4.1). Without vias there is nothing to scale and s = 1.
        @param q Source of 1 W on the block modes (K, K, L).
        @param out Output row of the point (K, K, L).
        @param target Wanted steady rise of the block part in K/W (the steady solve's rise minus the part of the modes outside the block).
        @return Tuple (s, ok): the factor and False when the target lay outside the bracket.
        """
        if not self.has_vias:
            self.s = 1.0
            return 1.0, True
        lo, hi = math.log(FACTOR_BRACKET[0]), math.log(FACTOR_BRACKET[1])
        f_lo = self.steady_point(math.exp(lo), q, out) - target          # Strong coupling on the vias: cooler, so f(hi) is the smaller
        f_hi = self.steady_point(math.exp(hi), q, out) - target
        if f_lo < 0.0:
            self.s = math.exp(lo)                                       # Even the weakest coupling is cooler than the target
            return self.s, False
        if f_hi > 0.0:
            self.s = math.exp(hi)
            return self.s, False
        x = brentq(lambda t: self.steady_point(math.exp(t), q, out) - target, lo, hi, xtol=1e-7, rtol=1e-10)
        self.s = math.exp(x)
        return self.s, True

    def decompose(self):
        """!
        @brief Eigen-decomposition of the block with the present factor.
        @return Eigenvalues (K, K, L) in 1/s.
        """
        lam, V = np.linalg.eigh(self._sym(self.s))
        self.lam, self.V = lam, V
        return lam.reshape(self.K, self.K, self.L)

    def release(self):
        """!
        @brief Free the matrices of the calibration once the block is decomposed: the rows, the coefficients and the start state need only the eigenvectors.
        @details The transient keeps one system per heater when the board has vias or heatsinks, and each system held four dense matrices of (K^2 L)^2 doubles (the base,
                 the via and heatsink projections and the eigenvectors; 67 MB each at 8 layers): on six parts of an 8-layer board the step responses peaked 0.9 GB above
                 the smeared transient they replace (review). After this call steady_point, calibrate and decompose raise RuntimeError.
        @return None.
        """
        self.base = self.Qv = self.Qs = None

    def _require_matrices(self):
        """!
        @brief Check that the calibration matrices are still held.
        @return None.
        @throws RuntimeError After release().
        """
        if self.base is None:
            raise RuntimeError("the local system was released after its decomposition: build a new LocalSystem to calibrate again")

    def source_row(self, q):
        """!
        @brief Modal source of a heater of 1 W in the eigen coordinates of the block.
        @param q Source of 1 W on the block modes (K, K, L).
        @return Array (K, K, L): g_k with zeta' = -lam zeta + g P.
        """
        return (self.V.T @ (self.ci * q.reshape(-1) / self.D)).reshape(self.K, self.K, self.L)

    def point_row(self, wx, wy, layer):
        """!
        @brief Row that gives the temperature at a point from the eigen coordinates of the block.
        @param wx The first K eigenfunctions along x at the point (K,).
        @param wy The first K eigenfunctions along y at the point (K,).
        @param layer Layer of the point (0-based).
        @return Array (K, K, L): T = sum(row * zeta).
        """
        out = np.zeros((self.K, self.K, self.L))
        out[:, :, layer] = wx[:, None] * wy[None, :]
        out = (out.reshape(-1) * self.D)
        return ((out * self.ci) @ self.V).reshape(self.K, self.K, self.L)

    def output_row(self, wx, wy, layer):
        """!
        @brief The output row of a point in the original coordinates (the eigenfunctions at the point times D), used by the calibration.
        @param wx The first K eigenfunctions along x at the point (K,).
        @param wy The first K eigenfunctions along y at the point (K,).
        @param layer Layer of the point (0-based).
        @return Array (K, K, L).
        """
        out = np.zeros((self.K, self.K, self.L))
        out[:, :, layer] = wx[:, None] * wy[None, :]
        return (out.reshape(-1) * self.D).reshape(self.K, self.K, self.L)

    def coefficients(self, zeta):
        """!
        @brief Modal coefficients a_mn of the block from the eigen coordinates.
        @param zeta Eigen coordinates (K, K, L).
        @return Array (K, K, L) of a_mn in K (the field is sum a_mn phi_m phi_n).
        """
        return (self.D * self.ci * (self.V @ zeta.reshape(-1))).reshape(self.K, self.K, self.L)

    def uniform_state(self, rise):
        """!
        @brief Eigen coordinates of a uniform rise of the whole board (only the constant mode of the series carries it).
        @param rise Rise above ambient in K.
        @return Array (K, K, L).
        """
        a = np.zeros((self.K, self.K, self.L))
        a[0, 0, :] = rise
        return (self.V.T @ (np.sqrt(np.tile(self.c_l, self.K * self.K)) * a.reshape(-1) / self.D)).reshape(self.K, self.K, self.L)
