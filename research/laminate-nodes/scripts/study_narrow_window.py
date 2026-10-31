#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_narrow_window.py
@brief Windows narrower than the gap (the -9 % left by bare-spot-under-source): separate the cell from the number of nodes, and say whether it is a limit or a cure.
@details Question answered: for a window of width w in the top copper of a two-layer board over a gap d (full copper below), the part 6 mm centred, why does the error stay at -9 % for w < d
         (2 mm on 1.6 mm), is it the cell (a 2 mm window is 4 cells at 0.5 mm), the number of nodes (a 1/n tail), or the idealisation (one temperature per cell across a window narrower than the
         gap it opens)? Sweep: w in (0.5, 1, 2, 3, 4, 6) mm, d in (0.2, 0.4, 0.8, 1.6, 3.2) mm; cells 0.25 and 0.5 mm; n = 1, 2, 4, 8, the default law, and the default law with the cell
         halved; the reference at 0.125 mm / 8 sub-slabs (windows of 0.5 mm are 4 reference cells). Printed: the error table over (w / d), the error of the best n against the reference
         at the same cell (the "same-cell" 3D solver is the reference at the cell of the program, so that the in-plane error of the cell is separated: 3D at the program's cell and sub-slabs
         refined), and the w / d at which the error of the default law exceeds 5 %. Output: out/narrow_window.json.
         Run: .venv/bin/python research/laminate-nodes/scripts/study_narrow_window.py [--quick]
"""

import _bootstrap  # noqa: F401  (import paths)

import sys

import boards as BD
import report as RP
import rule as RU
import runner as RN


def main():
    """!
    @brief Run the sweep.
    @return None.
    """
    ws = (1, 2, 4, 6) if "--quick" in sys.argv else (0.5, 1, 2, 3, 4, 6)
    ds = (0.4, 1.6) if "--quick" in sys.argv else (0.2, 0.4, 0.8, 1.6, 3.2)
    rows = []
    for d in ds:
        for w in ws:
            s = BD.Spec(f"2L {d} window {w}", layers=2, thickness=d + 0.07, shapes=[("window", w), ("full",)])      # gap d: board thickness minus the two 35 um coppers
            ref = RN.reference(s, 0.125, 8)["max"]
            for cell in (0.5, 0.25):
                same = RN.reference(s, cell, 16)["max"]                                      # the 3D solver on the program's cell: separates the in-plane error of the cell
                row = {"gap mm": d, "w mm": w, "w/d": (".2f", w / d), "cell": cell}
                for n in (1, 2, 4, 8):
                    row[f"n={n}"] = RN.err(RN.fvm_peak(s, RU.Rule(n_fixed=n), cell)["peak"], ref)
                row["law"] = RN.err(RN.fvm_peak(s, RU.Rule(), cell)["peak"], ref)
                row["n=8 vs same-cell 3D"] = RN.err(RN.fvm_peak(s, RU.Rule(n_fixed=8), cell)["peak"], same)
                row["cell effect (same-cell 3D vs ref)"] = RN.err(same, ref)
                rows.append(row)
    RP.table(rows, list(rows[0]), title="Narrow windows: error of the peak against the 0.125 mm reference, percent")
    RP.save("narrow_window", rows)


if __name__ == "__main__":
    main()
