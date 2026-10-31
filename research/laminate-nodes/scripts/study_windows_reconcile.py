#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_windows_reconcile.py
@brief Why the real windows of this folder disagreed with gerber-models R2, and the rule against R2's own independent 3D solution (review).
@details Question answered: the first run of study_windows_real.py gave the program -27 to -62 % on the seven real windows where gerber-models R2 gave -5.5 to -13.6 %. Two causes
         were found by the review: (1) the preset "program" did not take the fill of the mask (lib/gapnet.py returned before applying it, so the program solved the full-copper
         placeholder board of `problem()`), fixed in gapnet.apply_ladder; (2) this folder reads the masks as stored (row 0 at the top of the image) while R2 flips them, so its windows
         are mirror images of R2's and the off-centre heater sits over different copper. This script runs the program, the rule and eight nodes everywhere on R2's orientation
         (`flip=True`) and compares them with the 3D heater means that R2's own solver printed (`research/gerber-models/scripts/study_laminate_reference.py`, its output
         `out/study_laminate_reference.txt`, column "3D (K)"; an independent solver written in that study, not ref3d.py), at the 0.2 mm pixel and the 0.8 mm cell. The metric is
         R2's: the mean rise of the copper node over the heater block without a face term (R2's 3D value is the mean of its copper-slab cells, a cell centre).
         Run: .venv/bin/python research/laminate-nodes/scripts/study_windows_reconcile.py
"""

import _bootstrap  # noqa: F401  (import paths)

import numpy as np

import gapnet as GN
import report as RP
import rule as RU
import study_windows_real as W

# 3D heater mean rise in K of the seven windows in R2's orientation, as printed by research/gerber-models/scripts/study_laminate_reference.py (column "3D (K)")
R2_3D = {"storm": 72.91, "chibi": 82.27, "easyeda": 76.05, "pcbrnd": 83.76, "pcad": 121.33, "dip": 90.62, "fritz": 135.46}
# R2's summary of the program with two laminate nodes on the pixels, against that 3D solution (gerber-models README, Review R2): mean -9.8 %, range -13.6 to -5.5 %


def main():
    """!
    @brief Run the seven windows in R2's orientation.
    @return None.
    """
    p = W.problem()
    rules = {"program": RU.PRESETS["program"], "rule": RU.Rule(), "n=8 all": RU.Rule(n_fixed=8, mask="all", vert=False, face=-1.0)}
    rows, acc = [], {}
    for name, m in W.load_windows(False, flip=True):
        short = name.split()[0]
        ref = R2_3D[short]
        row = {"window": short, "R2 3D K": (".2f", ref)}
        for cell in (0.8, 0.2):
            k = int(round(cell / W.PIX))
            n = m.shape[0] // k
            fill = m.reshape(n, k, n, k).mean(axis=(1, 3))[None]
            for rn, rl in rules.items():
                net = GN.build(p, cell, rl, fill=fill)
                th, _ = net.solve_steady()
                raw = GN.footprint_values(net, th, p, rl)[0][0]               # the node, no face term (R2's metric)
                e = 100.0 * (raw.mean() / ref - 1.0)
                row[f"{rn} @{cell}"] = e
                acc.setdefault(f"{rn} @{cell}", []).append(e)
        rows.append(row)
    RP.table(rows, list(rows[0]), title="Seven real windows in R2's orientation: error of the heater mean against R2's independent 3D solution (percent)")
    summ = [{"case": k, "mean %": float(np.mean(v)), "min %": float(np.min(v)), "max %": float(np.max(v))} for k, v in acc.items()]
    RP.table(summ, ["case", "mean %", "min %", "max %"], title="Summary (R2 printed for the program on the pixels: mean -9.8 %, range -13.6 to -5.5 %)")
    RP.save("windows_reconcile", {"rows": rows, "summary": summ})


if __name__ == "__main__":
    main()
