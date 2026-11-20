#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_regression_set.py
@brief Does the new rule of the 'estimate (upper side)' flag move any surface number on the regression-set boards, and how many parts change flag?

@details Solves every board of tests/regression/regress_boards.py with the FVM and the FDM (cell 2 mm) in the tree given by `--root` and saves the surface arrays and the flags;
         `--compare A.npz B.npz` then prints, per board and model, whether T_surface and T_surface_mean are bit-identical and how many flagged cells and parts differ.
         Usage:  .venv/bin/python releases/2.9.0/surface-flag/scripts/study_regression_set.py --root <tree> --out <file.npz>     (once on development, once on the fix)
                 .venv/bin/python releases/2.9.0/surface-flag/scripts/study_regression_set.py --compare before.npz after.npz
"""

import argparse
import os
import sys

import numpy as np


def run(root, out):
    """!
    @brief Solve the boards in the tree `root` and save their surface arrays.
    @param root Repository root whose `pcbthermal` and `tests/regression` are used.
    @param out Path of the .npz file to write.
    """
    sys.path.insert(0, os.path.join(root, "tests", "regression"))
    sys.path.insert(0, root)
    import regress_boards as RB
    from pcbthermal.api import simulate
    from pcbthermal.api import SolverOptions
    data, nparts = {}, {}
    for name in RB.board_names():
        problem = RB.build(name)
        nparts[name] = len(problem.heaters)
        res = simulate(problem, SolverOptions(models=("fvm", "fdm"), cell_mm=2.0))
        for key in ("fvm", "fdm"):
            r = res.results[key]
            for arr in ("T_surface", "T_surface_mean", "T_surface_flag"):
                if arr in r.arrays:
                    data[f"{name}|{key}|{arr}"] = np.asarray(r.arrays[arr])
    np.savez(out, **data)
    print(f"{len(RB.board_names())} boards, {sum(nparts.values())} parts, saved {out}")


def compare(a, b):
    """!
    @brief Compare two saved runs.
    @param a Path of the run before the change.
    @param b Path of the run after the change.
    """
    A, B = np.load(a), np.load(b)
    boards = sorted({k.split("|")[0] for k in A.files})
    changed_cells = changed_runs = 0
    print("board | model | surface identical | flagged cells before -> after")
    for name in boards:
        for model in ("fvm", "fdm"):
            same = all(np.array_equal(A[f"{name}|{model}|{x}"], B[f"{name}|{model}|{x}"], equal_nan=True) for x in ("T_surface", "T_surface_mean") if f"{name}|{model}|{x}" in A.files)
            fa, fb = A.get(f"{name}|{model}|T_surface_flag"), B.get(f"{name}|{model}|T_surface_flag")
            if fa is None:
                continue
            n = int((fa != fb).sum())
            changed_cells += n
            changed_runs += n > 0
            print(f"{name:22s} | {model} | {same} | {int(fa.sum())} -> {int(fb.sum())}" + ("   <-- flag changed" if n else ""))
    print(f"runs with a changed flag: {changed_runs}; cells whose flag changed: {changed_cells}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root")
    ap.add_argument("--out")
    ap.add_argument("--compare", nargs=2)
    ns = ap.parse_args()
    if ns.compare:
        compare(*ns.compare)
    else:
        run(os.path.abspath(ns.root), ns.out)
