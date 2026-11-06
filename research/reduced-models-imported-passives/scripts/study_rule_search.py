#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_rule_search.py
@brief Is there an easy rule, computable before the run, that separates the parts the reduced models read within 35 % from the ones they read 50 % or more too cold?
@details Pools every row of out/decomposition_*.csv (RP2040, oswlight, co60 subsets) and, for each local variable the program could compute from the masks and the part (side, area, copper
         under the part, fill in 2, 5 and 10 mm squares, distance to bare laminate, constriction factor when the kappa file exists), prints the Spearman correlation with the Lumped error and the
         AUC of the variable as a classifier of "error below -50 %". An AUC near 0.5 means no rule; 0.8 or more would be a candidate. Also prints the best and the worst error of the pool.
         Run after the decomposition studies: .venv/bin/python research/reduced-models-imported-passives/scripts/study_rule_search.py
"""

import csv
import sys
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

OUT = Path(__file__).resolve().parents[1] / "out"


def auc(x, y):
    """!
    @brief Area under the ROC curve of x as a score for the boolean y (Mann-Whitney form; 0.5 is chance).
    @param x Scores.
    @param y Boolean labels.
    @return float AUC, or nan when one class is empty.
    """
    pos, neg = x[y], x[~y]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    cmp = (pos[:, None] > neg[None, :]).mean() + 0.5 * (pos[:, None] == neg[None, :]).mean()
    return float(cmp)


def main(argv):
    """!
    @brief Print the correlation and AUC table.
    @param argv Unused.
    @return int Exit code.
    """
    rows = []
    for p in sorted(OUT.glob("decomposition_*_*.csv")):
        if p.stem.endswith("_kappa"):
            continue
        rows += [{k: (float(v) if k not in ("board", "part") else v) for k, v in r.items()} for r in csv.DictReader(open(p))]
    errL = np.array([100 * (r["L_imp"] / r["F_imp"] - 1) for r in rows])
    errA = np.array([100 * (r["A_imp"] / r["F_imp"] - 1) for r in rows])
    print("pool: %d parts; Lumped error %.0f to %.0f %%, Analytic %.0f to %.0f %%; below -50 %%: Lumped %d, Analytic %d" % (
        len(rows), errL.min(), errL.max(), errA.min(), errA.max(), (errL < -50).sum(), (errA < -50).sum()))
    bad = errL < -50
    for k in ("side_mm", "area_mm2", "under", "fill_2", "fill_5", "fill_10", "dist_bare_mm", "bottom_5"):
        x = np.array([r[k] for r in rows])
        print("%-14s Spearman with the Lumped error %+.2f   AUC for 'below -50 %%' %.2f (score: the variable) / %.2f (score: minus the variable)" % (
            k, spearmanr(x, errL)[0], auc(x, bad), auc(-x, bad)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
