#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file robin_perlayer.py
@brief Prototype of the per-layer edge treatment of the Analytic steady model: the Robin condition of every layer, iterated on the common-beta modal solution.

@details The program expands every layer in the eigenfunctions of ONE edge parameter beta0 = h_side sum(s_l) / sum(S_l); layer l has beta_l = h_side s_l / S_l. The weak
         form of layer l in the basis of beta0 (eigenfunctions phi with d phi/dn = -beta0 phi on the edge, -laplacian phi = lam^2 phi) is, by Green's identity twice,

             S_l [ lam_mn^2 N_m N_n a_l,mn + (beta_l - beta0) closed-integral( theta_l phi_m phi_n ) ] + ( face and gap terms ) = integral( q phi_m phi_n ),

         N the squared norms. The closed integral over the four sides needs only the values of theta_l on the sides: along the sides x = 0, W the orthogonality of
         the y eigenfunctions gives sum_e phi_m(x_e) (sum_m' phi_m'(x_e) a_m'n) N_n, so with the norms divided out the extra source of the modal system is

             qc_l,mn = - S_l (beta_l - beta0) [ sum_e phi_m(x_e) / N_m (sum_m' phi_m'(x_e) a_l,m'n)  +  sum_e phi_n(y_e) / N_n (sum_n' phi_n'(y_e) a_l,mn') ].

         The fixed point a = Ainv (q + qc(a)) (the program's modal solve is Ainv) is solved with GMRES on the vector a, one application = one modal solve plus four small
         matrix products. For layers with equal slab / S the mismatch is zero and the result is the program's, bit for bit.
         This module handles the board WITHOUT vias and heatsinks (the Green-function step is linear in the modal source, so the same loop can wrap it: INTEGRATION.md).
"""

import os
import sys

import numpy as np
import scipy.sparse.linalg as spla

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from pcbthermal import analytic   # noqa: E402


def solve(problem, cell_mm=1.0, n_terms=300, per_layer=True, tol=1e-9, beta_rule="program"):
    """!
    @brief Steady solution of a uniform board with the per-layer Robin edge.
    @param problem A Problem without vias and heatsinks.
    @param cell_mm Cell of the sampling grid in mm.
    @param n_terms Modes per direction.
    @param per_layer True for the per-layer correction; False gives the program's common-beta solution.
    @param tol Relative tolerance of GMRES.
    @param beta_rule "program" (flux-conserving common beta, as analytic._effective_sheet) or "heated" (beta of the layer carrying the most power).
    @return dict: t_max (degC), iterations, beta (per layer), beta0, a (M, N, L), sh, p_sides (W), p_faces (W), balance.
    """
    problem = problem.drop_off_board_vias()
    sh = analytic._effective_sheet(problem, cell_mm)
    b, W, H, L, S, slab = sh["b"], sh["W"], sh["H"], sh["L"], sh["S"], sh["slab"]
    h_eff = sh["h_eff"]
    beta_l = h_eff * slab / S
    beta0 = sh["beta"]
    if beta_rule == "heated":
        beta0 = float(beta_l[0])
        sh = dict(sh)
        sh["beta"] = beta0
        sh.pop(("bases", int(n_terms)), None)
    bx, by = analytic._bases(sh, n_terms)
    M = N = n_terms
    ex, ey = bx.weight, by.weight
    q = np.zeros((M, N, L))
    for ht, qu in zip(problem.heaters, analytic._heater_unit_sources(problem, bx, by)):
        q += ht.power * qu
    k2 = bx.eig2[:, None] + by.eig2[None, :]
    h_l = np.zeros(L)
    h_l[0] += b.h_top
    h_l[L - 1] += b.h_bottom
    g = sh["g_diel"]
    A = np.zeros((M, N, L, L))
    for l in range(L):
        A[:, :, l, l] = S[l] * k2 + h_l[l]
        if l > 0:
            A[:, :, l, l] += g[l - 1]
            A[:, :, l, l - 1] -= g[l - 1]
        if l < L - 1:
            A[:, :, l, l] += g[l]
            A[:, :, l, l + 1] -= g[l]
    Ainv = np.linalg.inv(A)
    a0 = np.einsum("mnlk,mnk->mnl", Ainv, q)
    Ex, Ey = bx.evaluate([0.0, W]), by.evaluate([0.0, H])                       # (2, M), (2, N)
    Nx, Ny = bx.norm, by.norm
    dbeta = beta_l - beta0
    its = [0]

    def qcorr(a):
        """!
        @brief Extra modal source of the edge mismatch.
        @param a Modal coefficients (M, N, L).
        @return Array (M, N, L).
        """
        out = np.empty_like(a)
        for l in range(L):
            al = a[:, :, l]
            qx = (Ex.T / Nx[:, None]) @ (Ex @ al)
            qy = ((al @ Ey.T) @ (Ey / Ny[None, :]))
            out[:, :, l] = -S[l] * dbeta[l] * (qx + qy)
        return out

    if not per_layer or np.allclose(dbeta, 0.0, rtol=0, atol=1e-12 * max(abs(beta0), 1e-30)):
        a = a0
    else:
        shape = a0.shape

        def mv(v):
            """!
            @brief (I - Ainv qc) applied to a flattened vector.
            @param v Flattened coefficients.
            @return Flattened result.
            """
            its[0] += 1
            a = v.reshape(shape)
            return (a - np.einsum("mnlk,mnk->mnl", Ainv, qcorr(a))).ravel()

        op = spla.LinearOperator((a0.size, a0.size), matvec=mv, dtype=float)
        x, info = spla.gmres(op, a0.ravel(), x0=a0.ravel(), rtol=tol, restart=40, maxiter=40)
        a = x.reshape(shape)
        if info != 0:
            raise RuntimeError(f"GMRES did not converge ({info})")
    xs, ys = sh["xs"], sh["ys"]
    cx, cy = bx.evaluate(xs), by.evaluate(ys)
    theta = np.stack([cy @ a[:, :, l].T @ cx.T for l in range(L)])
    # Heat balance: faces (plan mean) plus the true per-layer edge loss  h_side s_l * integral of the layer rise along the sides  (= S_l beta_l * the edge integral)
    mean = [analytic._plan_mean(bx, by, a[:, :, k]) for k in range(L)]
    p_faces = float(b.h_top * W * H * mean[0] + b.h_bottom * W * H * mean[L - 1])
    p_sides = float(sum(analytic._edge_loss(bx, by, a[:, :, k], S[k], beta_l[k]) for k in range(L)))
    return {"t_max": float(theta.max() + b.ambient), "iterations": its[0], "beta_l": beta_l, "beta0": beta0, "a": a, "sh": sh, "p_sides": p_sides,
            "p_faces": p_faces, "power": problem.total_power(), "balance": (p_sides + p_faces) / problem.total_power()}
