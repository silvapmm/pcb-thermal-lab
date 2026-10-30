#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_failure.py
@brief Why does the program's red-black SOR fail with the mean-potential via couplings? The failure on simple boards, its cause and a closed form.
@details Four parts, simple cases first (the maintainer's rule), each isolating one effect:
         A. a hand-made 2 layers x 2 cells toy with one via over both cells: a closed form of the temperature of the direct solution and of the fixed point of the program's SOR;
         B. structure of the matrix: signs of the via entries, row dominance, positive definiteness, spectral radii of the iteration matrices (small boards, dense);
         C. the fixed point of the program's SOR is the solution of the matrix with the via off-diagonals dropped (checked on a board);
         D. the program's SOR against the direct solver on the unit cell, the lone via, a row of three and the 3 x 3 array.
         Run from the repository root: `.venv/bin/python research/sor-with-via-couplings/scripts/study_failure.py` (about three minutes; part D runs the program's 200 000-sweep limit on the 3 x 3 board).
"""

import json
import os
import sys

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import boards as bd                                                         # noqa: E402
import sorvia as sv                                                         # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")


def part_a():
    """!
    @brief The toy: closed forms against the numbers.
    @return dict of numbers for the results file.
    """
    print("\nA. Toy 2 layers x 2 cells, one via over both cells (weights 1/2, 1/2), uniform source q/2 in each top cell")
    gx, gz, gv, ga, q = 2.0, 3.0, 5.0, 0.5, 1.0
    t = bd.toy_two_layers(gx, gz, gv, ga, q)
    rhs = np.array([q / 2, q / 2, 0.0, 0.0])
    exact = np.linalg.solve(t["K"], rhs)
    fixed = np.linalg.solve(t["Kst"], rhs)
    # Closed form with equal temperatures in the two cells of a layer: bottom b = (q/2)/ga, top t = b + (q/2)/(gz + gv/2)
    b_cf = (q / 2) / ga
    t_cf = b_cf + (q / 2) / (gz + gv / 2)
    # Program fixed point: the via keeps only its diagonal gv/4 per cell (a leak to nowhere): 2 x 2 solve of
    # (gz + gv/4) t - gz b = q/2 ; -gz t + (gz + ga + gv/4) b = 0
    M = np.array([[gz + gv / 4, -gz], [-gz, gz + ga + gv / 4]])
    t_fp, b_fp = np.linalg.solve(M, [q / 2, 0.0])
    print(f"   direct          top {exact[0]:.6f}  bottom {exact[2]:.6f}   closed form top {t_cf:.6f}  bottom {b_cf:.6f}")
    print(f"   program's SOR   top {fixed[0]:.6f}  bottom {fixed[2]:.6f}   closed form top {t_fp:.6f}  bottom {b_fp:.6f}")
    # Iterate the program's rule (red-black on the toy: cells (0,0) and (1,1) red, (0,1) and (1,0) black; there is no same-colour coupling in the stencil)
    K, Kst = t["K"], t["Kst"]
    order = [[0, 3], [1, 2]]                                                # unknowns: top a, top b, bottom a, bottom b; colour = (layer + cell) parity
    x = np.zeros(4)
    for _ in range(3000):
        for grp in order:
            for i in grp:
                x[i] += 1.2 * ((rhs[i] - Kst[i] @ x + Kst[i, i] * x[i]) / Kst[i, i] - x[i])
    print(f"   iterated program rule (3000 sweeps, omega 1.2): top {x[0]:.6f}, residual of the true K {np.linalg.norm(K @ x - rhs):.4f}")
    return {"direct": exact.tolist(), "fixed": fixed.tolist(), "closed_direct": [t_cf, b_cf], "closed_fixed": [t_fp, b_fp]}


def _rho_sweep(net, **kw):
    """!
    @brief Spectral radius of the one-sweep iteration matrix of `RB` (built column by column on the basis vectors, zero right-hand side).
    @param net The network (small).
    @param kw Arguments of `sorvia.RB`.
    @return float.
    """
    rb = sv.RB(net, **kw)
    n = net.K.shape[0]
    G = np.zeros((n, n))
    z = np.zeros(rb.shape)
    for i in range(n):
        e = np.zeros(n)
        e[i] = 1.0
        G[:, i] = rb.sweep(e.reshape(rb.shape), z).ravel()
    return float(np.abs(np.linalg.eigvals(G)).max())


def part_b():
    """!
    @brief Structure of the matrix on small boards.
    @return dict of numbers.
    """
    print("\nB. Structure of K = stencil + via part (copper-filled via, disc footprint at eta = exp(-1/4))")
    print("| board | cell (mm) | N | via entries (+/-) | max row sum / diag | lambda_min(K) | rho Jacobi stencil | rho Jacobi K | rho program sweep | rho lagged sweep |")
    print("| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: |")
    res = {}
    cases = [("unit cell, 2 layers", bd.pc.unit_cell_board(3.5, 0.3, 385.0, layers=2), 0.25),
             ("unit cell, 4 layers", bd.pc.unit_cell_board(3.5, 0.3, 385.0, layers=4), 0.25),
             ("lone via, 2 layers", bd.pc.lone_via_board(10.0, 0.3, 385.0), 0.5)]
    for name, prob, cell in cases:
        net = bd.net_for(prob, cell)
        K = net.K.tocsr()
        Kv = sv.via_matrix(net)
        d = K.diagonal()
        absrow = np.asarray(abs(K - sp.diags(d)).sum(axis=1)).ravel()
        Kd = K.toarray()
        lam = np.linalg.eigvalsh(Kd).min()
        S = sv.stencil_parts(net)["S"]
        Dm = sp.diags(1.0 / d)
        rj_st = np.abs(np.linalg.eigvals((-Dm @ S).toarray())).max()
        rj_k = np.abs(np.linalg.eigvals(np.eye(len(d)) - (Dm @ K).toarray())).max()
        rp = _rho_sweep(net)
        rl = _rho_sweep(net, Kv=Kv)
        print(f"| {name} | {cell} | {K.shape[0]} | {(Kv.data > 0).sum()}/{(Kv.data < 0).sum()} | {(absrow / d).max():.4f} | {lam:.3e} | {rj_st:.5f} | {rj_k:.5f} | {rp:.5f} | {rl:.5f} |")
        res[name] = {"N": K.shape[0], "pos": int((Kv.data > 0).sum()), "neg": int((Kv.data < 0).sum()), "rowdom": float((absrow / d).max()), "lam": float(lam),
                     "rho_jac_stencil": float(rj_st), "rho_jac_K": float(rj_k), "rho_program": rp, "rho_lagged": rl}
    return res


def part_c():
    """!
    @brief The fixed point of the program's SOR is the solution of the matrix with the via off-diagonals dropped.
    @return dict.
    """
    print("\nC. Fixed point of the program's SOR = solution of K_drop (diagonal of K, stencil off-diagonals)")
    prob = bd.pc.lone_via_board(10.0, 0.3, 385.0)
    net = bd.net_for(prob, 0.5)
    K = net.K.tocsr()
    Kdrop = (sp.diags(K.diagonal()) + sv.stencil_parts(net)["S"]).tocsc()
    th_drop = spla.spsolve(Kdrop, net.Q.ravel())
    th_true = spla.spsolve(K.tocsc(), net.Q.ravel())
    rb = sv.RB(net, K=Kdrop)                                                # residual of K_drop: the program's iteration converges on this matrix
    r = rb.solve(net.Q, tol=1e-11, max_iter=60000)
    err = np.abs(r["theta"].ravel() - th_drop).max()
    print(f"   lone via, 0.5 mm: SOR on the program rule, residual measured on K_drop {r['residual']:.1e} after {r['iterations']} sweeps; "
          f"max |SOR - solve(K_drop)| = {err:.2e} K; T_max(K_drop) = {th_drop.max():.3f}, T_max(K) = {th_true.max():.3f} K above ambient")
    return {"err": float(err), "tmax_drop": float(th_drop.max()), "tmax_true": float(th_true.max()), "sweeps": r["iterations"]}


def part_d(max_iter=30000):
    """!
    @brief The program's SOR against the direct solver on simple boards.
    @param max_iter Sweep limit (the program's own is 200 000; the 3 x 3 rows use it).
    @return dict.
    """
    print("\nD. The program's SOR (red-black, residual rule, tol 1e-9) against the direct solver; rise above ambient")
    print("| board | cell (mm) | N | direct T_max (K) | SOR T_max - direct (K) | SOR sweeps | SOR residual | converged |")
    print("| :-- | --: | --: | --: | --: | --: | --: | :-- |")
    res = {}
    P = bd.pc
    cases = [("unit cell, 2 layers", P.unit_cell_board(3.5, 0.3, 385.0, layers=2), 0.25, max_iter),
             ("lone via, 2 layers", P.lone_via_board(10.0, 0.3, 385.0), 0.5, max_iter),
             ("row of 3 vias", P.row_board(n=3, fill_k=385.0), 0.5, max_iter),
             ("3 x 3 array", P.array_board(385.0), 0.5, 200000),
             ("3 x 3 array", P.array_board(385.0), 0.25, 200000)]
    for name, prob, cell, mi in cases:
        net = bd.net_for(prob, cell)
        th, _ = net.solve_steady("direct")
        r = sv.solve_variant(net, "program", max_iter=mi)
        print(f"| {name} | {cell} | {net.K.shape[0]} | {th.max():.3f} | {r['theta'].max() - th.max():+.2f} | {r['iterations']} | {r['residual']:.1e} | {r['converged']} |", flush=True)
        res[f"{name} {cell}"] = {"direct": float(th.max()), "diff": float(r["theta"].max() - th.max()), "sweeps": r["iterations"], "residual": r["residual"], "converged": r["converged"]}
    return res


def main():
    """!
    @brief Run the four parts and save the numbers to out/study_failure.json.
    @return None.
    """
    bd.pc.load_libraries()
    out = {"A": part_a(), "B": part_b(), "C": part_c(), "D": part_d()}
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "study_failure.json"), "w") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
