#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_n_law.py
@brief The 1/n law and the choice of the number of nodes: error against n per stack-up, Richardson in n, the grading, and the cost-accuracy table of the law n = min(n_max, ceil(d / s_max)).
@details Question answered: how does the error of the FVM with the construction fall with n on every kind of board (one-layer, two-layer thin and thick, typical 4 and 6 layers; a window
         and a pad), is it 1 / n, where does it stop, and which pair (s_max, n_max) is the best compromise between error and unknowns? Part A: n = 1, 2, 3, 4, 6, 8 with equal and with 2:1 graded
         sub-gaps, mask bare + margin, vertical correction on, face term on; the fit e = e_inf + a / n on n >= 2 (report.fit_inverse_n) and the Richardson limit in n from (2, 4, 8) (ratio 2). Part B:
         the grid of laws s_max in {0.2, 0.3, 0.4, 0.6, 0.8} mm x n_max in {3, 4, 6, 8}: for every board the error and the ragged unknown ratio, then the mean absolute error, the largest, and the
         mean ratio, so that the choice is a point on a curve and not a taste. Cell 0.5 mm, reference 0.25 mm / 8 sub-slabs.
         Output: out/n_law.json. Run: .venv/bin/python research/laminate-nodes/scripts/study_n_law.py
"""

import _bootstrap  # noqa: F401  (import paths)

import numpy as np

import boards as BD
import ref3d as R3
import report as RP
import rule as RU
import runner as RN

NS = (1, 2, 3, 4, 6, 8)


def main():
    """!
    @brief Part A and part B.
    @return None.
    """
    specs = [s for s in BD.simple_set() if ("window 6" in s.name or "pad 10" in s.name) and "uniform" not in s.name]
    base = RU.Rule()
    partA, rows = [], []
    for s in specs:
        ref = RN.reference(s)["max"]
        row = {"board": s.name}
        for ratio in (1.0, 2.0):
            errs = [RN.err(RN.fvm_peak(s, RU.with_(base, n_fixed=n, ratio=ratio), 0.5)["peak"], ref) for n in NS]
            row[f"r{ratio:g}"] = [round(e, 3) for e in errs]
            fit = RP.fit_inverse_n(NS, errs)
            row[f"fit r{ratio:g}"] = fit
            row[f"rich r{ratio:g}"] = R3.richardson([errs[1], errs[3], errs[5]], 2.0)       # n = 2, 4, 8
        partA.append(row)
        print(s.name, "equal:", row["r1"], " graded:", row["r2"], " e_inf %.2f a %.2f" % (row["fit r1"]["e_inf"], row["fit r1"]["a"]), flush=True)
    RP.save("n_law_A", partA)

    for s_max in (0.2e-3, 0.3e-3, 0.4e-3, 0.6e-3, 0.8e-3):
        for n_max in (3, 4, 6, 8):
            rl = RU.with_(base, s_max=s_max, n_max=n_max)
            e, u = [], []
            for s in specs:
                r = RN.fvm_peak(s, rl, 0.5)
                e.append(RN.err(r["peak"], RN.reference(s)["max"]))
                u.append(r["counts"]["ratio_ragged"])
            rows.append({"s_max mm": (".1f", s_max * 1e3), "n_max": n_max, "mean |e| %": (".2f", float(np.mean(np.abs(e)))), "max |e| %": (".2f", float(np.max(np.abs(e)))),
                         "mean unk x": (".2f", float(np.mean(u))), "max unk x": (".2f", float(np.max(u)))})
    RP.table(rows, ["s_max mm", "n_max", "mean |e| %", "max |e| %", "mean unk x", "max unk x"], title="Laws n = min(n_max, ceil(d / s_max)): error and cost over the boards of part A")
    RP.save("n_law_B", rows)


if __name__ == "__main__":
    main()
