#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_fin_check.py
@brief Independent check of the copper-structure factor: a pixel-resolved fin model of the top copper layer alone against the FVM's ratio F_imp / F_unif.
@details The FVM on the imported copper is compared with the FVM on the layer-average sheet (F_imp / F_unif, out/decomposition_<board>_<cell>.csv). Here the same ratio is predicted by a
         separate, much simpler calculation that shares no code with the program: the top-layer mask at its own pixel (0.05 mm) as a resistor network (lib/constriction.py, tested against the
         disc and strip closed forms and the fin solution of Carslaw and Jaeger, status M), every pixel leaking to the ambient with a fin length lambda (the vertical path of the board, a free
         parameter swept at 0.5, 0.75, 1 and 2 mm), the part's copper pixels as one node, 1 W; ratio = pad temperature on the real pattern / pad temperature on the same window filled with the layer-average
         fill. It has no second layer and no vias, so only the ratio is compared, not a temperature. Prints the geometric mean of the predicted and of the FVM ratio and their rank correlation.
         Run: .venv/bin/python research/reduced-models-imported-passives/scripts/study_fin_check.py rp2040 0.5
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
from pcbthermal import copper  # noqa: E402

LAMBDAS_MM = (0.5, 0.75, 1.0, 2.0)
HALF_MM = 8.0


def main(argv):
    """!
    @brief Predict F_imp / F_unif with the fin network and compare.
    @param argv board, cell in mm.
    @return int Exit code.
    """
    board = argv[1] if len(argv) > 1 else "rp2040"
    cell = float(argv[2]) if len(argv) > 2 else 0.5
    rows = list(csv.DictReader(open(HERE.parent / "out" / ("decomposition_%s_%g.csv" % (board, cell)))))
    sx, prob = V.open_board(board, cell)
    ras = copper.CopperSource.of(prob).raster(0).astype(float) / 255.0
    mean_fill = float(ras[ras > -1].mean())
    pix = copper.CopperSource.of(prob).pix * 1e3
    fvm = np.array([float(r["F_imp"]) / float(r["F_unif"]) for r in rows])
    out = {}
    for lam in LAMBDAS_MM:
        pred = []
        for r in rows:
            q = V.only_heater(prob, r["part"])
            cov, pad = V.window_and_pad(q, r["part"], HALF_MM)
            fixed = np.zeros(cov.shape, bool); fixed[0, :] = fixed[-1, :] = fixed[:, 0] = fixed[:, -1] = True
            leak = (pix / lam) ** 2
            R = constriction.resistance(cov, pad & ~fixed, fixed, leak=leak)
            Ru = constriction.resistance(np.full_like(cov, mean_fill), pad & ~fixed, fixed, leak=leak)
            pred.append(R / Ru if np.isfinite(R) else float("inf"))
        pred = np.array(pred)
        ok = np.isfinite(pred)
        rho = spearmanr(pred[ok], fvm[ok])[0]
        out[lam] = pred
        print("lambda %.2f mm: predicted ratio geo-mean %.2f (range %.2f to %.2f, %d cut off) | FVM geo-mean %.2f | Spearman %.2f" % (
            lam, np.exp(np.log(pred[ok]).mean()), pred[ok].min(), pred[ok].max(), (~ok).sum(), np.exp(np.log(fvm).mean()), rho))
        # Prototype on a copy: the Lumped / Analytic rise multiplied by the predicted structure factor, against the FVM on the imported copper
        for key, nm in (("L_imp", "Lumped"), ("A_imp", "Analytic")):
            e = np.array([100 * (float(r[key]) * pr / float(r["F_imp"]) - 1) for r, pr in zip(rows, pred)])[ok]
            e0 = np.array([100 * (float(r[key]) / float(r["F_imp"]) - 1) for r in rows])[ok]
            print("   %s: error %+.0f to %+.0f %% (mean %+.0f %%) as run; times the factor: %+.0f to %+.0f %% (mean %+.0f %%, mean absolute %.0f %%)" % (
                nm, e0.min(), e0.max(), e0.mean(), e.min(), e.max(), e.mean(), abs(e).mean()))
    print("per part (lambda 1 mm): " + ", ".join("%s %.2f/%.2f" % (r["part"], p, f) for r, p, f in zip(rows, out[1.0], fvm)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
