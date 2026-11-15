#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_amg_variants.py
@brief Question: can a cheap pyamg variant make the whole FEM solve (setup + CG) faster than the program's smoothed aggregation on thin, strongly anisotropic layered meshes, with the same field to 1e-8 K?
@details Each (case, variant) runs in a fresh child process (`--one`), so the peak memory is its own; the parent appends one JSON line per run to out/variants.jsonl and skips what is already there
         (resumable). The reference field of a case is the 'base' variant's, saved in out/ref_<case>.npy by the first run of 'base'. HEAVY: take the lock first (rule of CLAUDE.md 12: one heavy job at a
         time, below 4 GB each); the script refuses to start when the lock directory exists. NOT RUN when written. Usage (repository root, the .venv with pyamg):

         .venv/bin/python research/fem-amg-thin-layers/scripts/study_amg_variants.py --lock <scratchpad>/heavy_lock --cases example_2mm example_1mm --variants base sym_t0.03 evo_k2_e4
         .venv/bin/python research/fem-amg-thin-layers/scripts/study_amg_variants.py --one example_2mm base          # one child run, one JSON line
         .venv/bin/python research/fem-amg-thin-layers/scripts/study_amg_variants.py --table                          # print out/variants.jsonl as a table
"""

import argparse
import json
import os
import resource
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(FOLDER, "lib"))
OUT = os.path.join(FOLDER, "out")
LOG = os.path.join(OUT, "variants.jsonl")
PEAK_LIMIT_GB = 4.0                                                # the maintainer's ceiling for one heavy job


def run_one(case, variant, cell=None):
    """!
    @brief Solve one case with one variant in this process and return the measurements.
    @param case A key of cases.CASES.
    @param variant A key of variants.VARIANTS.
    @param cell Plan cell in mm or None for the case default.
    @return dict: case, variant, n, assemble_s, setup_s, iterations, solve_s, total_s (setup + solve), residual, converged, levels, op_complexity, grid_complexity, max_dT_vs_base (K, None for base), peak_gb.
    """
    import cases
    import variants
    import time
    t0 = time.perf_counter()
    c = cases.build(case, cell)
    out = {"case": case, "variant": variant, "n": c["n"], "cell_mm": c["cell_mm"], "assemble_s": time.perf_counter() - t0}
    M, info = variants.make_preconditioner(c["A"], variant)
    if M is None:
        out.update(info)
        return out
    x, cg = variants.timed_cg(c["A"], c["rhs"], M)
    out.update(info)
    out.update(cg)
    out["total_s"] = info["setup_s"] + cg["solve_s"]
    os.makedirs(OUT, exist_ok=True)
    ref = os.path.join(OUT, f"ref_{c['label']}.npy")
    if variant == "base":
        np.save(ref, x)
        out["max_dT_vs_base"] = None
    elif os.path.exists(ref):
        out["max_dT_vs_base"] = float(np.max(np.abs(x - np.load(ref))))     # K: the matrix is in K, so the unknowns are rises
    out["peak_gb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1e9 if sys.platform == "darwin" else 1e6)
    return out


def done_keys():
    """!
    @brief The (case, variant, cell) triples already in the log.
    @return set of tuples.
    """
    if not os.path.exists(LOG):
        return set()
    with open(LOG) as fh:
        return {(r["case"], r["variant"], r.get("cell_req")) for r in map(json.loads, fh)}


def table():
    """!
    @brief Print the log as a table, each variant against 'base' of the same case (total time ratio).
    @return None.
    """
    rows = [json.loads(s) for s in open(LOG)]
    base = {r["case"]: r for r in rows if r["variant"] == "base" and "total_s" in r}
    print(f"{'case':18s} {'variant':12s} {'n':>8s} {'its':>5s} {'setup':>7s} {'solve':>7s} {'total':>7s} {'/base':>6s} {'dT_K':>9s} {'res':>8s} {'GB':>5s}")
    for r in rows:
        if "total_s" not in r:
            print(f"{r['case']:18s} {r['variant']:12s} refused: {r.get('refused', '?')}")
            continue
        b = base.get(r["case"])
        ratio = r["total_s"] / b["total_s"] if b else float("nan")
        d = r.get("max_dT_vs_base")
        print(f"{r['case']:18s} {r['variant']:12s} {r['n']:8d} {r['iterations']:5d} {r['setup_s']:7.2f} {r['solve_s']:7.2f} {r['total_s']:7.2f} {ratio:6.2f} "
              f"{'' if d is None else format(d, '9.2e'):>9s} {r['residual']:8.1e} {r['peak_gb']:5.2f}")


def main():
    """!
    @brief Parse the arguments and run the matrix of (case, variant) one child process at a time under the lock.
    @return int Exit code.
    """
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--one", nargs=2, metavar=("CASE", "VARIANT"))
    ap.add_argument("--cell", type=float, default=None)
    ap.add_argument("--table", action="store_true")
    ap.add_argument("--lock", help="directory used as the heavy-job lock (mkdir is atomic); refuses to run if it exists")
    ap.add_argument("--cases", nargs="*", default=["example_2mm"])
    ap.add_argument("--variants", nargs="*", default=["base"])
    a = ap.parse_args()
    if a.one:
        print(json.dumps(run_one(a.one[0], a.one[1], a.cell)))
        return 0
    if a.table:
        table()
        return 0
    if not a.lock:
        print("refusing to run a heavy study without --lock (CLAUDE.md 12)")
        return 2
    os.mkdir(a.lock)                                               # FileExistsError means another heavy job is running
    try:
        os.makedirs(OUT, exist_ok=True)
        done = done_keys()
        for case in a.cases:
            for variant in (["base"] + [v for v in a.variants if v != "base"]):       # the reference field first
                if (case, variant, a.cell) in done:
                    continue
                r = subprocess.run([sys.executable, os.path.abspath(__file__), "--one", case, variant] + (["--cell", str(a.cell)] if a.cell else []),
                                   capture_output=True, text=True, timeout=1800)
                line = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else json.dumps({"case": case, "variant": variant, "refused": r.stderr[-300:]})
                rec = json.loads(line)
                rec["cell_req"] = a.cell
                with open(LOG, "a") as fh:
                    fh.write(json.dumps(rec) + "\n")
                if rec.get("peak_gb", 0) > PEAK_LIMIT_GB:
                    print(f"peak {rec['peak_gb']:.2f} GB above {PEAK_LIMIT_GB} GB on {case}/{variant}: stopping this case")
                    break
    finally:
        os.rmdir(a.lock)
    table()
    return 0


if __name__ == "__main__":
    sys.exit(main())
