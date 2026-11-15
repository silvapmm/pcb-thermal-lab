#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_hierarchy_reuse.py
@brief Question: how much of a (possibly expensive) AMG setup can be paid once? Three reuses are measured: (a) the same matrix, other right-hand sides (only the power changes); (b) a STALE hierarchy
       as preconditioner of a matrix whose film coefficients changed (the computed-h loop of the API); (c) the hierarchy of K as the preconditioner of K + M/dt (transient steps).
@details A fixed preconditioner stays SPD, so CG remains valid whatever the matrix it is applied to; only the iteration count changes. (a) scales the heater volumetric sources one at a time and
         reassembles the right-hand side; (b) multiplies every film coefficient by s in {0.5, 0.8, 1.25, 2} (`Model.faces[i]['h']`) and solves with the hierarchy built at s = 1; (c) adds a diagonal
         (rho cp V / dt)-like term of a few sizes to the matrix (the lumped mass is approximated by a constant times the element volumes, an ASSUMPTION: the transient FEM code is not used here).
         HEAVY; lock as the other studies. NOT RUN when written. Usage (repository root):

         .venv/bin/python research/fem-amg-thin-layers/scripts/study_hierarchy_reuse.py --lock <scratchpad>/heavy_lock --case example_2mm --variant evo_k2_e4
"""

import argparse
import json
import os
import sys
import time

import numpy as np
import scipy.sparse as sp

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(FOLDER, "lib"))
OUT = os.path.join(FOLDER, "out")


def main():
    """!
    @brief Build the hierarchy once, then solve the three families of changed systems and print iterations and time against a fresh setup.
    @return int Exit code.
    """
    import cases
    import variants
    ap = argparse.ArgumentParser()
    ap.add_argument("--lock", required=True)
    ap.add_argument("--case", default="example_2mm")
    ap.add_argument("--variant", default="base")
    a = ap.parse_args()
    os.mkdir(a.lock)
    rows = []
    try:
        c = cases.build(a.case)
        A, rhs, model = c["A"], c["rhs"], c["model"]
        cols = variants.column_ids(model) if a.variant in variants.COLUMN_VARIANTS else None
        M, info = variants.make_preconditioner(A, a.variant, cols)
        if M is None:
            print("refused:", info)
            return 1
        x0, cg0 = variants.timed_cg(A, rhs, M)
        rows.append({"what": "first solve", "setup_s": info["setup_s"], **cg0})
        # (a) other right-hand sides: the heater sources scaled one at a time (same matrix)
        q0 = model.q.copy()
        for s in (0.5, 2.0, 3.0):
            model.q[:] = q0 * s
            r = model.assemble()["rhs"]
            _, cg = variants.timed_cg(A, np.asarray(r, float), M)
            rows.append({"what": f"same matrix, sources x{s}", **cg})
        model.q[:] = q0
        # (b) stale hierarchy for changed films
        h0 = [f["h"].copy() for f in model.faces]
        for s in (0.5, 0.8, 1.25, 2.0):
            for f, h in zip(model.faces, h0):
                f["h"] = h * s
            asm = model.assemble()
            A2, b2 = asm["A"].tocsr(), np.asarray(asm["rhs"], float)
            _, stale = variants.timed_cg(A2, b2, M)
            M2, i2 = variants.make_preconditioner(A2, a.variant, cols)
            _, fresh = variants.timed_cg(A2, b2, M2)
            rows.append({"what": f"films x{s}: stale hierarchy", **stale})
            rows.append({"what": f"films x{s}: fresh hierarchy", "setup_s": i2["setup_s"], **fresh})
        for f, h in zip(model.faces, h0):
            f["h"] = h
        # (c) K + D with D a constant times the element-volume lumped mass (assumption, see the module text)
        vol = np.asarray(model.element_volumes())
        lump = np.zeros(A.shape[0])
        diag_scale = float(A.diagonal().mean())
        lump[:] = diag_scale
        for s in (0.01, 0.1, 1.0, 10.0):
            A3 = (A + s * sp.diags(lump)).tocsr()
            _, cg = variants.timed_cg(A3, rhs, M)
            rows.append({"what": f"K + {s} * mean diag, hierarchy of K", **cg})
        del vol
    finally:
        os.rmdir(a.lock)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, f"reuse_{a.case}_{a.variant}.json"), "w") as fh:
        json.dump(rows, fh, indent=1)
    for r in rows:
        print(f"{r['what']:40s} its {r.get('iterations', '-'):>5} solve {r.get('solve_s', float('nan')):7.2f} s setup {r.get('setup_s', float('nan')):7.2f} s resid {r.get('residual', float('nan')):.1e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
