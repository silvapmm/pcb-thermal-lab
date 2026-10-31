#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_mask.py
@brief Which cells get the nodes: the type of the mask, the fill threshold, the margin and its shape, against error and unknowns, on the simple boards.
@details Question answered: is "cells where a layer next to the gap has copper fill below 1, plus a margin of a gap thickness and a cell" (bare-spot-under-source, gap-subdivision) the best
         mask, or is the cell next to a copper edge enough ("edge"), or is every cell cheaper than the bookkeeping ("all")? Variants: mask in (bare, edge, all); threshold in (1.0, 0.98, 0.9);
         margin in (none, 1 cell, gap + 1 cell (default), two gaps); shape in (disc, diamond, square). For each variant over the boards of study_n_law (windows and pads on one-, two-,
         four- and six-layer boards, n by the default law): the error against the reference (mean absolute, largest), the ragged and the dense unknown ratio, and the number of cells that
         differ from "every cell refined" in the peak (the cost of leaving a cell out). The real windows (many fine features) are run by study_windows_real.py with the same variants.
         Output: out/mask.json. Run: .venv/bin/python research/laminate-nodes/scripts/study_mask.py
"""

import _bootstrap  # noqa: F401  (import paths)

import numpy as np

import boards as BD
import report as RP
import rule as RU
import runner as RN


def main():
    """!
    @brief Run the variants.
    @return None.
    """
    specs = [s for s in BD.simple_set() if ("window 6" in s.name or "pad 10" in s.name or "window 4" in s.name) and "uniform" not in s.name]
    base = RU.Rule()
    variants = {"proposed (bare, 1.0, gap, disc)": base}
    for mk in ("edge", "all"):
        variants[f"mask {mk}"] = RU.with_(base, mask=mk)
    for th in (0.98, 0.9):
        variants[f"threshold {th}"] = RU.with_(base, threshold=th)
    for mg in ("none", "1", "2gap"):
        variants[f"margin {mg}"] = RU.with_(base, margin=mg)
    for sh in ("diamond", "square"):
        variants[f"shape {sh}"] = RU.with_(base, shape=sh)
    all_rule = RU.with_(base, mask="all")
    rows = []
    for name, rl in variants.items():
        e, e_all, ru, rd = [], [], [], []
        for s in specs:
            ref = RN.reference(s)["max"]
            r = RN.fvm_peak(s, rl, 0.5)
            ra = RN.fvm_peak(s, all_rule, 0.5)
            e.append(RN.err(r["peak"], ref))
            e_all.append(RN.err(ra["peak"], ref))
            ru.append(r["counts"]["ratio_ragged"])
            rd.append(r["counts"]["ratio_dense"])
        rows.append({"variant": name, "mean |e| %": (".2f", float(np.mean(np.abs(e)))), "max |e| %": (".2f", float(np.max(np.abs(e)))),
                     "vs every cell, max points": (".2f", float(np.max(np.abs(np.array(e) - np.array(e_all))))), "ragged x": (".2f", float(np.mean(ru))), "dense x": (".2f", float(np.mean(rd)))})
    RP.table(rows, ["variant", "mean |e| %", "max |e| %", "vs every cell, max points", "ragged x", "dense x"], title="Mask variants over the simple boards (cell 0.5 mm, n by the default law)")
    RP.save("mask", rows)


if __name__ == "__main__":
    main()
