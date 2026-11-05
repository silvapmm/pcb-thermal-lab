#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file perlayer_local.py
@brief The per-layer edge iteration around the COMPLETE steady solve of the program (vias, heatsinks, Green-function step), on a patched copy.

@details The program's analytic.solve_steady is linear in the modal source q_mn: the uniform solution A a = q, the tile averages y0, the Woodbury solve and the
         response of the injected heat are all linear maps. So the edge-mismatch source qc(a) of lib/robin_perlayer.py can be added to q_mn and the loop
         a = Phi(q_heaters) + Phi(qc(a)) solved with GMRES, Phi the whole program solve. This module builds Phi by patching the SOURCE of analytic.solve_steady at
         import time (three text edits: two new arguments `q_extra` and `no_heater_source`, and a return of the modal coefficients), so the program file is not touched.
"""

import inspect
import os
import sys

import numpy as np
import scipy.sparse.linalg as spla

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from pcbthermal import analytic   # noqa: E402


def _patched():
    """!
    @brief The solve_steady function with an extra modal source and the modal coefficients as an optional result.
    @return Function.
    """
    src = inspect.getsource(analytic.solve_steady)
    src = src.replace("def solve_steady(problem, cell_mm=1.0, n_terms=300, local_corrections=True):",
                      "def solve_steady(problem, cell_mm=1.0, n_terms=300, local_corrections=True, q_extra=None, no_heater_source=False, want_modal=False):", 1)
    old = "        q_mn += ht.power * q_unit\n"
    assert old in src
    src = src.replace(old, "        q_mn += (0.0 if no_heater_source else ht.power) * q_unit\n    if q_extra is not None:\n        q_mn = q_mn + q_extra\n", 1)
    old = "    return SteadyResult(\n"
    assert old in src
    src = src.replace(old, "    if want_modal:\n        return a_mn, bx, by, sh\n" + old, 1)
    g = dict(analytic.__dict__)
    exec(compile(src, "<patched solve_steady>", "exec"), g)
    return g["solve_steady"]


_SOLVE = _patched()


def solve(problem, cell_mm=1.0, n_terms=300, per_layer=True, tol=1e-8):
    """!
    @brief Steady solution with the per-layer Robin edge around the complete program solve.
    @param problem A Problem (vias and heatsinks allowed, no metal blocks).
    @param cell_mm Cell of the sampling grid in mm.
    @param n_terms Modes per direction.
    @param per_layer False for the program's common-beta result (the patched copy without the loop).
    @param tol Relative tolerance of GMRES.
    @return dict: t_max (degC), matvecs.
    """
    a0, bx, by, sh = _SOLVE(problem, cell_mm, n_terms, want_modal=True)
    L, S, slab, b = sh["L"], sh["S"], sh["slab"], sh["b"]
    W, H = sh["W"], sh["H"]
    beta_l = sh["h_eff"] * slab / S
    dbeta = beta_l - sh["beta"]
    Ex, Ey = bx.evaluate([0.0, W]), by.evaluate([0.0, H])
    Nx, Ny = bx.norm, by.norm
    n = [0]

    def qcorr(a):
        """!
        @brief Edge-mismatch modal source.
        @param a Coefficients (M, N, L).
        @return Array (M, N, L).
        """
        out = np.empty_like(a)
        for l in range(L):
            al = a[:, :, l]
            out[:, :, l] = -S[l] * dbeta[l] * ((Ex.T / Nx[:, None]) @ (Ex @ al) + (al @ Ey.T) @ (Ey / Ny[None, :]))
        return out

    a = a0
    if per_layer and not np.allclose(dbeta, 0.0, rtol=0, atol=1e-12 * max(abs(sh["beta"]), 1e-30)):
        shape = a0.shape

        def mv(v):
            """!
            @brief (I - Phi qc) on a flattened vector.
            @param v Flattened coefficients.
            @return Flattened result.
            """
            n[0] += 1
            x = v.reshape(shape)
            resp = _SOLVE(problem, cell_mm, n_terms, q_extra=qcorr(x), no_heater_source=True, want_modal=True)[0]
            return (x - resp).ravel()

        op = spla.LinearOperator((a0.size, a0.size), matvec=mv, dtype=float)
        x, info = spla.gmres(op, a0.ravel(), x0=a0.ravel(), rtol=tol, restart=30, maxiter=30)
        if info != 0:
            raise RuntimeError(f"GMRES did not converge ({info})")
        a = x.reshape(shape)
    cx, cy = bx.evaluate(sh["xs"]), by.evaluate(sh["ys"])
    theta = np.stack([cy @ a[:, :, l].T @ cx.T for l in range(L)])
    return {"t_max": float(theta.max() + b.ambient), "matvecs": n[0], "a": a}
