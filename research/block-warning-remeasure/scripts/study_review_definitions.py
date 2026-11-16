#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_review_definitions.py
@brief Review check: is the 'temperature of a part' of the Lumped the same quantity as the FVM's, and does the 3D solid see a block error common to the layered models?

@details The study `study_block_pads.py` reads every part with `analysis.heater_stats`, which takes the hottest value of the drawn FIELD under the footprint. For the FVM and the
         Analytic that is the peak of the part. For the Lumped the field paints the footprint with its ring-0 node (no peak term); the Lumped's own peak of a part (node plus
         `peak_extra` plus the other heaters read at its centroid, `lumped.solve_steady`) enters only `SteadyResult.t_max`. This script reads, on the same boards:
         (a) the part peak: FVM field maximum, Lumped own peak (rebuilt with the program's formula from the networks the solve built), Analytic field maximum;
         (b) the part mean: footprint mean of each field (the Lumped node is a footprint mean);
         (c) optionally (`--solid`) the 3D solid at the same cell as an independent idealisation (real slabs, the block as a solid slab).
         Errors in percent of the FVM rise of the hottest part.
         Usage (from the repository root; one process, light):
             .venv/bin/python research/block-warning-remeasure/scripts/study_review_definitions.py [--cell-mm 0.5] [--solid] [--cases base]
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pcbthermal import analytic, fvm, lumped, solid3d                 # noqa: E402
from pcbthermal.analysis import heater_stats                          # noqa: E402
import study_block_pads as base                                       # noqa: E402

AMB = base.AMB

def read(model, p, cell):
    """!
    @brief Part peaks, part means and the hottest point of one model.
    @param model 'fvm', 'lumped', 'analytic' or 'solid3d'.
    @param p Problem.
    @param cell Cell in mm.
    @return dict: field_max (list), mean (list), own_peak (list; the Lumped's own peak from study_block_pads.lumped_part_peaks, else the field max), hot (rise of t_max), all in K above ambient.
    """
    mod = {"fvm": fvm, "lumped": lumped, "analytic": analytic, "solid3d": solid3d}[model]
    base._CAPTURED.clear()
    r = mod.solve_steady(p, cell_mm=cell)
    rows = heater_stats(r, p)
    fmax = [row["t_max"] - AMB for row in rows]
    mean = [row["t_mean"] - AMB for row in rows]
    own = base.lumped_part_peaks(p, r) if model == "lumped" else fmax
    return {"field_max": fmax, "mean": mean, "own_peak": own, "hot": r.t_max - AMB}


CASES = {
    "1pad": ("1 pad 12 mm, block", dict(n_pads=1)),
    "2pad": ("2 pads 12 mm, block", dict(n_pads=2)),
    "4pad": ("4 pads 12 mm, block", dict(n_pads=4)),
    "2pad_ctl": ("control, 2 pads, no block", dict(n_pads=2, with_block=False)),
    "2pad_40": ("2 pads, block 40x30", dict(block=(40.0, 30.0))),
    "2pad_h200": ("2 pads, h_extra 200", dict(h_extra=200.0)),
    "1pad_ctl": ("control, 1 pad, no block", dict(n_pads=1, with_block=False)),
}


def main():
    """!
    @brief Print, per case, the worst part error of each model with the field maximum, the Lumped own peak and the footprint mean, and the hottest point.
    @return None.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--cell-mm", type=float, default=0.5)
    ap.add_argument("--solid", action="store_true", help="also run the 3D solid at the same cell")
    ap.add_argument("--cases", default=",".join(CASES))
    a = ap.parse_args()
    models = ["lumped", "analytic"] + (["solid3d"] if a.solid else [])
    print(f"cell {a.cell_mm:g} mm; errors in % of the FVM rise of the hottest part (model - FVM), worst part by absolute value")
    head = "| Case | FVM hot K | L part field max | L part own peak | L part mean | L hot | L spread field max | L spread own peak | A part max | A part mean | A hot |"
    if a.solid:
        head += " 3D part max | 3D part mean | 3D hot |"
    print(head)
    print("|" + " :-- |" + " --: |" * (head.count("|") - 2))
    for key in a.cases.split(","):
        label, kw = CASES[key]
        p = base.make(**kw)
        ref = read("fvm", p, a.cell_mm)
        scale = max(ref["field_max"])

        def worst(vals, refs):
            """!
            @brief Worst part error in percent of the FVM part rise.
            @param vals Model values per part (K).
            @param refs FVM values per part (K).
            @return float.
            """
            return max(((v - r) / scale * 100.0 for v, r in zip(vals, refs)), key=abs)

        def spread(vals, refs):
            """!
            @brief Change of the hottest-to-coolest part spread against the FVM, in percent of the FVM part rise (the sharing of the heat between the pads).
            @param vals Model values per part (K).
            @param refs FVM values per part (K).
            @return float.
            """
            return ((max(vals) - min(vals)) - (max(refs) - min(refs))) / scale * 100.0

        res = {m: read(m, p, a.cell_mm) for m in models}
        L, A = res["lumped"], res["analytic"]
        cols = [worst(L["field_max"], ref["field_max"]), worst(L["own_peak"], ref["field_max"]), worst(L["mean"], ref["mean"]),
                (L["hot"] - ref["hot"]) / ref["hot"] * 100.0, spread(L["field_max"], ref["field_max"]), spread(L["own_peak"], ref["field_max"]),
                worst(A["field_max"], ref["field_max"]), worst(A["mean"], ref["mean"]), (A["hot"] - ref["hot"]) / ref["hot"] * 100.0]
        if a.solid:
            S = res["solid3d"]
            cols += [worst(S["field_max"], ref["field_max"]), worst(S["mean"], ref["mean"]), (S["hot"] - ref["hot"]) / ref["hot"] * 100.0]
        print(f"| {label} | {ref['hot']:.1f} | " + " | ".join(f"{c:+.1f}" for c in cols) + " |", flush=True)


if __name__ == "__main__":
    main()
