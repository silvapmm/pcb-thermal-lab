#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_remeasure.py
@brief Is the 3D solid still hotter when a square board is turned (A3)? Re-measured on the current program, with the board and the part turned separately.
@details A 40 mm square board in a 60 mm box (two copper planes, 2 W in a 6 mm square part at the centre, cell 1 mm) is turned by 0, 10, 20, 30
         and 45 degrees about its centre, at edge coefficients of 10, 100 and 1000 W/m2K. The continuum problem does not depend on the turn when the
         part turns with the board (case "both"), so the difference to the aligned square is a discretisation artefact. The cases "board only"
         (square turned, part on the grid) and "part only" (board on the grid, part turned 20 degrees) separate the two. Models: FVM, FDM, the
         program's 3D solid and the cut-cell variant of the 3D solid (`rotsq.VARIANTS["cutcell"]`, a copy made in memory). Prints a markdown table
         of the maximum temperature and the difference to the aligned square of the same model, and writes out/remeasure.json.
Usage: .venv/bin/python research/rotated-square-3d/scripts/study_remeasure.py   (from the repository root)
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import rotsq   # noqa: E402
import runs    # noqa: E402

MODELS = ("fvm", "fdm", "solid3d", "cutcell")
CASES = [("aligned", 0, 0.0), ("both 10", 10, 10.0), ("both 20", 20, 20.0), ("both 30", 30, 30.0), ("both 45", 45, 45.0),
         ("board only 20", 20, 0.0), ("board only 45", 45, 0.0), ("part only 20", 0, 20.0)]


def main():
    """!
    @brief Run the cases and print the table.
    @return None.
    """
    cell = 1.0
    res = {}
    for hs in (10.0, 100.0, 1000.0):
        for name, ang, pa in CASES:
            p = rotsq.board(ang, hs, side_mm=40.0, box_mm=60.0, part_mm=6.0, part_angle_deg=pa)
            res[(hs, name)] = {m: runs.tmax(p, m, cell) for m in MODELS}
        print(f"\n**h_side = {hs:g} W/m2K, cell {cell:g} mm** (maximum temperature in degC; in brackets the difference to the aligned square of the same model, K)\n")
        print("| case | " + " | ".join(MODELS) + " |")
        print("| :-- | " + " | ".join("--:" for _ in MODELS) + " |")
        for name, _, _ in CASES:
            row = res[(hs, name)]
            base = res[(hs, "aligned")]
            print(f"| {name} | " + " | ".join(f"{row[m]:.2f} ({row[m] - base[m]:+.2f})" for m in MODELS) + " |", flush=True)
    runs.save("remeasure.json", {f"{hs:g}|{n}": v for (hs, n), v in res.items()})


if __name__ == "__main__":
    main()
