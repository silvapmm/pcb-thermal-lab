#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_error_decomposition.py
@brief Why the Lumped and Analytic models read too cold on the heat sources of an imported board: the error cut into steps, part by part.
@details Question: the reduced models read 31 to 75 % below the FVM on the small parts of the RP2040 (docs/validation.md 27.7). The same program is run, one part at a time with 1 W,
         on the imported copper (FVM faces) and on variants that keep everything but the copper: the arithmetic cell fill of the same masks ("fill"), tiles of T mm with the mask
         average (T = 1, 2, 5, 10 mm), one zone per layer with the layer average ("uniform"), and the imported board without vias. The Lumped and Analytic run on each variant
         as the program runs them. The local measures of the copper around the part (fill in squares of 2, 5 and 10 mm, distance to the nearest copper-free pixel, copper
         under the part, size of the part) are written beside the rises. Output: a CSV in out/ (git-ignored) and a table on the screen.
         Run from the repository root (one solve at a time, about 0.5 GB):
         eval "$(pcb-library/scripts/link_env.sh)"; .venv/bin/python research/reduced-models-imported-passives/scripts/study_error_decomposition.py rp2040 0.5 [U1,U3,...]
         Not verified: a physical board; boards other than the three of the library.
"""

import csv
import resource
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))

import variants as V  # noqa: E402
from pcbthermal import api  # noqa: E402

TILES = (1.0, 2.0, 5.0, 10.0)           # Tile sides in mm


def rises(problem, models, cell):
    """!
    @brief Rise of the hottest node of each model above the ambient.
    @param problem Problem.
    @param models Tuple of model keys.
    @param cell Cell in mm.
    @return dict key -> K.
    """
    sim = api.simulate(problem, api.SolverOptions(models=tuple(models), cell_mm=cell))
    return {m: r.t_max - problem.board.ambient for m, r in sim.results.items()}


def main(argv):
    """!
    @brief Run the decomposition for one board.
    @param argv board folder name, cell in mm, optional comma-separated designators.
    @return int Exit code.
    """
    board = argv[1] if len(argv) > 1 else "rp2040"
    cell = float(argv[2]) if len(argv) > 2 else 0.5
    only = argv[3].split(",") if len(argv) > 3 else None
    sx, prob = V.open_board(board, cell)
    names = [h.name for h in prob.heaters if only is None or h.name in only]
    out = HERE.parent / "out"
    out.mkdir(exist_ok=True)
    rows = []
    for n in names:
        t0 = time.time()
        q = V.only_heater(prob, n)
        row = {"board": board, "cell": cell, "part": n}
        row.update(V.local_measures(q, n))
        r = rises(q, ("fvm", "lumped", "analytic"), cell)
        row.update({"F_imp": r["fvm"], "L_imp": r["lumped"], "A_imp": r["analytic"]})
        row["F_fill"] = rises(V.variant(q, "fill"), ("fvm",), cell)["fvm"]
        for T in TILES:
            row["F_t%g" % T] = rises(V.variant(q, "tiles", T), ("fvm",), cell)["fvm"]
        r = rises(V.variant(q, "tiles", 5.0), ("lumped", "analytic"), cell)
        row.update({"L_t5": r["lumped"], "A_t5": r["analytic"]})
        r = rises(V.variant(q, "uniform"), ("fvm", "lumped", "analytic"), cell)
        row.update({"F_unif": r["fvm"], "L_unif": r["lumped"], "A_unif": r["analytic"]})
        r = rises(V.variant(q, "novias"), ("fvm", "lumped", "analytic"), cell)
        row.update({"F_nov": r["fvm"], "L_nov": r["lumped"], "A_nov": r["analytic"]})
        rows.append(row)
        print("%-5s side %.2f fill5 %.2f dbare %.2f | F_imp %.1f F_fill %.1f F_t2 %.1f F_t5 %.1f F_unif %.1f | L %+.0f%% A %+.0f%% | L_unif %+.0f%% (%.1fs)" % (
            n, row["side_mm"], row["fill_5"], row["dist_bare_mm"], row["F_imp"], row["F_fill"], row["F_t2"], row["F_t5"], row["F_unif"],
            100 * (row["L_imp"] / row["F_imp"] - 1), 100 * (row["A_imp"] / row["F_imp"] - 1), 100 * (row["L_unif"] / row["F_unif"] - 1), time.time() - t0), flush=True)
    path = out / ("decomposition_%s_%g.csv" % (board, cell))
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("written", path, "peak RSS %.2f GB" % (resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2 ** 30))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
