#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_frozen_robustness.py
@brief Question: does a candidate variant still converge, to the same field within 1e-8 K, on every one of the 29 frozen finite-element records (board, cell) and on case 2 at 828 000 unknowns?
@details For each (board, cell) of `cases.frozen_fem_keys()` it assembles the system, solves it with 'base' and with the candidate through `variants.timed_cg`, and prints iterations, time and
         the largest difference of the fields. Only boards above the direct limit are interesting for the iterative path, but all 29 are run through CG (`force='cg'` equivalent: the matrix is
         handed straight to CG) so the robustness is tested on the whole set. HEAVY (several minutes); take the lock like study_amg_variants.py. NOT RUN when written. Usage (repository root):

         .venv/bin/python research/fem-amg-thin-layers/scripts/study_frozen_robustness.py --lock <scratchpad>/heavy_lock --variant sym_t0.03
"""

import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(FOLDER, "lib"))
OUT = os.path.join(FOLDER, "out")


def main():
    """!
    @brief Run base and the candidate over every frozen record and print a table; exit code 1 if any record fails to converge or differs by 1e-8 K or more.
    @return int Exit code.
    """
    import cases
    import variants
    ap = argparse.ArgumentParser()
    ap.add_argument("--lock", required=True)
    ap.add_argument("--variant", required=True)
    ap.add_argument("--max-unknowns", type=int, default=900_000)
    a = ap.parse_args()
    os.mkdir(a.lock)
    bad = 0
    rows = []
    try:
        for board, cell in cases.frozen_fem_keys():
            try:
                A_rhs = _assemble(board, cell, a.max_unknowns)
            except ValueError as exc:                              # the program's own refusal of a mesh: recorded, not hidden
                rows.append({"board": board, "cell": cell, "skipped": str(exc)[:120]})
                continue
            A, rhs = A_rhs
            Mb, ib = variants.make_preconditioner(A, "base")
            xb, cb = variants.timed_cg(A, rhs, Mb)
            Mv, iv = variants.make_preconditioner(A, a.variant)
            if Mv is None:
                rows.append({"board": board, "cell": cell, "refused": iv["refused"]})
                bad += 1
                continue
            xv, cv = variants.timed_cg(A, rhs, Mv)
            d = float(np.max(np.abs(xv - xb)))
            ok = cv["converged"] and d < 1e-8
            bad += 0 if ok else 1
            rows.append({"board": board, "cell": cell, "n": int(rhs.size), "base_its": cb["iterations"], "base_total_s": ib["setup_s"] + cb["solve_s"], "its": cv["iterations"],
                         "total_s": iv["setup_s"] + cv["solve_s"], "max_dT_K": d, "ok": ok})
            print(json.dumps(rows[-1]))
    finally:
        os.rmdir(a.lock)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, f"frozen_{a.variant}.json"), "w") as fh:
        json.dump(rows, fh, indent=1)
    print(f"{len(rows)} records, {bad} failed")
    return 1 if bad else 0


def _assemble(board, cell, max_unknowns):
    """!
    @brief Assemble the system of a frozen board at a cell.
    @param board Board name of tests/regression/regress_boards.py.
    @param cell Plan cell in mm.
    @param max_unknowns Refuse above this many unknowns (memory).
    @return (A, rhs).
    @throws ValueError If the mesh is too big or the program refuses it.
    """
    import cases
    from pcbthermal import femmesh
    p = cases.problem_of("frozen:" + board)
    if femmesh.unknowns(p, cell)[0] > max_unknowns:
        raise ValueError("above max-unknowns")
    a = femmesh.build(p, cell, 6, 2.0).model.assemble()
    return a["A"].tocsr(), np.asarray(a["rhs"], float)


if __name__ == "__main__":
    sys.exit(main())
