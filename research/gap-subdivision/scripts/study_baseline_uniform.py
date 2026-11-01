#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_baseline_uniform.py
@brief Baseline of the program on uniform boards (no patterned copper): the five models against the exact series solution, over layers, gaps, copper, source, board, cell, h and the stack-up mode.
@details Question: how far is every model of the program, as it is today, from the exact answer of a laminated plate with a square source when the copper has no pattern? The reference
         is lib/series.py (no mesh; the peak is the mean over the hottest cell of the model's own size, so that the comparison is like for like). Two parts: `one-at-a-time` sweeps around a base
         board (2 layers, 1.6 mm, 35 um, 30 mm, 6 mm source, 1 W, h 10 / 10, cell 0.5 mm) and a `grid` of layers x gap x source x cell x h.
         Output: baseline/uniform.csv (committed, small) with the board, the cell, the reference and the five peaks and their energy-balance errors; a summary on the screen.
         Usage: .venv/bin/python research/gap-subdivision/scripts/study_baseline_uniform.py [--grid]   (from the repository root; the sweeps take about a minute, the grid a few).
"""

import csv
import sys
import time
from dataclasses import replace

import _bootstrap as BS
import boards as B

BASE = B.Board("base", layers=2, gap=1.6, copper=35.0, size=30.0, source=6.0, power=1.0, h_top=10.0, h_bottom=10.0, stack="advanced")
CELL = 0.5
FIELDS = ["sweep", "layers", "gap_mm", "copper_um", "size_mm", "source_mm", "h_top", "h_bottom", "stack", "cell_mm", "ref_K"] + \
    [f"{m}_K" for m in B.MODELS] + [f"{m}_bal" for m in B.MODELS]


def one_at_a_time():
    """!
    @brief The one-at-a-time sweeps around the base board.
    @return List of (sweep name, Board, cell in mm).
    """
    rows = []
    for l in (2, 3, 4, 6, 8):
        rows.append(("layers", replace(BASE, layers=l), CELL))
    for g in (0.1, 0.2, 0.4, 0.8, 1.6, 3.2):
        rows.append(("gap", replace(BASE, gap=g), CELL))
    for cu in (17.5, 35.0, 70.0, 105.0):
        rows.append(("copper", replace(BASE, copper=cu), CELL))
    for s in (2.0, 4.0, 6.0, 12.0, 20.0, 28.0):
        rows.append(("source", replace(BASE, source=s), CELL))
    for sz in (20.0, 30.0, 60.0, 100.0):
        rows.append(("board", replace(BASE, size=sz), CELL if sz <= 60 else 1.0))
    for c in (2.0, 1.0, 0.5, 0.25):
        rows.append(("cell", BASE, c))
    for h in (2.0, 5.0, 10.0, 25.0, 100.0, 500.0):
        rows.append(("h", replace(BASE, h_top=h, h_bottom=h), CELL))
    rows.append(("h_one_face", replace(BASE, h_top=10.0, h_bottom=0.0), CELL))
    for l in (3, 4, 6, 8):
        rows.append(("stack", replace(BASE, layers=l, stack="simple"), CELL))
        rows.append(("stack", replace(BASE, layers=l, stack="advanced"), CELL))
    return rows


def grid():
    """!
    @brief The grid layers x gap x source x cell x h.
    @return List of (sweep name, Board, cell in mm).
    """
    rows = []
    for l in (2, 3, 4, 6, 8):
        for g in (0.1, 0.2, 0.4, 0.8, 1.6):
            for s in (2.0, 6.0, 12.0):
                for h in (10.0, 100.0):
                    for c in (1.0, 0.5):
                        rows.append(("grid", replace(BASE, layers=l, gap=g, source=s, h_top=h, h_bottom=h), c))
    return rows


def run(rows, path):
    """!
    @brief Run the rows and write the CSV.
    @param rows List of (sweep, Board, cell).
    @param path Output file.
    @return List of dict rows.
    """
    out = []
    t0 = time.time()
    for sweep, bd, cell in rows:
        p = B.problem(bd)
        ref = B.exact_peak(bd, cell, p)
        res = B.all_models(bd, cell, p)
        row = {"sweep": sweep, "layers": bd.layers, "gap_mm": bd.gap, "copper_um": bd.copper, "size_mm": bd.size, "source_mm": bd.source, "h_top": bd.h_top, "h_bottom": bd.h_bottom,
               "stack": bd.stack, "cell_mm": cell, "ref_K": round(ref, 5)}
        for m in B.MODELS:
            row[f"{m}_K"] = round(res[m][0], 5)
            row[f"{m}_bal"] = f"{res[m][1]:.2e}"
        out.append(row)
    with open(path, "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=FIELDS)
        wr.writeheader()
        wr.writerows(out)
    print(f"{len(out)} boards in {time.time() - t0:.0f} s -> {path}")
    return out


def show(rows):
    """!
    @brief Print the one-at-a-time table: error of every model against the exact series in percent.
    @param rows List of dict rows.
    @return None.
    """
    print(f"{'sweep':11s} {'L':>2s} {'gap':>5s} {'cu':>5s} {'size':>5s} {'src':>5s} {'h':>5s} {'stack':>8s} {'cell':>5s} {'ref K':>8s}  " + " ".join(f"{m:>8s}" for m in B.MODELS))
    for r in rows:
        errs = " ".join(f"{100 * (float(r[f'{m}_K']) / float(r['ref_K']) - 1):+8.2f}" for m in B.MODELS)
        print(f"{r['sweep']:11s} {r['layers']:2d} {r['gap_mm']:5.2f} {r['copper_um']:5.1f} {r['size_mm']:5.0f} {r['source_mm']:5.1f} {r['h_top']:5.0f} {r['stack']:>8s} {r['cell_mm']:5.2f} {float(r['ref_K']):8.2f}  {errs}")


def main(argv):
    """!
    @brief Run the one-at-a-time sweeps (and the grid with --grid) and print the tables.
    @param argv Command line arguments.
    @return None.
    """
    rows = run(one_at_a_time(), BS.BASELINE / "uniform.csv")
    show(rows)
    if "--grid" in argv:
        g = run(grid(), BS.BASELINE / "uniform_grid.csv")
        for m in B.MODELS:
            e = [100 * (float(r[f"{m}_K"]) / float(r["ref_K"]) - 1) for r in g if r[f"{m}_K"] == r[f"{m}_K"]]
            print(f"grid {m:9s} n={len(e):3d} mean {sum(e) / len(e):+.2f} %  min {min(e):+.2f}  max {max(e):+.2f}  mean abs {sum(abs(x) for x in e) / len(e):.2f}")


if __name__ == "__main__":
    main(sys.argv[1:])
