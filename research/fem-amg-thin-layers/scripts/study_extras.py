#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_extras.py
@brief Question: do the free or baseline knobs of README E1b (CG tolerance), E9 (diagonal scaling), E10 (ILU, column block-Jacobi) and E11 (candidate improvement off) change the total time of the FEM solve?
@details One child process per (case, extra), lock as the other studies; lines appended to out/extras.jsonl. The reference field is the program's default solve (out/ref_<case>@<cell>.npy made by
         study_amg_variants.py 'base'). Usage (repository root):

         .venv/bin/python research/fem-amg-thin-layers/scripts/study_extras.py --lock <scratchpad>/heavy_lock --cases example_2mm example_1mm
         .venv/bin/python research/fem-amg-thin-layers/scripts/study_extras.py --table
"""

import argparse
import json
import os
import resource
import subprocess
import sys
import time

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(FOLDER, "lib"))
OUT = os.path.join(FOLDER, "out")
LOG = os.path.join(OUT, "extras.jsonl")
EXTRAS = ["rtol1e-8", "rtol1e-9", "scaled", "scaled_rtol1e-9", "cand_none", "ilu", "colblock", "colblock_amg", "colblock_amg_mult"]


def column_ids(model):
    """!
    @brief The vertical column (same x, y) of every unknown, in the unknown order of `Model.assemble` (unused nodes dropped).
    @param model femcore.Model.
    @return numpy.ndarray int (n,) column index.
    """
    used = np.zeros(model.nodes.shape[0], bool)
    used[model.elems.ravel()] = True
    xy = np.round(model.nodes[used][:, :2] / 1e-9).astype(np.int64)         # nm, so equal columns match exactly
    _, inv = np.unique(xy, axis=0, return_inverse=True)
    return inv.ravel()


def run_one(case, extra):
    """!
    @brief Solve one case with one extra and measure it.
    @param case Key of cases.CASES.
    @param extra One of EXTRAS.
    @return dict as study_amg_variants.run_one (case, variant=extra, n, setup_s, iterations, solve_s, total_s, residual, max_dT_vs_base, peak_gb).
    """
    import cases
    import pyamg
    import variants
    c = cases.build(case)
    A, rhs, n = c["A"], c["rhs"], c["n"]
    out = {"case": case, "variant": extra, "n": n, "cell_mm": c["cell_mm"]}
    tol = {"rtol1e-8": 1e-8, "rtol1e-9": 1e-9, "scaled_rtol1e-9": 1e-9}.get(extra, 1e-10)
    kw = dict(variants.VARIANTS["base"]["kw"])
    t0 = time.perf_counter()
    scale = None
    As, bs = A, rhs
    if extra.startswith("scaled"):
        d = 1.0 / np.sqrt(A.diagonal())                                    # symmetric Jacobi scaling D^-1/2 A D^-1/2
        scale = d
        As = (sp.diags(d) @ A @ sp.diags(d)).tocsr()
        bs = d * rhs
    if extra == "cand_none":
        kw["improve_candidates"] = None
    if extra == "ilu":
        ilu = spla.spilu(A.tocsc(), drop_tol=1e-4, fill_factor=10)
        M = spla.LinearOperator(A.shape, ilu.solve)
    elif extra in ("colblock", "colblock_amg", "colblock_amg_mult"):
        col = column_ids(c["model"])
        coo = A.tocoo()
        keep = col[coo.row] == col[coo.col]
        P = sp.csc_matrix((coo.data[keep], (coo.row[keep], coo.col[keep])), shape=A.shape)
        lu = spla.splu(P)
        Mb = spla.LinearOperator(A.shape, lu.solve)
        if extra == "colblock":
            M = Mb
        elif extra == "colblock_amg_mult":                                  # symmetric multiplicative: column solve, AMG on the residual, column solve (SPD)
            ml = pyamg.smoothed_aggregation_solver(A, **kw)
            Ma = ml.aspreconditioner(cycle="V")

            def apply(r):
                x = Mb.matvec(r)
                x = x + Ma.matvec(r - A @ x)
                return x + Mb.matvec(r - A @ x)

            M = spla.LinearOperator(A.shape, apply)
        else:                                                              # additive combination of the AMG V cycle and the column solve (still SPD)
            ml = pyamg.smoothed_aggregation_solver(A, **kw)
            Ma = ml.aspreconditioner(cycle="V")
            M = spla.LinearOperator(A.shape, lambda r: Ma.matvec(r) + Mb.matvec(r))
    else:
        ml = pyamg.smoothed_aggregation_solver(As, **kw)
        M = ml.aspreconditioner(cycle="V")
    out["setup_s"] = time.perf_counter() - t0
    count = [0]

    def tick(_):
        count[0] += 1

    t1 = time.perf_counter()
    x, flag = spla.cg(As, bs, rtol=tol, maxiter=5000, M=M, callback=tick)
    if scale is not None:
        x = scale * x
    out["solve_s"] = time.perf_counter() - t1
    out["iterations"] = count[0]
    out["total_s"] = out["setup_s"] + out["solve_s"]
    out["residual"] = float(np.linalg.norm(A @ x - rhs) / np.linalg.norm(rhs))
    out["converged"] = flag == 0
    ref = os.path.join(OUT, f"ref_{c['label']}.npy")
    if os.path.exists(ref):
        out["max_dT_vs_base"] = float(np.max(np.abs(x - np.load(ref))))
    out["peak_gb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1e9 if sys.platform == "darwin" else 1e6)
    return out


def table():
    """!
    @brief Print the log of the extras.
    @return None.
    """
    for r in map(json.loads, open(LOG)):
        if "total_s" not in r:
            print(r)
            continue
        print(f"{r['case']:12s} {r['variant']:16s} its {r['iterations']:5d} setup {r['setup_s']:7.2f} solve {r['solve_s']:7.2f} total {r['total_s']:7.2f} "
              f"dT {r.get('max_dT_vs_base', float('nan')):.1e} res {r['residual']:.1e} conv {r['converged']} GB {r['peak_gb']:.2f}")


def main():
    """!
    @brief Run the extras of the named cases, one child process each, under the lock.
    @return int Exit code.
    """
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--one", nargs=2)
    ap.add_argument("--table", action="store_true")
    ap.add_argument("--lock")
    ap.add_argument("--cases", nargs="*", default=["example_2mm"])
    ap.add_argument("--extras", nargs="*", default=EXTRAS)
    a = ap.parse_args()
    if a.one:
        print(json.dumps(run_one(*a.one)))
        return 0
    if a.table:
        table()
        return 0
    if not a.lock:
        print("refusing to run without --lock")
        return 2
    os.mkdir(a.lock)
    try:
        os.makedirs(OUT, exist_ok=True)
        for case in a.cases:
            for ex in a.extras:
                r = subprocess.run([sys.executable, os.path.abspath(__file__), "--one", case, ex], capture_output=True, text=True, timeout=1800)
                js = [s for s in r.stdout.splitlines() if s.startswith("{")]
                rec = json.loads(js[-1]) if js else {"case": case, "variant": ex, "refused": r.stderr[-300:]}
                with open(LOG, "a") as fh:
                    fh.write(json.dumps(rec) + "\n")
    finally:
        os.rmdir(a.lock)
    table()
    return 0


if __name__ == "__main__":
    sys.exit(main())
