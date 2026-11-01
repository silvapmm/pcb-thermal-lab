#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_variants.py
@brief Which fix lets the red-black SOR carry the mean-potential via couplings? Convergence, accuracy and cost of the variants on simple boards first.
@details Variants (names of `lib/sorvia.py`): program (the failure), lagged (a), block (c), woodbury (b), SSOR-preconditioned CG (d), the point link as an approximation (e);
         (f), refusing SOR on boards with vias, has nothing to measure. Parts:
         1. the table of the boards (unit cell, lone via, row of three, 3 x 3 array): sweeps and difference from the direct solver for every variant, with the no-via board as the reference sweep count;
         2. the relaxation factor omega on the 3 x 3 array;
         3. the stiffness of the via part: K_via multiplied by s from 0.01 to 1e4 (one fixed geometry);
         4. the point link for SOR (e): the difference between the SOR on the point treatment and the direct solution of the mean-potential treatment;
         5. cost: direct, CG (Jacobi) and SSOR-CG times and iterations at the same tolerance.
         The convergence histories are saved to out/study_variants.json for `make_figures.py`.
         Run from the repository root: `.venv/bin/python research/sor-with-via-couplings/scripts/study_variants.py` (about ten minutes).
"""

import json
import os
import sys
import time

import numpy as np
import scipy.sparse.linalg as spla

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import boards as bd                                                         # noqa: E402
import sorvia as sv                                                         # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")
TOL = 1e-9
CAP = 200000


def cases():
    """!
    @brief The boards of the study, simple first: (name, Problem, cell sizes in mm).
    @return list.
    """
    P = bd.pc
    return [("unit cell, 2 layers", P.unit_cell_board(3.5, 0.3, 385.0, layers=2), (0.25,)),
            ("unit cell, 4 layers", P.unit_cell_board(3.5, 0.3, 385.0, layers=4), (0.25,)),
            ("lone via, 2 layers", P.lone_via_board(10.0, 0.3, 385.0), (0.5, 0.25)),
            ("row of 3 vias", P.row_board(n=3, fill_k=385.0), (0.5,)),
            ("3 x 3 array", P.array_board(385.0), (0.5, 0.25))]


def cg_jacobi(net, tol=TOL):
    """!
    @brief The program's CG (Jacobi preconditioner) with an iteration counter.
    @param net The network.
    @param tol Relative tolerance.
    @return dict(iterations, seconds, theta).
    """
    K = net.K.tocsr()
    dinv = 1.0 / K.diagonal()
    cnt = [0]
    t0 = time.perf_counter()
    th, _ = spla.cg(K, net.Q.ravel(), rtol=tol, atol=0.0, maxiter=20000, M=spla.LinearOperator(K.shape, matvec=lambda x: dinv * x),
                    callback=lambda x: cnt.__setitem__(0, cnt[0] + 1))
    return {"iterations": cnt[0], "seconds": time.perf_counter() - t0, "theta": th.reshape(net.nl, net.ny, net.nx)}


def part1(save):
    """!
    @brief Variants against the direct solver on every board.
    @param save dict that receives the numbers and histories.
    @return None.
    """
    print("\n1. Variants at the program's omega, tol 1e-9; sweeps (or CG iterations), max |field - direct| in K and T_max difference")
    print("| board | cell (mm) | N | no-via sweeps | program | lagged (a) | block (c) | woodbury (b) | SSOR-CG nat. (d) | SSOR-CG r-b (d) | CG Jacobi |")
    print("| :-- | --: | --: | --: | :-- | :-- | :-- | :-- | :-- | :-- | :-- |")
    for name, prob, cells in cases():
        for cell in cells:
            net = bd.net_for(prob, cell)
            th, _ = net.solve_steady("direct")
            base = sv.RB(bd.net_for(bd.without_vias(prob), cell, "point")).solve(bd.net_for(bd.without_vias(prob), cell, "point").Q, TOL, CAP)
            row, rec = {}, {"N": int(net.K.shape[0]), "base_sweeps": base["iterations"], "base_history": base["history"]}
            for v in ("program", "lagged", "block", "woodbury"):
                if v == "woodbury" and net.K.shape[0] > 8000:
                    row[v] = "not run"
                    continue
                r = sv.solve_variant(net, v, max_iter=CAP)
                d = float(np.abs(r["theta"] - th).max())
                row[v] = f"{r['iterations']}{'' if r['converged'] else ' (no conv.)'}; {d:.1e}"
                rec[v] = {"iterations": r["iterations"], "converged": bool(r["converged"]), "maxdiff": d, "dtmax": float(r["theta"].max() - th.max()),
                          "residual": r["residual"], "seconds": r["seconds"], "history": r["history"][:: max(1, len(r["history"]) // 400)]}
            for o in ("natural", "redblack"):
                r = sv.ssor_cg(net, 1.0, TOL, order=o)
                row["ssor_" + o] = f"{r['iterations']}; {np.abs(r['theta'] - th).max():.1e}"
                rec["ssor_" + o] = {"iterations": r["iterations"], "maxdiff": float(np.abs(r["theta"] - th).max()), "seconds": r["seconds"]}
            c = cg_jacobi(net)
            row["cg"] = f"{c['iterations']}; {np.abs(c['theta'] - th).max():.1e}"
            rec["cg"] = {"iterations": c["iterations"], "maxdiff": float(np.abs(c["theta"] - th).max()), "seconds": c["seconds"]}
            print(f"| {name} | {cell} | {net.K.shape[0]} | {base['iterations']} | {row['program']} | {row['lagged']} | {row['block']} | {row['woodbury']} | "
                  f"{row['ssor_natural']} | {row['ssor_redblack']} | {row['cg']} |", flush=True)
            save[f"{name} {cell}"] = rec


def part2(save):
    """!
    @brief The relaxation factor on the 3 x 3 array at 0.5 mm.
    @param save dict that receives the numbers.
    @return None.
    """
    print("\n2. Relaxation factor on the 3 x 3 array, 0.5 mm (sweeps to 1e-9; '-' = not converged in 20000)")
    net = bd.net_for(bd.pc.array_board(385.0), 0.5)
    base = bd.net_for(bd.without_vias(bd.pc.array_board(385.0)), 0.5, "point")
    print("| omega | no-via board | lagged (a) | block (c) |")
    print("| --: | --: | --: | --: |")
    rows = {}
    for om in (1.0, 1.5, 1.8, 1.9, 1.95, 1.97, 1.98, 1.99):
        out = []
        for key, f in (("base", lambda: sv.RB(base, omega=om).solve(base.Q, TOL, 20000)),
                       ("lagged", lambda: sv.solve_variant(net, "lagged", omega=om, max_iter=20000)),
                       ("block", lambda: sv.solve_variant(net, "block", omega=om, max_iter=20000))):
            r = f()
            out.append(r["iterations"] if r["converged"] else None)
        rows[om] = out
        print(f"| {om} | {out[0] or '-'} | {out[1] or '-'} | {out[2] or '-'} |", flush=True)
    save["omega"] = {str(k): v for k, v in rows.items()}


def part3(save):
    """!
    @brief Stiffness of the via part: K_via times s on the 3 x 3 array at 0.5 mm and on the unit cell with four layers.
    @param save dict that receives the numbers.
    @return None.
    """
    print("\n3. Stiffness of the via part: K = A + s K_via (3 x 3 array 0.5 mm, program's omega); sweeps and max |field - direct| (K); '-' = no convergence in 20000")
    print("| s | lagged (a) sweeps | lagged diff | block (c) sweeps | block diff |")
    print("| --: | --: | --: | --: | --: |")
    net0 = bd.net_for(bd.pc.array_board(385.0), 0.5)
    rows = {}
    for s in (0.01, 0.1, 1.0, 10.0, 100.0, 1e3, 1e4):
        net = bd.scaled(net0, s)
        th = spla.spsolve(net.K, net.Q.ravel())
        cells = []
        for v in ("lagged", "block"):
            try:
                r = sv.solve_variant(net, v, max_iter=20000)
                ok = r["converged"]
                cells += [r["iterations"] if ok else None, float(np.abs(r["theta"].ravel() - th).max())]
            except FloatingPointError:
                cells += [None, float("nan")]
        rows[s] = cells
        print(f"| {s:g} | {cells[0] or '-'} | {cells[1]:.1e} | {cells[2] or '-'} | {cells[3]:.1e} |", flush=True)
    save["stiffness"] = {str(k): v for k, v in rows.items()}


def part4(save):
    """!
    @brief The point link as the approximation for SOR (e): SOR on the program's own via treatment against the direct solution of the mean-potential one.
    @param save dict that receives the numbers.
    @return None.
    """
    print("\n4. (e) SOR on the program's point link: the field it converges to against the direct solution of the mean-potential treatment (T_max difference, K)")
    print("| board | cell (mm) | point link SOR sweeps | SOR(point) - direct(point) (K) | direct(point) - direct(mean potential) (K) | direct(mean) T_max (K) |")
    print("| :-- | --: | --: | --: | --: | --: |")
    rows = {}
    for name, prob, cells in cases():
        for cell in cells:
            netp = bd.net_for(prob, cell, "point")
            netm = bd.net_for(prob, cell, "mw_disc")
            thp, _ = netp.solve_steady("direct")
            thm, _ = netm.solve_steady("direct")
            r = sv.solve_variant(netp, "program", max_iter=CAP)
            rows[f"{name} {cell}"] = [r["iterations"], float(r["theta"].max() - thp.max()), float(thp.max() - thm.max()), float(thm.max())]
            print(f"| {name} | {cell} | {r['iterations']}{'' if r['converged'] else ' (no conv.)'} | {r['theta'].max() - thp.max():+.1e} | {thp.max() - thm.max():+.2f} | {thm.max():.2f} |", flush=True)
    save["point"] = rows


def main():
    """!
    @brief Run the five parts and save out/study_variants.json.
    @return None.
    """
    bd.pc.load_libraries()
    save = {}
    for f in (part1, part2, part3, part4):
        f(save)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "study_variants.json"), "w") as fh:
        json.dump(save, fh)


if __name__ == "__main__":
    main()
