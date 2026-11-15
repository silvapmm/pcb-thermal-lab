#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file measure_fem_law.py
@brief Measures the peak memory and the time of the program's FEM (`femmesh.build` + `femcore.Model.solve`) on boards of the regression harness, each in a fresh process, to fit the memory law of
       the model key `fem` in `pcbthermal/memory.py` (`releases/2.8.0/fem-model/DESIGN.md`, section 5.3, branch 3).
@details One case is a harness board at a plan cell, solved directly (`force` 'direct', at most FEM_DIRECT_MAX unknowns) or by conjugate gradients with pyamg. The peak is `ru_maxrss` of the child
         (bytes on macOS) minus the resident size read after the imports, so what is counted is what the mesh and the solve allocate. The boards include vias (patches and rods), a metal block, a
         rectilinear outline, a one-layer board and hatched copper. Needs pyamg on `PYTHONPATH` for the conjugate-gradient cases (a scratch `pip install --target` folder works).
         Usage, from the repository root (one heavy job at a time; the largest case peaks under 2 GB):

         PYTHONPATH=<pyamg folder> .venv/bin/python releases/2.8.0/fem-model/scripts/measure_fem_law.py            # every case, a table and the fit (optionally --json FILE)
         PYTHONPATH=<pyamg folder> .venv/bin/python releases/2.8.0/fem-model/scripts/measure_fem_law.py --one example_board 2 cg   # one case, one JSON line
"""

import json
import os
import resource
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

# (board of the harness, plan cell in mm, solver): the direct cases are the small meshes of 2 mm, the CG cases the larger ones
CASES = [
    ("plate_uniform", 2.0, "direct"), ("plate_vias", 2.0, "direct"), ("t_outline", 2.0, "direct"), ("finned_block", 2.0, "direct"),
    ("hatched_copper", 2.0, "direct"), ("two_layer_partial", 2.0, "direct"), ("one_layer_full", 2.0, "direct"), ("drawn_stripes_pad", 1.0, "direct"),
    ("example_board", 2.0, "cg"), ("example_cut_to_T", 2.0, "cg"), ("plate_vias", 1.0, "cg"), ("finned_block", 1.0, "cg"), ("t_outline", 1.0, "cg"),
    ("one_layer_pad", 1.0, "cg"), ("two_layer_partial", 1.0, "cg"), ("hatched_copper", 1.0, "cg"), ("reference_board", 1.0, "cg"),
    ("plate_vias", 0.5, "cg"), ("finned_block", 0.5, "cg"), ("one_layer_pad", 0.5, "cg"), ("t_outline", 0.5, "cg"),
]


def one(name, cell, solver):
    """!
    @brief Build and solve one case in this process and describe it.
    @param name Board of the regression harness.
    @param cell Plan cell in mm.
    @param solver 'direct' or 'cg'.
    @return dict with the unknowns, the solver, the build and solve seconds, the resident growth and the peak growth in bytes.
    """
    sys.path.insert(0, ROOT)
    sys.path.insert(0, os.path.join(ROOT, "releases", "regression-harness", "lib"))
    import regress_boards as rb
    from pcbthermal import femmesh, memory
    p = rb.build(name)
    start = memory.resident_bytes()
    t0 = time.time()
    m = femmesh.build(p, cell)
    t1 = time.time()
    r = m.model.solve(force=solver)
    t2 = time.time()
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == "darwin" else 1024)
    return {"board": name, "cell": cell, "solver": r["solver"], "n": m.n_unknowns, "elements": m.n_elements, "patches": m.n_patches, "rods": m.n_rods, "t_build": t1 - t0, "t_solve": t2 - t1,
            "start": start, "peak": peak, "growth": peak - start, "balance": r["balance"], "rise": float(r["T"][~(r["T"] != r["T"])].max())}


def main():
    """!
    @brief Run every case in a fresh process, print the table and the fit of the law (bytes per unknown by solver).
    @return None.
    """
    if len(sys.argv) > 1 and sys.argv[1] == "--one":
        print(json.dumps(one(sys.argv[2], float(sys.argv[3]), sys.argv[4])))
        return
    rows = []
    for name, cell, solver in CASES:
        out = subprocess.run([sys.executable, os.path.abspath(__file__), "--one", name, str(cell), solver], capture_output=True, text=True)
        if out.returncode != 0:
            print(f"{name} {cell} {solver}: FAILED {out.stderr.strip().splitlines()[-1:]}")
            continue
        r = json.loads(out.stdout.strip().splitlines()[-1])
        rows.append(r)
        print(f"{r['board']:20s} {r['cell']:4.1f} mm {r['solver']:6s} n={r['n']:8d} build {r['t_build']:6.2f} s solve {r['t_solve']:6.2f} s growth {r['growth'] / 1e9:5.2f} GB = {r['growth'] / r['n'] / 1e3:6.2f} kB/unknown "
              f"balance {r['balance']:.9f}", flush=True)
    for how in ("direct", "cg"):
        sel = [r for r in rows if r["solver"] == how]
        if not sel:
            continue
        per = [r["growth"] / r["n"] for r in sel]
        print(f"{how}: {len(sel)} runs, bytes per unknown min {min(per):.0f}, mean {sum(per) / len(per):.0f}, max {max(per):.0f}; max x 1.1 = {1.1 * max(per):.0f}")
    if "--json" in sys.argv:
        with open(sys.argv[sys.argv.index("--json") + 1], "w") as fh:
            json.dump(rows, fh, indent=1)


if __name__ == "__main__":
    main()
