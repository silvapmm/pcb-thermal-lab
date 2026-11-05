#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_warning.py
@brief Does the partial-copper footprint rule (lib/warnrule.py) fire where the program's via effect is wrong, and stay silent where it is right (cases, antipads, the frozen boards)?
@details For every case and cell of study_variants (needs `out/variants.json`: run study_variants.py first) it prints whether the rule fires for the FVM and the error of the program's
         via effect against the 3D reference; the confusion table counts, at the error threshold of 25 %, the cases fired and wrong, fired and right, silent and wrong, silent and right.
         It also runs the rule on the boards of the frozen regression (2, 1 and 0.5 mm) and on the documented 30 x 30 mm board.
         Run from the repository root: `.venv/bin/python research/via-partial-copper/scripts/study_warning.py`.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests", "regression"))
sys.path.insert(0, os.path.join(ROOT, "tests"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import cases                                                                  # noqa: E402
import warnrule                                                               # noqa: E402
from study_variants import PLAN, label                                        # noqa: E402

import regress_boards as B                                                    # noqa: E402
from test_maximum_principle import copper_edge_board                          # noqa: E402

THRESHOLD = 25.0          # error of the via effect (percent of the reference) that counts as wrong
FLOOR = 1.0               # K: an error is only counted when the reference via effect is above this (the antipad cases move the part by 0.3 K)


def main():
    """!
    @brief Print the confusion table and the false alarms on the frozen boards.
    @return None.
    """
    data = json.load(open(os.path.join(os.path.dirname(HERE), "out", "variants.json")))
    tab = {"fired wrong": 0, "fired right": 0, "silent wrong": 0, "silent right": 0}
    print(f"{'case':26s} {'cell':>6s} {'fires':>6s} {'ratio':>6s} {'err% (current FVM)':>19s}")
    for name, kw in PLAN:
        f = cases.CASES[name]
        for cell in (1.0, 0.5, 0.25, 0.125):
            hits = warnrule.partial_vias(f(**kw), cell)
            rec = data[f"{label(name, kw)}|fvm|current|{cell}"]
            ratio = min((h[2] for h in hits), default=1.0)
            big = rec["ref"][1] > FLOOR
            wrong = big and abs(rec["err_pct"]) > THRESHOLD
            tab[("fired " if hits else "silent ") + ("wrong" if wrong else "right")] += 1
            print(f"{label(name, kw):26s} {cell:6.3f} {str(bool(hits)):>6s} {ratio:6.2f} {rec['err_pct']:19.1f}{'' if big else '  (reference < 1 K)'}")
    print("confusion (reference via effect above 1 K):", tab)
    print("\nthe thermal-via array with antipads:")
    for cell in (1.0, 0.5, 0.25, 0.15):
        print(f"  array4 antipad 0.8 cell {cell}: {len(warnrule.partial_vias(cases.array4(), cell))} partial (via, layer) pairs of {len(cases.array4().vias)} vias")
    print("\ndocumented 30 mm board:")
    for cell in (1.0, 0.5, 0.25, 0.125):
        print(f"  cell {cell}: {len(warnrule.partial_vias(copper_edge_board(), cell))} partial")
    print("\nfrozen boards with vias:")
    for nm in B.board_names():
        p = B.build(nm)
        if p.vias:
            print(f"  {nm:18s} " + " ".join(f"{c}:{len(warnrule.partial_vias(p, c))}" for c in (2.0, 1.0, 0.5)))


if __name__ == "__main__":
    main()
