#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_copper_mapping.py
@brief Which copper mapping should an import use by default: the program's arithmetic fill fraction, the flow-based faces, or another, on real boards, with the program of 2.4.5 (laminate rule, point via), a finer pixel and the nine-point reference?
@details Part A (one conducting sheet, isolates the mapping): windows of 36 mm cut from the top copper of every downloaded board (scripts/fetch_boards.py), coverage mask at 0.05 mm, cells of 0.5 and 1.0 mm, heater of 6 mm;
         methods: fill fraction (what the program does), geometric mean, lambda 0.5, flow-based faces, flow-based faces with half the diagonal couplings; references: the five-point and the nine-point pixel solution
         (research/gerber-models README 4.44). Part B (the program's own network, every copper layer, plated holes as vias, laminate rule of 2.4.5): windows of 24 mm of the multilayer boards imported at
         0.05 mm, cells of 0.5 and 1.0 mm, the program as it is (one zone per cell, fill = coverage), the flow-based and the lambda 0.5 faces, against the program's pixel run.
         Output: out/copper_mapping.json (every window and the summary); the summary table is printed.
         Success criterion (set before the run): the default is the method with the smallest mean absolute error of the heater mean in Part B, provided its worst window is within 10 % and it beats the fill fraction by a factor of 2
         in the mean; the nine-point reference decides ties in Part A. NOT verified: any measurement on a physical board; copper thickness other than the program's default; heaters other than a 6 mm square on the top layer.
         Run (from the repository root): .venv-research/bin/python research/gerber-real-boards/scripts/study_copper_mapping.py [--quick] [--part A|B]
         (--quick: two windows per board, pixel 0.1 mm, cells 1.0 mm only; the full run is long: expect about two hours on a quiet 10-core machine with 16 GB; run after the other studies are done.)
"""

import _bootstrap  # noqa: F401  (puts the import paths in order)

import json
import sys
import time

import numpy as np

import boardrun
import onesheet
import native_gerber as ng
import registry
import rb_paths


def part_a(quick):
    """!
    @brief Part A: the one-sheet comparison on windows of every available board.
    @param quick True for the reduced run.
    @return list of dicts (board, window position, copper fractions, ref5, ref9, errors).
    """
    pix = 0.1 if quick else 0.05
    cells = (1.0,) if quick else (0.5, 1.0)
    rows = []
    for key in registry.available():
        r = registry.roles(key)
        box = ng.layer_bbox(r["outline"]) if r["outline"] else ng.layer_bbox(r["copper"][0])
        for w in onesheet.cut_windows(r["copper"][0], box, per_board=2 if quick else 6, pix=pix):
            t = time.time()
            res = onesheet.run_window(w.pop("coverage"), pix, cells, with_reference9=not quick)
            res.update(board=key, x_left=w["x_left"], y_bottom=w["y_bottom"], copper_fraction=w["copper_fraction"], heater_fraction=w["heater_fraction"])
            rows.append(res)
            print(f"A {key} window ({w['x_left']}, {w['y_bottom']}): copper {w['copper_fraction']:.2f}, heater block {w['heater_fraction']:.2f}, {time.time() - t:.0f} s", flush=True)
    return rows


def part_b(quick):
    """!
    @brief Part B: the program's own network on imported windows of the multilayer boards.
    @param quick True for the reduced run.
    @return list of dicts (board, window, cell, read-outs of every run, errors against the program's pixel run).
    """
    pix = 0.1 if quick else 0.05
    cells = (1.0,) if quick else (0.5, 1.0)
    rows = []
    size, heater = 24.0, 6.0
    for key in registry.available():
        r = registry.roles(key)
        if len(r["copper"]) < 2:
            continue
        box0 = ng.layer_bbox(r["outline"]) if r["outline"] else ng.layer_bbox(r["copper"][0])
        for w in onesheet.cut_windows(r["copper"][0], box0, per_board=1 if quick else 3, pix=pix, window=size, heater=heater, seed=11):
            box = (w["x_left"], w["y_bottom"], w["x_left"] + size, w["y_bottom"] + size)
            for c in cells:
                t = time.time()
                ib = boardrun.import_window(key, box, pix, c)
                centre = (size / 2.0, size / 2.0)
                p = boardrun.make_problem(ib, centre, heater)
                out = boardrun.program_runs(ib, p, centre, heater)
                ref = out["fine"][0]
                rec = {"board": key, "x_left": w["x_left"], "y_bottom": w["y_bottom"], "cell": c, "pix": pix, "layers": len(ib.layers), "holes": len(ib.holes), "reference_mean_K": ref,
                       "errors_percent": {k: boardrun.percent(out[k][0], ref) for k in ("today", "flow", "lambda")}, "seconds": time.time() - t}
                rows.append(rec)
                print(f"B {key} ({w['x_left']}, {w['y_bottom']}) cell {c}: reference {ref:.1f} K; " + ", ".join(f"{k} {v:+.1f} %" for k, v in rec["errors_percent"].items()), flush=True)
    return rows


def summarise(rows_a, rows_b):
    """!
    @brief Print and return the summary tables.
    @param rows_a Part A rows.
    @param rows_b Part B rows.
    @return dict with the means and the maxima of the absolute errors per method (and cell size).
    """
    summ = {"A": {}, "B": {}}
    for ref in ("5", "9"):
        for c in sorted({c for r in rows_a for c in r["errors"]}):
            methods = sorted({m for r in rows_a for m in r["errors"].get(c, {})})
            for m in methods:
                v = np.array([r["errors"][c][m][ref] for r in rows_a if c in r["errors"] and not np.isnan(r["errors"][c][m][ref])])
                if v.size:
                    summ["A"][f"ref{ref} cell {c} {m}"] = {"n": int(v.size), "mean_abs": float(np.abs(v).mean()), "max_abs": float(np.abs(v).max()), "bias": float(v.mean())}
    for c in sorted({r["cell"] for r in rows_b}):
        for m in ("today", "flow", "lambda"):
            v = np.array([r["errors_percent"][m] for r in rows_b if r["cell"] == c])
            summ["B"][f"cell {c} {m}"] = {"n": int(v.size), "mean_abs": float(np.abs(v).mean()), "max_abs": float(np.abs(v).max()), "bias": float(v.mean())}
    for part in ("A", "B"):
        print(f"\nPart {part}: mean absolute error, maximum, bias (percent of the heater mean rise)")
        for k, v in summ[part].items():
            print(f"  {k:48s} n={v['n']:3d}  mean {v['mean_abs']:6.2f}  max {v['max_abs']:6.2f}  bias {v['bias']:+6.2f}")
    return summ


def main(argv):
    """!
    @brief Run the parts asked for and write out/copper_mapping.json.
    @param argv Command-line words: --quick, --part A or B.
    @return None.
    """
    quick = "--quick" in argv
    part = argv[argv.index("--part") + 1] if "--part" in argv else "AB"
    if not registry.available():
        raise SystemExit("no board in data/: run research/gerber-real-boards/scripts/fetch_boards.py first")
    a = part_a(quick) if "A" in part else []
    b = part_b(quick) if "B" in part else []
    rb_paths.OUT.mkdir(parents=True, exist_ok=True)
    s = summarise(a, b)
    with open(rb_paths.OUT / "copper_mapping.json", "w") as fh:
        json.dump({"quick": quick, "part_a": a, "part_b": b, "summary": s}, fh, indent=1)


if __name__ == "__main__":
    main(sys.argv[1:])
