#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file measure_fem_transient_direct_limit.py
@brief Measures, on one board at several cell sizes, the time and the peak memory of ONE stage of a FEM time simulation on the direct path and on the conjugate-gradient path (the factorisation or
       hierarchy, then eight steps), to decide `femcore.FEM_TRANSIENT_DIRECT_MAX`: the largest unknown count at which the direct path is cheaper than the CG path per run and fits the memory guard.
@details HEAVY (the direct path at 100 000 unknowns holds a factor of about 2.5 GB by the superlinear fill of DESIGN.md 14.3): one case at a time, never beside another heavy job. Each case is a
         fresh process. Usage from the repository root:

         .venv/bin/python releases/2.9.0/fem-transient/scripts/measure_fem_transient_direct_limit.py --dry-run       # the cases and the expected peak of the shipped steady direct law
         .venv/bin/python releases/2.9.0/fem-transient/scripts/measure_fem_transient_direct_limit.py                 # all cases, a table of seconds per stage on both paths
         .venv/bin/python releases/2.9.0/fem-transient/scripts/measure_fem_transient_direct_limit.py --one 2.5 cg    # one case, one JSON line
"""

import json
import os
import resource
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
BOARD = "example_board"
CELLS = [4.0, 3.0, 2.5, 2.0, 1.6]                        # about 15 000 to 140 000 unknowns on the example board
PATHS = ("direct", "cg")
STEPS = 8


def _setup():
    """!
    @brief Import the program and the harness board.
    @return Tuple (problem, memory module, femmesh, femcore, fem).
    """
    sys.path.insert(0, ROOT)
    sys.path.insert(0, os.path.join(ROOT, "tests", "regression"))
    import regress_boards as rb
    from pcbthermal import fem, femcore, femmesh, memory
    return rb.build(BOARD), memory, femmesh, femcore, fem


def one(cell, path):
    """!
    @brief One stage of a Crank-Nicolson run on the example board: assemble, factor (or build the hierarchy), eight steps.
    @param cell Plan cell in mm.
    @param path 'direct' or 'cg'.
    @return dict: unknowns, seconds of the factorisation, seconds per step, CG iterations per step, growth in bytes.
    """
    p, memory, femmesh, femcore, fem = _setup()
    import numpy as np
    start = memory.resident_bytes()
    mesh = femmesh.build(p, cell)
    a = mesh.model.assemble(capacity=True)
    st = femcore.Stepper(a["A"], a["M"], force=path)
    t0 = time.time()
    st.prepare(0.5, 0.5)
    t_factor = time.time() - t0
    T = np.zeros(a["rhs"].size)
    t1 = time.time()
    for _ in range(STEPS):
        T = st.step(T, 0.5, 0.5, a["rhs"], a["rhs"])
    t_step = (time.time() - t1) / STEPS
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == "darwin" else 1024)
    return {"cell": cell, "path": path, "n": int(a["rhs"].size), "t_factor": t_factor, "t_step": t_step, "iterations_per_step": st.total_iterations / STEPS, "growth": peak - start}


def main():
    """!
    @brief Dry run, one case, or every case in a fresh process.
    @return None.
    """
    if "--one" in sys.argv:
        i = sys.argv.index("--one")
        print(json.dumps(one(float(sys.argv[i + 1]), sys.argv[i + 2])))
        return
    if "--dry-run" in sys.argv:
        p, memory, femmesh, femcore, fem = _setup()
        print("dry run: nothing is run; the expected peak is the steady direct law (FEM_DIRECT_BYTES x n) or the CG law, times the shipped transient factor")
        for cell in CELLS:
            n = femmesh.unknowns(p, cell)[0]
            for path in PATHS:
                est = (memory.FEM_DIRECT_BYTES * n * memory.FEM_TRANSIENT_FACTOR_DIRECT) if path == "direct" else memory.estimate_bytes("fem", n, n / 10.0, base=0.0, factor=memory.FEM_TRANSIENT_FACTOR_CG)
                print(f"cell {cell:3.1f} mm {path:6s} unknowns {n:8d}  expected peak growth {est / 1e9:5.2f} GB")
        return
    p, memory, femmesh, femcore, fem = _setup()
    grown = {}                                                  # bytes per unknown of the last direct case, to extrapolate the superlinear fill to the next one
    for cell in CELLS:
        n = femmesh.unknowns(p, cell)[0]
        for path in PATHS:
            # a guard of the script itself (review): the expected peak (the shipped law, or the last direct case scaled by sqrt(n) for the superlinear fill) times 1.5 must be
            # below the memory available now, or the case is not started
            est = (memory.FEM_DIRECT_BYTES * n * memory.FEM_TRANSIENT_FACTOR_DIRECT) if path == "direct" else memory.estimate_bytes("fem", n, n / 10.0, base=0.0, factor=memory.FEM_TRANSIENT_FACTOR_CG)
            if path == "direct" and grown:
                n0, b0 = grown["n"], grown["bytes"]
                est = max(est, b0 / n0 * (n / n0) ** 0.5 * n)
            free = memory.available_bytes()
            if free is not None and 1.5 * est > free:
                print(f"cell {cell} {path}: NOT RUN, expected peak {est / 1e9:.2f} GB x 1.5 above the {free / 1e9:.2f} GB available now", flush=True)
                continue
            out = subprocess.run([sys.executable, os.path.abspath(__file__), "--one", str(cell), path], capture_output=True, text=True)
            if out.returncode != 0:
                print(f"cell {cell} {path}: FAILED {out.stderr.strip().splitlines()[-1:]}", flush=True)
                continue
            r = json.loads(out.stdout.strip().splitlines()[-1])
            if path == "direct":
                grown = {"n": r["n"], "bytes": r["growth"]}
            print(f"cell {r['cell']:3.1f} mm {r['path']:6s} n={r['n']:8d}  stage setup {r['t_factor']:7.2f} s  step {r['t_step']:7.3f} s  iterations/step {r['iterations_per_step']:6.1f}  growth {r['growth'] / 1e9:5.2f} GB", flush=True)


if __name__ == "__main__":
    main()
