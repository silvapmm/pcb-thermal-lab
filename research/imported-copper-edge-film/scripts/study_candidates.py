#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_candidates.py
@brief Question 2: candidate corrections of the cool edge bias of imported copper on a board with an outline, measured against the 3D truth on turns and shifts of the board.
@details Bench: the 20 mm board of `lib/cases.py` (imported copper held `inset` inside the edge, full copper inside, 2 or 4 layers, 4 mm heater of 1 W), turned by 0, 11.25, 22.5,
         33.75 and 45 degrees and shifted against the grid by 0 and 0.3 of a cell (ten boards), at the given cells and edge coefficients. Candidates (names below) are variants of
         `lib/variants.py` and of the laminate options. Error = program / truth - 1 with the truth of `scripts/study_truth.py` (`lib/truth_values.json`, same layers, inset, h_side).
         Prints, per candidate, edge coefficient and cell: mean error, spread (max - min), worst |error|, the heat-balance error, the unknowns and the seconds of the aligned board.
         Run: `.venv/bin/python research/imported-copper-edge-film/scripts/study_candidates.py <layers> <inset mm> <h_side list> <cell list> <candidate list|all> <out.json>`.
"""

import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))

import cases                                                                   # noqa: E402
import study_outline_mask as sm                                                # noqa: E402
import variants                                                                # noqa: E402
from pcbthermal import fvm, laminate                                           # noqa: E402

# name -> (variant switches, n_max)
CANDIDATES = {
    "c0_program": ({}, 4),
    "c1_series": ({"film": "series"}, 4),
    "c2_node_n8": ({}, 8),
    "c3_node_n16": ({}, 16),
    "c4_node_cos4": ({"grade": "cos"}, 4),
    "c5_series_n16": ({"film": "series"}, 16),
    "c6_node_cos8": ({"grade": "cos"}, 8),
    "c7_series_half": ({"film": "series", "alpha": 0.5}, 4),
    "c8_series_cos8": ({"film": "series", "grade": "cos"}, 8),
    "c9_centroid": ({"film": "centroid"}, 4),
    "c10_centroid_half": ({"film": "centroid", "alpha": 0.5}, 4),
    "c11_centroid_n16": ({"film": "centroid"}, 16),
}
ANGLES = (0.0, 11.25, 22.5, 33.75, 45.0)
SHIFTS = (0.0, 0.3)


def truth_for(layers, inset, h):
    """!
    @brief The stored 3D truth.
    @param layers Layers.
    @param inset Inset in mm.
    @param h Edge coefficient.
    @return Truth (K).
    """
    data = json.load(open(os.path.join(HERE, "..", "lib", "truth_values.json")))
    return data[f"{layers}|{inset}|{h}"]["truth"]


def bench(layers, inset, h, cell, name, pattern=False):
    """!
    @brief Run one candidate on the ten boards.
    @param layers Layers.
    @param inset Inset in mm.
    @param h Edge coefficient.
    @param cell Cell in mm.
    @param name Candidate name.
    @param pattern Stripes and pad on the top layer (the truth does not hold then; error against the finest-cell value is the caller's).
    @return Dict of statistics, with the errors list.
    """
    sw, nmax = CANDIDATES[name]
    cases.set_inset(inset)
    errs, bal, t_aligned, unk = [], 0.0, 0.0, 0
    tr = None if pattern else truth_for(layers, inset, h)
    vals = {}
    for sh in SHIFTS:
        sm.C = 15.0 + sh * cell
        for ang in ANGLES:
            p = cases.build("square", "imported", h, layers=layers, ang=ang, pattern=pattern)
            t0 = time.time()
            with variants.use(**sw), laminate.using(0.4e-3 if nmax == 4 else 0.05e-3, nmax):
                m, tm, be = cases.run(p, cell)
                if ang == 0.0 and sh == 0.0:
                    t_aligned = time.time() - t0
                    unk = int(fvm.unknowns(p, cell)[0])
            vals[f"{sh}|{ang}"] = m
            if tr:
                errs.append(100 * (m / tr - 1))
            bal = max(bal, abs(be))
    sm.C = 15.0
    out = {"vals": vals, "balance": bal, "seconds_aligned": round(t_aligned, 2), "unknowns": unk}
    if errs:
        out.update({"mean": float(np.mean(errs)), "spread": float(np.ptp(errs)), "worst": float(np.max(np.abs(errs))), "errs": errs})
    return out


def main():
    """!
    @brief Run the candidates and print and store the table.
    @return None.
    """
    layers, inset = int(sys.argv[1]), float(sys.argv[2])
    hs = [float(x) for x in sys.argv[3].split(",")]
    cells = [float(x) for x in sys.argv[4].split(",")]
    names = list(CANDIDATES) if sys.argv[5] == "all" else sys.argv[5].split(",")
    res = {}
    for h in hs:
        for c in cells:
            for n in names:
                r = bench(layers, inset, h, c, n)
                res[f"{h}|{c}|{n}"] = r
                print(f"h_side {h:6g} cell {c:5g} {n:16s} mean {r['mean']:+6.2f} spread {r['spread']:5.2f} worst {r['worst']:5.2f} balance {r['balance']:.0e} unknowns {r['unknowns']} s {r['seconds_aligned']}", flush=True)
    json.dump(res, open(sys.argv[6], "w"))


if __name__ == "__main__":
    main()
