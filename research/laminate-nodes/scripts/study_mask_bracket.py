#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_mask_bracket.py
@brief Why do the masks "edge", "margin none" and "margin 1 cell" have a lower mean error than the proposed mask (README 3.4)? The signed error of every variant per board (review).
@details Question answered: a partial mask refines fewer cells than "every cell" at the same n, so a physically sound partial mask should read between the program (n = 1, the coolest)
         and "every cell" (the most refined): an answer **hotter** than "every cell" cannot come from more resolution. Where the mask ends, the interior nodes of the last refined cell
         have no lateral link to the next cell (whose laminate is lumped into its copper nodes), so a mask that ends where the laminate still carries heat sideways makes an artificial
         insulating wall. The script prints the signed error of each variant on the boards of study_mask.py and flags a variant that leaves the bracket [program, every cell] by more than
         0.3 point. References from the cache of runner.py (run study_s0_four_treatments.py first).
         Run: .venv/bin/python research/laminate-nodes/scripts/study_mask_bracket.py
"""

import _bootstrap  # noqa: F401  (import paths)

import boards as BD
import report as RP
import rule as RU
import runner as RN


def main():
    """!
    @brief Run the variants and print the signed errors.
    @return None.
    """
    specs = [s for s in BD.simple_set() if ("window 6" in s.name or "pad 10" in s.name or "window 4" in s.name) and "uniform" not in s.name]
    base = RU.Rule()
    variants = {"program": RU.PRESETS["program"], "margin none": RU.with_(base, margin="none"), "margin 1": RU.with_(base, margin="1"), "proposed": base,
                "mask edge": RU.with_(base, mask="edge"), "every cell": RU.with_(base, mask="all")}
    rows, out = [], {k: 0 for k in variants}
    for s in specs:
        ref = RN.reference(s)["max"]
        e = {k: RN.err(RN.fvm_peak(s, rl, 0.5)["peak"], ref) for k, rl in variants.items()}
        lo, hi = min(e["program"], e["every cell"]), max(e["program"], e["every cell"])
        row = {"board": s.name}
        for k, v in e.items():
            outside = v > hi + 0.3 or v < lo - 0.3
            out[k] += outside
            row[k] = f"{v:+.2f}" + (" *" if outside else "")
        rows.append(row)
    RP.table(rows, list(rows[0]), title="Signed error of the peak (percent); * outside [program, every cell] by more than 0.3 point")
    RP.table([{"variant": k, "boards outside the bracket": v} for k, v in out.items()], ["variant", "boards outside the bracket"])
    RP.save("mask_bracket", {"rows": rows, "outside": out})


if __name__ == "__main__":
    main()
