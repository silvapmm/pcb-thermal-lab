#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file rerun_baseline.py
@brief Re-run the five models of the program on the boards of the committed baseline (baseline/uniform.csv, baseline/pads.csv) and report how far every peak has moved: the tool to judge a change of the program against the common reference.
@details The references (exact series, converged graded 3D solver) are stored in the CSV files and are not recomputed. For every row the board is rebuilt, the five models are run, and the change of each model's peak
         against the stored value is printed as a percentage of the rise, together with the error against the reference before and after. Use it before and after a change of `pcbthermal/` (a proposal of a
         research folder on a copy, or a fix branch): the rows that should not move must not move (full copper boards), and the rows that should move must move towards the reference.
         Usage: .venv/bin/python research/gap-subdivision/scripts/rerun_baseline.py [--update] [--models fvm,fdm]   (from the repository root; about two minutes). `--update` rewrites the model columns of the CSV files.
"""

import csv
import sys

import _bootstrap as BS
import boards as B
import study_baseline_pads as SP


def uniform_board(r):
    """!
    @brief Rebuild a Board from a row of uniform.csv.
    @param r Row.
    @return Board.
    """
    return B.Board("u", layers=int(r["layers"]), gap=float(r["gap_mm"]), copper=float(r["copper_um"]), size=float(r["size_mm"]), source=float(r["source_mm"]), h_top=float(r["h_top"]),
                   h_bottom=float(r["h_bottom"]), stack=r["stack"])


def pad_board(r):
    """!
    @brief Rebuild a Board from a row of pads.csv.
    @param r Row.
    @return Board.
    """
    bd = B.Board("p", layers=int(r["layers"]), gap=float(r["gap_mm"]), copper=float(r["copper_um"]), size=float(r["size_mm"]), source=float(r["source_mm"]), h_top=float(r["h_top"]),
                 h_bottom=float(r["h_bottom"]), stack=r["stack"], pad=float(r["pad_mm"]), pad_layers=(0,))
    return SP.bottom_cfg(bd, r["bottom"])


def main(argv):
    """!
    @brief Re-run both baselines and print the movement of every model.
    @param argv Command line arguments.
    @return None.
    """
    models = B.MODELS
    if "--models" in argv:
        models = tuple(argv[argv.index("--models") + 1].split(","))
    for name, build in (("uniform.csv", uniform_board), ("pads.csv", pad_board)):
        path = BS.BASELINE / name
        with open(path) as fh:
            rows = list(csv.DictReader(fh))
        worst = {m: 0.0 for m in models}
        print(f"\n{name}: {len(rows)} boards; change of the peak against the stored one (% of the rise), then error against the reference (stored -> now)")
        for r in rows:
            bd = build(r)
            res = B.all_models(bd, float(r["cell_mm"]), None, models)
            ref = float(r["ref_K"])
            cells = []
            for m in models:
                old, new = float(r[f"{m}_K"]), res[m][0]
                if new != new or old != old:
                    continue
                d = 100 * (new / old - 1)
                worst[m] = max(worst[m], abs(d))
                if "--update" in argv:
                    r[f"{m}_K"] = round(new, 5 if name == "uniform.csv" else 4)
                cells.append(f"{m} {d:+.3f} ({100 * (old / ref - 1):+.2f} -> {100 * (new / ref - 1):+.2f})")
            tag = r.get("tag") or f"{r['sweep']} L{r['layers']} gap {r['gap_mm']}"
            if any(abs(float(c.split()[1])) > 1e-6 for c in cells):
                print(f"  {tag:30s} " + "; ".join(cells))
        print("  largest movement per model: " + ", ".join(f"{m} {worst[m]:.4f} %" for m in models))
        if "--update" in argv:
            with open(path, "w", newline="") as fh:
                wr = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
                wr.writeheader()
                wr.writerows(rows)


if __name__ == "__main__":
    main(sys.argv[1:])
