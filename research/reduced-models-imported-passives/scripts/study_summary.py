#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_summary.py
@brief Tables of the error chain of the reduced models from the CSV files of study_error_decomposition.py: geometric-mean factor of each step by size class and board.
@details Chain for the rise of a part: F_imp (FVM on the imported copper) is compared step by step with the FVM on the arithmetic cell fill (F_fill), on tiles of 1, 2, 5, 10 mm
         (F_t*), on one uniform sheet per layer (F_unif); then the Lumped and Analytic on the imported board (L_imp, A_imp) and on the uniform sheet (L_unif, A_unif). Prints, per board
         and size class (side of the footprint < 1.5 mm, 1.5 to 3, above 3), the geometric mean and the range of every factor. Run after the decomposition:
         .venv/bin/python research/reduced-models-imported-passives/scripts/study_summary.py
"""

import csv
import sys
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parents[1] / "out"
CLASSES = (("side < 1.5 mm", 0.0, 1.5), ("1.5 to 3 mm", 1.5, 3.0), ("side > 3 mm", 3.0, 1e9))
FACTORS = (("F_t10/F_unif", "F_t10", "F_unif"), ("F_t5/F_t10", "F_t5", "F_t10"), ("F_t2/F_t5", "F_t2", "F_t5"), ("F_t1/F_t2", "F_t1", "F_t2"),
           ("F_fill/F_t1", "F_fill", "F_t1"), ("F_imp/F_fill", "F_imp", "F_fill"), ("F_imp/F_unif (all copper structure)", "F_imp", "F_unif"),
           ("L_unif/F_unif (model on a uniform sheet)", "L_unif", "F_unif"), ("A_unif/F_unif", "A_unif", "F_unif"),
           ("L_imp/L_unif (does the model see the pattern)", "L_imp", "L_unif"), ("A_imp/A_unif", "A_imp", "A_unif"),
           ("L_imp/F_imp (what the user sees)", "L_imp", "F_imp"), ("A_imp/F_imp", "A_imp", "F_imp"),
           ("F_nov/F_imp (vias removed)", "F_nov", "F_imp"), ("L_nov/L_imp", "L_nov", "L_imp"))


def load():
    """!
    @brief Read every decomposition CSV in out/.
    @return list of dict rows with numbers as floats.
    """
    rows = []
    for p in sorted(OUT.glob("decomposition_*_*.csv")):
        if p.stem.endswith("_kappa"):
            continue
        for r in csv.DictReader(open(p)):
            rows.append({k: (float(v) if k not in ("board", "part") else v) for k, v in r.items()})
    return rows


def main(argv):
    """!
    @brief Print the factor tables.
    @param argv Unused.
    @return int Exit code.
    """
    rows = load()
    for board in sorted({r["board"] for r in rows}):
        sel = [r for r in rows if r["board"] == board]
        print("\n== %s (%d parts, cell %g mm) ==" % (board, len(sel), sel[0]["cell"]))
        for cname, lo, hi in CLASSES:
            s = [r for r in sel if lo <= r["side_mm"] < hi]
            if not s:
                continue
            print("  %s (n=%d)" % (cname, len(s)))
            for name, a, b in FACTORS:
                x = np.array([r[a] / r[b] for r in s])
                print("    %-48s geo-mean %.2f  range %.2f to %.2f" % (name, np.exp(np.log(x).mean()), x.min(), x.max()))
    print("\n== pooled, all boards (%d parts): error of the models against the FVM on the imported copper, by size class ==" % len(rows))
    for cname, lo, hi in CLASSES:
        s = [r for r in rows if lo <= r["side_mm"] < hi]
        if s:
            eL = np.array([100 * (r["L_imp"] / r["F_imp"] - 1) for r in s]); eA = np.array([100 * (r["A_imp"] / r["F_imp"] - 1) for r in s])
            print("  %-14s n=%2d  Lumped %+.0f to %+.0f %% (mean %+.0f)  Analytic %+.0f to %+.0f %% (mean %+.0f)" % (cname, len(s), eL.min(), eL.max(), eL.mean(), eA.min(), eA.max(), eA.mean()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
