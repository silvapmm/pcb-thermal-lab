#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_memory_ladder.py
@brief Question: how much memory and time does a solve of each model and board class take as the unknowns grow, and what are the coefficients of the law peak = base + k N (N/N_REF)^(p-1) of each class?
@details Builds a ladder of boards (plain 2, 4 and 6 layers; vias; partial copper with the laminate rule; outline; metal block; FDM; 3D solid; Lumped; Analytic with vias and heatsink)
         at several cells and runs every point in its own subprocess (lib/measure.py), recording the unknowns, the peak resident memory seen by the kernel and the solve time.
         Safety: before a point runs, its unknowns are counted (no solve) and the provisional estimate is compared with a cutoff (default 60 % of the physical memory, at most 10 GB);
         a point above it is skipped, a running child above it is killed by the watchdog, and a series stops at its first skipped or killed point. Results are appended to
         out/ladder.jsonl, so an interrupted study resumes where it stopped (a finished point is not repeated).
         The cell-major ordering is measured as a second series ("order": "cell") on the same boards, and the "compare" mode checks that both orderings give the same temperatures.
         Usage (from the repository root, on a quiet machine, nothing else heavy running):
             .venv/bin/python research/memory-guard/scripts/study_memory_ladder.py --plan              # list the points and their estimated size, runs nothing
             .venv/bin/python research/memory-guard/scripts/study_memory_ladder.py --run              # the whole ladder (about an hour)
             .venv/bin/python research/memory-guard/scripts/study_memory_ladder.py --run --quick      # the small half only (minutes)
             .venv/bin/python research/memory-guard/scripts/study_memory_ladder.py --fit              # fit the coefficients from out/ladder.jsonl and print the tables
"""

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))
sys.path.insert(0, str(HERE.parents[2]))

import numpy as np                                     # noqa: E402

import cases                                           # noqa: E402
import measure                                         # noqa: E402
import memory_model as mm                              # noqa: E402

OUT = HERE.parent / "out"
LADDER = OUT / "ladder.jsonl"
FIT = OUT / "fit.json"
SIZE_MM = 100.0                                        # Board side of the ladder (the unknowns are changed through the cell)


def series():
    """!
    @brief The series of the ladder: (name, family, layers, model, order, cells in mm from coarse to fine).
    @return List of tuples.
    """
    s = []
    cells_fvm = (2.0, 1.0, 0.7, 0.5, 0.35, 0.25)
    for fam, layers in (("plain", 2), ("plain", 4), ("plain", 6), ("vias", 4), ("partial", 2), ("partial", 4), ("partial", 6), ("outline", 2), ("block", 2)):
        s.append((f"fvm_{fam}_{layers}L", fam, layers, "fvm", "layer", cells_fvm))
    for order in ("layer", "cell"):
        for layers in (2, 4):
            s.append((f"fvm_stripes_{layers}L" + ("_cellmajor" if order == "cell" else ""), "stripes", layers, "fvm", order, cells_fvm))
    for fam, layers in (("partial", 2), ("partial", 4), ("plain", 4)):
        s.append((f"fvm_{fam}_{layers}L_cellmajor", fam, layers, "fvm", "cell", cells_fvm))
    for fam, layers in (("plain", 4), ("partial", 4)):
        s.append((f"fdm_{fam}_{layers}L", fam, layers, "fdm", "layer", (2.0, 1.0, 0.7, 0.5, 0.35)))
    for fam, layers in (("plain", 2), ("plain", 6), ("vias", 4), ("partial", 2), ("block", 2)):
        s.append((f"solid3d_{fam}_{layers}L", fam, layers, "solid3d", "layer", (2.0, 1.5, 1.0, 0.7, 0.5)))
    for fam, layers in (("plain", 2), ("partial", 2)):
        s.append((f"lumped_{fam}_{layers}L", fam, layers, "lumped", "layer", (1.0, 0.5, 0.25)))
    for fam, layers in (("plain", 2), ("viashs", 2), ("viashs", 4)):
        s.append((f"analytic_{fam}_{layers}L", fam, layers, "analytic", "layer", (1.0, 0.5, 0.25)))
    return s


def klass_of(rec):
    """!
    @brief Class of a measured point for the fit.
    @param rec Record of the ladder (spec, unknowns, slabs).
    @return Key of memory_model.COEFFS, or None for the models that have no sparse factorisation (Analytic has its own, fitted by tile count in README).
    """
    sp = rec["spec"]
    if sp["model"] == "solid3d":
        return mm.classify_solid3d(rec["slabs"])
    if sp["model"] in ("fvm", "fdm"):
        # The laminate nodes of the rule exist unless a metal block is present (laminate.uses_rule); the ragged count shows whether any exist
        rule = sp["family"] != "block" and rec["unknowns"] > sp["layers"] * rec["cells"] * 1.02
        return mm.classify_layered(sp["layers"], rule)
    return "lumped" if sp["model"] == "lumped" else None


def load():
    """!
    @brief Records already measured.
    @return List of dicts (empty if the file does not exist).
    """
    if not LADDER.exists():
        return []
    return [json.loads(line) for line in LADDER.read_text().splitlines() if line.strip()]


def plan(cutoff):
    """!
    @brief Count every point of the ladder without solving it and print its provisional estimate.
    @param cutoff Bytes above which a point is skipped.
    @return List of (series name, spec, unknowns, slabs, estimate bytes, skipped).
    """
    rows = []
    for name, fam, layers, model, order, cells in series():
        for c in cells:
            spec = dict(family=fam, layers=layers, size_mm=SIZE_MM, cell_mm=c, model=model, order=order, series=name)
            n, ns = cases.count(spec)
            kl = "solid3d_many" if model == "solid3d" and ns > 6 else "solid3d_few" if model == "solid3d" else "layered_laminate_many" if layers > 2 else "layered_laminate_few"
            if model in ("lumped", "analytic"):
                kl = "lumped"
            est = mm.estimate_bytes(n, kl)
            rows.append((name, spec, n, ns, est, est * 1.5 > cutoff))
    return rows


def run(args):
    """!
    @brief Run the ladder (or its quick half), resuming from out/ladder.jsonl.
    @param args Parsed arguments.
    @return None.
    """
    OUT.mkdir(exist_ok=True)
    ram = mm.ram_bytes() or 16e9
    cutoff = min(args.cutoff_gb * 1e9 if args.cutoff_gb else 0.6 * ram, 10e9)
    done = {(r["spec"]["series"], r["spec"]["cell_mm"], r["spec"].get("mode", "solve")) for r in load()}
    print(f"physical memory {ram / 1e9:.1f} GB, cutoff {cutoff / 1e9:.1f} GB per point")
    # A baseline: the smallest board, so that the base of the program (imports, NumPy, SciPy) is measured and not assumed
    base_spec = dict(family="plain", layers=2, size_mm=20.0, cell_mm=2.0, model="fvm", order="layer", series="baseline")
    if ("baseline", 2.0, "solve") not in done:
        rec = measure.run_case(base_spec, cutoff)
        _store(rec, 0, 0)
    stopped = set()
    for name, fam, layers, model, order, cells in series():
        for c in cells:
            if args.quick and (model == "solid3d" or c < 0.7):
                continue
            spec = dict(family=fam, layers=layers, size_mm=SIZE_MM, cell_mm=c, model=model, order=order, series=name)
            if (name, c, "solve") in done:
                continue
            n, ns = cases.count(spec)
            kl = "solid3d_many" if model == "solid3d" and ns > 6 else "solid3d_few" if model == "solid3d" else "layered_laminate_many" if layers > 2 else "layered_laminate_few"
            if name in stopped or mm.estimate_bytes(n, kl) * 1.5 * args.est_scale > cutoff:
                print(f"skip {name} cell {c}: {n} unknowns, provisional estimate {mm.estimate_bytes(n, kl) / 1e9:.1f} GB x 1.5 above the cutoff")
                stopped.add(name)
                continue
            rec = measure.run_case(spec, cutoff, timeout_s=args.timeout)
            _store(rec, n, ns)
            print(f"{name} cell {c}: {n} unknowns, {rec['status']}, peak {rec['peak_bytes'] / 1e9:.2f} GB, solve {rec.get('t_solve', float('nan')):.1f} s")
            if rec["status"] != "ok":
                stopped.add(name)
    # The equality of the two orderings, small boards only
    for fam, layers, c in (("partial", 2, 2.0), ("partial", 4, 1.0), ("outline", 2, 1.0), ("plain", 4, 1.0)):
        spec = dict(family=fam, layers=layers, size_mm=SIZE_MM, cell_mm=c, model="fvm", order="layer", mode="compare", series=f"compare_{fam}_{layers}L")
        if (spec["series"], c, "compare") in done:
            continue
        rec = measure.run_case(spec, cutoff, timeout_s=args.timeout)
        _store(rec, 0, 0)
        print(f"compare {fam} {layers}L cell {c}: max difference {rec.get('max_abs_diff_K', float('nan')):.2e} K, layer-major {rec.get('t_solve_layer', 0):.1f} s, cell-major {rec.get('t_solve_cell', 0):.1f} s")


def _store(rec, n, ns):
    """!
    @brief Append a record to out/ladder.jsonl with the counts the parent made.
    @param rec Result of measure.run_case.
    @param n Unknowns counted before the run (0 for the baseline and compare records).
    @param ns Slabs of the 3D solid.
    @return None.
    """
    sp = rec["spec"]
    rec["slabs"] = ns
    rec["cells"] = max(int(round(sp["size_mm"] / sp["cell_mm"])), 2) ** 2
    rec["unknowns_parent"] = n                          # The count made before the run; "unknowns" is the child's (README 7 compares them)
    rec.setdefault("unknowns", n)
    with open(LADDER, "a") as fh:
        fh.write(json.dumps(rec) + "\n")


def fit():
    """!
    @brief Fit the coefficients of every class from out/ladder.jsonl, print the tables and write out/fit.json.
    @return None.
    """
    recs = load()
    base_rec = [r for r in recs if r["spec"]["series"] == "baseline" and r["status"] == "ok"]
    base = base_rec[0]["peak_bytes"] if base_rec else 0.4e9
    print(f"base (baseline run, peak): {base / 1e9:.2f} GB")
    groups = {}
    for r in recs:
        if r["status"] != "ok" or r["spec"].get("mode", "solve") != "solve" or r["spec"]["series"] == "baseline":
            continue
        # The cell-major points are fitted apart from the layer-major points of the same class
        k = klass_of(r)
        if k is None:
            continue
        key = k + ("@cell_major" if r["spec"].get("order") == "cell" else "")
        groups.setdefault(key, []).append((r["unknowns"], r["peak_bytes"], r.get("t_solve", np.nan), r["spec"]["series"]))
    out = {"base_bytes": base}
    for key, pts in sorted(groups.items()):
        try:
            c = mm.fit_class([(n, m) for n, m, _, _ in pts], base=base)
        except ValueError as e:
            print(f"{key}: not enough points ({e})")
            continue
        pred = np.array([mm.estimate_bytes(n, "layered_plain", {"layered_plain": c}) for n, _, _, _ in pts])
        meas = np.array([m for _, m, _, _ in pts])
        ratio = meas / pred
        # Leave the largest point out and predict it: does the law extrapolate?
        big = max(range(len(pts)), key=lambda i: pts[i][0])
        loo = None
        rest = [(n, m) for i, (n, m, _, _) in enumerate(pts) if i != big]
        if len({n for n, _ in rest}) >= 2:
            c2 = mm.fit_class(rest, base=base)
            loo = pts[big][1] / mm.estimate_bytes(pts[big][0], "layered_plain", {"layered_plain": c2})
        print(f"{key}: {len(pts)} points, p = {c.p:.2f}, k = {c.k:.0f} B/unknown at N = {mm.N_REF}, measured/fitted {ratio.min():.2f}-{ratio.max():.2f}, "
              f"largest point predicted from the others: {'-' if loo is None else f'{loo:.2f}'} {c.note}")
        # Time law t = a N^q on the same points
        tt = [(n, t) for n, _, t, _ in pts if np.isfinite(t) and t > 0]
        q = float(np.polyfit(np.log([n for n, _ in tt]), np.log([t for _, t in tt]), 1)[0]) if len(tt) >= 2 else float("nan")
        out[key] = dict(base=c.base, k=c.k, p=c.p, note=c.note, safety=float(ratio.max()), time_exponent=q, points=[(n, m) for n, m, _, _ in pts])
    FIT.write_text(json.dumps(out, indent=1))
    print(f"written {FIT}")
    for r in recs:
        if r["spec"].get("mode") == "compare" and r["status"] == "ok":
            print(f"ordering check {r['spec']['series']}: max |difference| {r['max_abs_diff_K']:.2e} K; layer-major {r['t_solve_layer']:.1f} s, cell-major {r['t_solve_cell']:.1f} s")


def main():
    """!
    @brief Command line entry.
    @return None.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--plan", action="store_true", help="list the points and the provisional estimates, run nothing")
    ap.add_argument("--run", action="store_true", help="run the ladder")
    ap.add_argument("--fit", action="store_true", help="fit the coefficients from out/ladder.jsonl")
    ap.add_argument("--quick", action="store_true", help="coarse points only (cell >= 0.7 mm, no 3D)")
    ap.add_argument("--cutoff-gb", type=float, default=0.0, help="memory cutoff per point in GB (default 60 %% of the RAM, at most 10)")
    ap.add_argument("--est-scale", type=float, default=1.0, help="factor on the provisional estimate in the skip rule (the first pass showed the provisional coefficients about 2 to 3 times too high for the layered models; the watchdog at the cutoff stays)")
    ap.add_argument("--timeout", type=float, default=900.0, help="seconds per point")
    a = ap.parse_args()
    if a.plan:
        ram = mm.ram_bytes() or 16e9
        cutoff = min(a.cutoff_gb * 1e9 if a.cutoff_gb else 0.6 * ram, 10e9)
        for name, spec, n, ns, est, skip in plan(cutoff):
            print(f"{name:34s} cell {spec['cell_mm']:5.2f} mm {n:>9d} unknowns {ns:>3d} slabs  provisional {est / 1e9:5.1f} GB {'SKIP' if skip else ''}")
    if a.run:
        run(a)
    if a.fit:
        fit()
    if not (a.plan or a.run or a.fit):
        ap.print_help()


if __name__ == "__main__":
    main()
