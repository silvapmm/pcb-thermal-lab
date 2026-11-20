#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file measure_fem_transient_law.py
@brief Measures the peak memory and the time of the program's FEM time simulation (`fem.solve_transient`, `profiles.run_fem`) on boards of the regression harness, each case in a fresh
       process, to refit `memory.FEM_TRANSIENT_FACTOR_CG`, `FEM_TRANSIENT_FACTOR_DIRECT`, `FEM_STEP_SECONDS_DIRECT`, `FEM_STEP_SECONDS_CG`, `FEM_RUN_SECONDS_MAX` and `femcore.FEM_TRANSIENT_DIRECT_MAX`.
@details HEAVY: do not run it beside another heavy job (one case at a time; the largest case peaks at about 2.7 GB of resident memory by the program's time law, see `--dry-run`).
         A case is a harness board at a plan cell, a solver path ('direct' or 'cg'; CG needs pyamg) and a kind: 'step' (a power-step response of 40 frames, `fem.solve_transient`) or 'profile'
         (two windows of a 60 s square wave through `profiles.run_fem`). The peak is `ru_maxrss` of the child minus the resident size read after the imports, as `releases/2.8.0/fem-model/scripts/measure_fem_law.py`.
         The ratio is the peak growth over the law of the path WITHOUT its time factor (`FEM_DIRECT_BYTES x n` for direct; for CG the law of `memory.estimate_bytes('fem_time_cg')`
         divided by `FEM_TRANSIENT_FACTOR_CG`, i.e. the steady CG law without the floor that the steady estimate puts at the direct limit): the constants become the largest measured
         ratio of each path times 1.15 (never below 1.0), the CG one over the cases above `FEM_DIRECT_MAX` (below it a time run is always direct; review). The seconds per unknown and step are the stepping time over unknowns x steps. Usage from the repository root:

         .venv/bin/python releases/2.9.0/fem-transient/scripts/measure_fem_transient_law.py --dry-run      # list the cases with the expected peak of the program's time law, run nothing
         .venv/bin/python releases/2.9.0/fem-transient/scripts/measure_fem_transient_law.py                # every case, a table and the fitted constants (optionally --json FILE)
         .venv/bin/python releases/2.9.0/fem-transient/scripts/measure_fem_transient_law.py --one example_board 2 cg step   # one case, one JSON line
"""

import json
import os
import resource
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

# (board of the harness, plan cell in mm, solver path, kind): the direct cases are the small meshes and two above the steady direct limit, the CG cases the larger ones
CASES = [
    ("plate_uniform", 2.0, "direct", "step"), ("plate_vias", 2.0, "direct", "step"), ("finned_block", 2.0, "direct", "step"), ("t_outline", 2.0, "direct", "profile"),
    ("example_board", 3.0, "direct", "step"), ("example_board", 2.0, "direct", "step"), ("finned_block", 1.4, "direct", "step"),
    ("example_board", 2.0, "cg", "step"), ("plate_vias", 1.0, "cg", "step"), ("finned_block", 1.0, "cg", "step"), ("t_outline", 1.0, "cg", "profile"),
    ("example_board", 2.0, "cg", "profile"), ("hatched_copper", 1.0, "cg", "step"), ("one_layer_pad", 1.0, "cg", "step"),
    ("example_board", 1.0, "cg", "step"),
]


def _import():
    """!
    @brief Put the repository and the harness boards on the path and import what the cases need.
    @return Tuple (regress_boards module, the pcbthermal modules fem, femmesh, memory, profiles).
    """
    sys.path.insert(0, ROOT)
    sys.path.insert(0, os.path.join(ROOT, "tests", "regression"))
    import regress_boards as rb
    from pcbthermal import fem, femmesh, memory, profiles
    return rb, fem, femmesh, memory, profiles


def expected_peak(name, cell, path):
    """!
    @brief The peak growth the program's time law predicts for a case (`memory.estimate_bytes` models 'fem_time' and 'fem_time_cg', what the guard estimates without the base and
           the frames), for the dry run and the script's own memory guard.
    @param name Harness board.
    @param cell Plan cell in mm.
    @param path 'direct' or 'cg'.
    @return Tuple (unknowns, expected growth in bytes).
    """
    rb, fem, femmesh, memory, profiles = _import()
    p = rb.build(name)
    n = femmesh.unknowns(p, cell)[0]
    if path == "direct":
        return n, memory.FEM_DIRECT_BYTES * n * memory.FEM_TRANSIENT_FACTOR_DIRECT       # the direct law of 'fem_time' at every size (forced direct above the limit too)
    return n, memory.estimate_bytes("fem_time_cg", n, n / 10.0, base=0.0)


def memory_factors():
    """!
    @brief The time factors and the steady direct limit of the program under test, for the texts of the script.
    @return Tuple (FEM_TRANSIENT_FACTOR_DIRECT, FEM_TRANSIENT_FACTOR_CG, FEM_DIRECT_MAX).
    """
    rb, fem, femmesh, memory, profiles = _import()
    return memory.FEM_TRANSIENT_FACTOR_DIRECT, memory.FEM_TRANSIENT_FACTOR_CG, memory.FEM_DIRECT_MAX


def available_now():
    """!
    @brief The memory available to a new process now, as the program's guard reads it.
    @return int bytes, or None when the system does not say.
    """
    rb, fem, femmesh, memory, profiles = _import()
    return memory.available_bytes()


def one(name, cell, path, kind):
    """!
    @brief Run one case in this process and describe it.
    @param name Harness board.
    @param cell Plan cell in mm.
    @param path 'direct' or 'cg'.
    @param kind 'step' or 'profile'.
    @return dict: unknowns, solver, seconds of the run, steps, factorisations, iterations, growth and ratio to the steady law.
    """
    rb, fem, femmesh, memory, profiles = _import()
    import numpy as np
    p = rb.build(name)
    n = femmesh.unknowns(p, cell)[0]
    if kind == "profile":
        # the decision (an FVM step response with its own factors) is taken BEFORE the resident size is read, so that its peak is not counted as the FEM's (review)
        from pcbthermal import SquareWave
        p.heaters[0].set_profile(SquareWave(p_on=p.heaters[0].power / 0.3, period=60.0, duty=0.3))
        d = profiles.decide(p, profiles.step_response_fvm(p, 2.0), 0.001)
    start = memory.resident_bytes()
    t0 = time.time()
    if kind == "step":
        r = fem.solve_transient(p, 300.0, n_out=40, cell_mm=cell, theta_scheme=0.5, force_solver=path)
        steps, facts, iters, solver = r.extras["steps"], r.extras["factorisations"], r.extras["iterations"], r.extras["solver"]
    else:
        opts = profiles.ProfileOptions(duration="cycles", cycles=2)
        ad = profiles._FEMAdapter(p, cell, force_solver=path)
        r = profiles.run_windows(p, d, opts, ad, "fem")
        steps, facts, iters, solver = r.steps, ad.stepper.factorisations, ad.stepper.total_iterations, ad.stepper.solver
    secs = time.time() - t0
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == "darwin" else 1024)
    growth = peak - start
    # the law of the path without its time factor (for CG without the floor of the steady estimate at the direct limit, which the time law does not have)
    steady = memory.FEM_DIRECT_BYTES * n if solver == "direct" else memory.estimate_bytes("fem_time_cg", n, n / 10.0, base=0.0) / memory.FEM_TRANSIENT_FACTOR_CG
    return {"board": name, "cell": cell, "kind": kind, "solver": solver, "n": n, "steps": int(steps), "factorisations": int(facts), "iterations": int(iters), "seconds": secs,
            "growth": growth, "ratio": growth / steady, "sec_per_unknown_step": secs / (n * max(steps, 1))}


def main():
    """!
    @brief Dry run, one case, or every case in a fresh process with the table and the fitted constants.
    @return None.
    """
    if "--one" in sys.argv:
        i = sys.argv.index("--one")
        print(json.dumps(one(sys.argv[i + 1], float(sys.argv[i + 2]), sys.argv[i + 3], sys.argv[i + 4])))
        return
    if "--dry-run" in sys.argv:
        print(f"dry run: nothing is run; expected peak growth of the program's time law (direct {memory_factors()[0]:.2f} x 15.9 kB per unknown, CG the steady CG law x "
              f"{memory_factors()[1]:.2f}; resident bytes, without the base of the process)")
        for name, cell, path, kind in CASES:
            n, est = expected_peak(name, cell, path)
            print(f"{name:16s} {cell:4.1f} mm {path:6s} {kind:7s} unknowns {n:8d}  expected peak growth {est / 1e9:5.2f} GB")
        return
    rows = []
    for name, cell, path, kind in CASES:
        n, est = expected_peak(name, cell, path)
        free = available_now()
        if free is not None and 1.5 * est > free:
            # a guard of the script itself (review): never start a case whose expected peak, with a margin of 1.5, is above the memory available at that moment
            print(f"{name} {cell} {path} {kind}: NOT RUN, expected peak {est / 1e9:.2f} GB x 1.5 above the {free / 1e9:.2f} GB available now", flush=True)
            continue
        out = subprocess.run([sys.executable, os.path.abspath(__file__), "--one", name, str(cell), path, kind], capture_output=True, text=True)
        if out.returncode != 0:
            print(f"{name} {cell} {path} {kind}: FAILED {out.stderr.strip().splitlines()[-1:]}", flush=True)
            continue
        r = json.loads(out.stdout.strip().splitlines()[-1])
        rows.append(r)
        print(f"{r['board']:16s} {r['cell']:4.1f} mm {r['solver']:6s} {r['kind']:7s} n={r['n']:8d} steps {r['steps']:5d} {r['seconds']:7.1f} s growth {r['growth'] / 1e9:5.2f} GB "
              f"ratio {r['ratio']:5.2f} {r['sec_per_unknown_step']:.2e} s/unknown/step", flush=True)
    for how in ("direct", "cg"):
        # the CG factor only from the cases where a time run can take CG (above the steady direct limit)
        sel = [r for r in rows if r["solver"] == how and (how == "direct" or r["n"] > memory_factors()[2])]
        if sel:
            worst = max(r["ratio"] for r in sel)
            per = max(r["sec_per_unknown_step"] for r in sel)
            print(f"{how}: largest ratio {worst:.3f} -> FEM_TRANSIENT_FACTOR_{how.upper()} = {max(worst * 1.15, 1.0):.2f}; slowest {per:.2e} s per unknown and step (a whole run over "
                  "unknowns x steps; the program's time model is a setup per stage plus a cost per step, MEASURED.md 3)")
    if "--json" in sys.argv:
        with open(sys.argv[sys.argv.index("--json") + 1], "w") as fh:
            json.dump(rows, fh, indent=1)


if __name__ == "__main__":
    main()
