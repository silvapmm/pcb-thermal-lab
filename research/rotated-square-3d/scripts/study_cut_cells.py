#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_cut_cells.py
@brief Does the maximum temperature of a square board depend on where its edge falls against the grid (shifted by a fraction of a cell, or turned), and does the cut-cell copy of the 3D solid remove the dependence?
@details The continuum problem is invariant under a translation and a rotation of the board with its part, so any dependence is a discretisation
         artefact. A 20 mm square board in a 30 mm box (two copper planes, 2 W in a 3 mm square part at the centre, h_side 2000 W/m2K, which
         is the edge Biot number of the 40 mm board at 1000) is solved with cells of 1, 0.5 and 0.25 mm (20, 40 and 80 cells per side; with `--fine`
         also 0.125 mm for the program and the cut-cell copy), aligned, shifted by a quarter and by half a cell (a straight edge through the middle
         of the edge cells) and turned by 20 and 45 degrees, in the FVM, the FDM, the program's 3D solid and four copies of the 3D solid
         (`kx_physical`, `strip`, `cutcell_floor` and `cutcell`, see `lib/rotsq.py`). Prints markdown tables of the maximum temperature and of the
         difference to the aligned board of the same model and cell, and writes out/cut_cells.json.
Usage: .venv/bin/python research/rotated-square-3d/scripts/study_cut_cells.py [--fine]   (from the repository root)
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import rotsq   # noqa: E402
import runs    # noqa: E402

MODELS = ("fvm", "fdm", "solid3d", "kx_physical", "strip", "cutcell_floor", "cutcell")
LAYOUTS = [("aligned", 0, 0.0), ("shift 1/4 cell", 0, 0.25), ("shift 1/2 cell", 0, 0.5), ("turned 20", 20, 0.0), ("turned 45", 45, 0.0)]


def board_for(cell, angle, shift, hs=2000.0):
    """!
    @brief The 20 mm board of the study for a cell size, a turn and a shift.
    @param cell Cell size in mm (the shift is a fraction of it).
    @param angle Turn of the board and of the part, degrees.
    @param shift Shift of the board and the part in x and y, in cells.
    @param hs Edge coefficient in W/m2K.
    @return Problem.
    """
    return rotsq.board(angle, hs, side_mm=20.0, box_mm=30.0, part_mm=3.0, part_angle_deg=float(angle), shift_mm=(shift * cell, shift * cell))


def main():
    """!
    @brief Run the ladder and print the tables.
    @return None.
    """
    fine = "--fine" in sys.argv
    cells = [1.0, 0.5, 0.25] + ([0.125] if fine else [])
    res = {}
    for cell in cells:
        models = MODELS if cell > 0.125 else ("solid3d", "cutcell")
        layouts = LAYOUTS if cell > 0.125 else [LAYOUTS[0], LAYOUTS[2], LAYOUTS[3]]
        for name, ang, sh in layouts:
            p = board_for(cell, ang, sh)
            for m in models:
                res[(cell, name, m)] = runs.tmax(p, m, cell)
        print(f"\n**cell {cell:g} mm ({round(20 / cell)} cells per side)**, maximum temperature in degC (difference to the aligned board of the same model, K)\n")
        print("| layout | " + " | ".join(models) + " |")
        print("| :-- | " + " | ".join("--:" for _ in models) + " |")
        for name, _, _ in layouts:
            row = [res[(cell, name, m)] for m in models]
            base = [res[(cell, "aligned", m)] for m in models]
            print(f"| {name} | " + " | ".join(f"{t:.2f} ({t - b:+.2f})" for t, b in zip(row, base)) + " |", flush=True)
    runs.save("cut_cells.json", {f"{c:g}|{n}|{m}": v for (c, n, m), v in res.items()})


if __name__ == "__main__":
    main()
