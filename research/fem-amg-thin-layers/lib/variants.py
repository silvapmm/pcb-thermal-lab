#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file variants.py
@brief The AMG preconditioner variants under test (README section 4), each a name and a pyamg call, plus the timed CG solve that measures them all the same way.
@details pyamg only (MIT, already a dependency). The parameter names follow the pyamg 5.x documentation as remembered; the FIRST run of each family checks them against the installed
         `help(pyamg.smoothed_aggregation_solver)` and a variant that pyamg refuses is recorded as 'refused', not hidden. Written, not run.
"""

import time

import numpy as np
import scipy.sparse.linalg as spla

GS = ("gauss_seidel", {"sweep": "symmetric", "iterations": 1})        # pyamg's default smoother; symmetric sweep keeps the V-cycle SPD for CG
SYM0 = ("symmetric", {"theta": 0.0})                                   # the program's strength measure: every connection is 'strong'

#: name -> dict(builder 'sa' | 'rs' | 'root', kwargs for the pyamg builder, cycle 'V' | 'W' | 'F', note)
VARIANTS = {
    # E0: what the program does today
    "base": dict(builder="sa", kw=dict(symmetry="symmetric", strength=SYM0, max_coarse=200), cycle="V", note="program default"),
    # E1: strength threshold. theta 0 calls every link strong, so the thin-layer anisotropy is invisible to the aggregation (hypothesis, to be measured)
    "sym_t0.01": dict(builder="sa", kw=dict(symmetry="symmetric", strength=("symmetric", {"theta": 0.01}), max_coarse=200), cycle="V", note="theta sweep"),
    "sym_t0.03": dict(builder="sa", kw=dict(symmetry="symmetric", strength=("symmetric", {"theta": 0.03}), max_coarse=200), cycle="V", note="theta sweep"),
    "sym_t0.08": dict(builder="sa", kw=dict(symmetry="symmetric", strength=("symmetric", {"theta": 0.08}), max_coarse=200), cycle="V", note="theta sweep"),
    "sym_t0.25": dict(builder="sa", kw=dict(symmetry="symmetric", strength=("symmetric", {"theta": 0.25}), max_coarse=200), cycle="V", note="pyamg's own default theta"),
    # E2: smoother
    "gs2": dict(builder="sa", kw=dict(symmetry="symmetric", strength=SYM0, max_coarse=200, presmoother=("gauss_seidel", {"sweep": "symmetric", "iterations": 2}),
                                      postsmoother=("gauss_seidel", {"sweep": "symmetric", "iterations": 2})), cycle="V", note="two symmetric sweeps"),
    "jac": dict(builder="sa", kw=dict(symmetry="symmetric", strength=SYM0, max_coarse=200, presmoother=("jacobi", {"omega": 4.0 / 3.0, "iterations": 2}),
                                      postsmoother=("jacobi", {"omega": 4.0 / 3.0, "iterations": 2})), cycle="V", note="weighted Jacobi (omega 4/3 over rho scaling in pyamg)"),
    # E3: prolongation smoothing
    "energy": dict(builder="sa", kw=dict(symmetry="symmetric", strength=SYM0, max_coarse=200, smooth="energy"), cycle="V", note="reviewer: 275 its, 0.5 + 9.5 s"),
    # E4: aggregation
    "lloyd": dict(builder="sa", kw=dict(symmetry="symmetric", strength=("symmetric", {"theta": 0.03}), aggregate="lloyd", max_coarse=200), cycle="V", note="Lloyd clustering"),
    "pairwise": dict(builder="sa", kw=dict(symmetry="symmetric", strength=("symmetric", {"theta": 0.03}), aggregate="pairwise", max_coarse=200), cycle="V", note="pairwise (small aggregates)"),
    # E5: cheaper evolution measure (reviewer: default evolution 37 + 14.5 s, 34 its; k 2 eps 4: 40-45 + 11.5 s, 28 its)
    "evo_k1_e2": dict(builder="sa", kw=dict(symmetry="symmetric", strength=("evolution", {"k": 1, "epsilon": 2.0}), max_coarse=200), cycle="V", note="one smoothing step"),
    "evo_k2_e4": dict(builder="sa", kw=dict(symmetry="symmetric", strength=("evolution", {"k": 2, "epsilon": 4.0}), max_coarse=200), cycle="V", note="reviewer's measured pair"),
    "evo_k1_e8": dict(builder="sa", kw=dict(symmetry="symmetric", strength=("evolution", {"k": 1, "epsilon": 8.0}), max_coarse=200), cycle="V", note="coarser epsilon"),
    # E6: classical Ruge-Stueben and root-node
    "rs": dict(builder="rs", kw=dict(max_coarse=200), cycle="V", note="classical AMG (strength 'classical' theta 0.25)"),
    "root": dict(builder="root", kw=dict(symmetry="symmetric", strength=("symmetric", {"theta": 0.03}), max_coarse=200), cycle="V", note="root-node SA"),
    # E7: cycle and coarse level
    "base_W": dict(builder="sa", kw=dict(symmetry="symmetric", strength=SYM0, max_coarse=200), cycle="W", note="W cycle"),
    "base_c2000": dict(builder="sa", kw=dict(symmetry="symmetric", strength=SYM0, max_coarse=2000), cycle="V", note="direct solve on a larger coarse level"),
}


def make_preconditioner(A, name):
    """!
    @brief Build the hierarchy of a variant and time the setup.
    @param A SPD scipy CSR matrix.
    @param name Key of VARIANTS.
    @return (M, info) with M the LinearOperator for `spla.cg(M=...)`, info a dict with setup_s, levels, op_complexity, grid_complexity; M is None and info['refused'] holds the message when pyamg refuses.
    """
    import pyamg
    spec = VARIANTS[name]
    t0 = time.perf_counter()
    try:
        if spec["builder"] == "sa":
            ml = pyamg.smoothed_aggregation_solver(A, **spec["kw"])
        elif spec["builder"] == "rs":
            ml = pyamg.ruge_stuben_solver(A, **spec["kw"])
        else:
            ml = pyamg.rootnode_solver(A, **spec["kw"])
    except Exception as exc:                                        # a parameter pyamg does not know is a finding, kept in the table
        return None, {"refused": f"{type(exc).__name__}: {exc}"}
    setup = time.perf_counter() - t0
    info = {"setup_s": setup, "levels": len(ml.levels), "op_complexity": float(ml.operator_complexity()), "grid_complexity": float(ml.grid_complexity())}
    return ml.aspreconditioner(cycle=spec["cycle"]), info


def timed_cg(A, rhs, M, tol=1e-10, maxiter=5000, x0=None):
    """!
    @brief Conjugate gradients with the program's tolerance, the iteration count, the wall time and the TRUE relative residual, with the one restart that `femcore.Model.solve` makes.
    @param A SPD scipy CSR matrix.
    @param rhs Right-hand side (n,).
    @param M Preconditioner operator.
    @param tol Relative residual asked of CG (the program: 1e-10).
    @param maxiter Iteration cap (the program: 5000).
    @param x0 Start vector or None.
    @return (x, info) with iterations (both passes added), solve_s, residual (true, relative), converged (bool), restarted (bool).
    """
    count = [0]

    def tick(_xk):
        count[0] += 1

    bn = float(np.linalg.norm(rhs))
    t0 = time.perf_counter()
    x, flag = spla.cg(A, rhs, x0=x0, rtol=tol, maxiter=maxiter, M=M, callback=tick)
    restarted = False
    res = float(np.linalg.norm(A @ x - rhs)) / bn
    if flag == 0 and res > max(1e-8, 100 * tol):                    # the program's restart on a drifted recursive residual
        x, flag = spla.cg(A, rhs, x0=x, rtol=tol, maxiter=maxiter, M=M, callback=tick)
        restarted = True
        res = float(np.linalg.norm(A @ x - rhs)) / bn
    return x, {"iterations": count[0], "solve_s": time.perf_counter() - t0, "residual": res, "converged": flag == 0 and res <= max(1e-8, 100 * tol), "restarted": restarted}
