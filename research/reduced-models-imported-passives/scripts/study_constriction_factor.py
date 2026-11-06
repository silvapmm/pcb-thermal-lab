#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_constriction_factor.py
@brief Which variable explains the error of the reduced models: the constriction factor of the copper around the part against the local fill, the distance to bare laminate and the size of the part.
@details Reads out/decomposition_<board>_<cell>.csv (study_error_decomposition.py), adds for every part the in-plane constriction factor kappa_R of the top-layer mask
         (R of the real pattern between the pad and the frame of a square window of half side R, divided by R of the same window filled with copper; lib/constriction.py), and prints
         the rank correlations (Spearman) of the ratios F_imp / F_fill (what the flow-based faces add to the cell fill) and L_imp / F_imp, A_imp / F_imp with each variable.
         Run: .venv/bin/python research/reduced-models-imported-passives/scripts/study_constriction_factor.py rp2040 0.5
         Not verified: only the top layer's pattern enters kappa (the vias and the second layer are not in it).
"""

import csv
import sys
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))

import constriction  # noqa: E402
import variants as V  # noqa: E402

WINDOWS = (2.0, 5.0)                 # Half sides in mm


def main(argv):
    """!
    @brief Add kappa to the decomposition table and print the correlations.
    @param argv board, cell in mm.
    @return int Exit code.
    """
    board = argv[1] if len(argv) > 1 else "rp2040"
    cell = float(argv[2]) if len(argv) > 2 else 0.5
    path = HERE.parent / "out" / ("decomposition_%s_%g.csv" % (board, cell))
    rows = list(csv.DictReader(open(path)))
    sx, prob = V.open_board(board, cell)
    for r in rows:
        q = V.only_heater(prob, r["part"])
        for hw in WINDOWS:
            cov, pad = V.window_and_pad(q, r["part"], hw)
            k, R, Rf = constriction.kappa(cov, pad, hw)
            r["kappa_%g" % hw] = k
            r["Rsq_%g" % hw] = R
    keys = list(rows[0].keys())
    with open(path.with_name(path.stem + "_kappa.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader(); w.writerows(rows)
    num = lambda k: np.array([float(r[k]) for r in rows])
    F, Ff, Fu, L, A = num("F_imp"), num("F_fill"), num("F_unif"), num("L_imp"), num("A_imp")
    ys = {"F_imp/F_fill": F / Ff, "L/F_imp": L / F, "A/F_imp": A / F, "F_fill/F_imp": Ff / F, "F_unif/F_imp": Fu / F}
    xs = {"kappa_2": num("kappa_2"), "kappa_5": num("kappa_5"), "fill_2": num("fill_2"), "fill_5": num("fill_5"), "fill_10": num("fill_10"),
          "dist_bare": num("dist_bare_mm"), "side": num("side_mm"), "under": num("under")}
    print("board %s cell %g, %d parts; Spearman rho (p) of each ratio against each variable" % (board, cell, len(rows)))
    print("%-14s" % "" + "".join("%-18s" % k for k in xs))
    for yn, y in ys.items():
        line = "%-14s" % yn
        for xn, x in xs.items():
            ok = np.isfinite(x) & np.isfinite(y)
            rho, p = spearmanr(x[ok], y[ok])
            line += "%+.2f (%.3f)    " % (rho, p)
        print(line)
    print("kappa_5 per part:", ", ".join("%s %.2f" % (r["part"], r["kappa_5"]) for r in rows))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
