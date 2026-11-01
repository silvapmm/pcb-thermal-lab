#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_solid3d.py
@brief Why the copper-fill gain of the 3D solid varies with the cell, and what the footprint of the barrel does to it.
@details Three parts. (1) The 3 x 3 via-array board of research/via-fill: open rise and copper-fill gain of the 3D solid of the program at 1, 0.5 and 0.25 mm (and 0.125 mm
         with the size limit raised) against the 3D reference with barrels drawn (`layered3d`). (2) The same board with the whole via array shifted by fractions of a cell: the
         gain should not depend on where the vias sit inside the cells, and a point feature does. (3) The footprint rules of `lib/solid_patch.py` (point, area, tuned).
         The 3D solid has real slabs for the copper planes, so a point sink in one cell column sees the same lattice constriction as the layered models (r_eq = 0.1985 dx).
Usage: python research/point-via-convergence/scripts/study_solid3d.py [--fine]   (from the repository root; about 8 minutes, --fine adds 0.125 mm with about 5 GB)
"""

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import program_cases as pc                                                  # noqa: E402
import solid_patch as sp                                                    # noqa: E402
from pcbthermal import solid3d                                              # noqa: E402


def shifted_board(fill, shift_mm):
    """!
    @brief The array board with every via (and nothing else) shifted along x and y.
    @param fill Fill conductivity.
    @param shift_mm Shift in mm.
    @return Problem.
    """
    p = pc.array_board(fill)
    for v in p.vias:
        v.x += shift_mm * 1e-3                                                  # coordinates are in metres
        v.y += shift_mm * 1e-3
    return p


def gain(cell, treatment, shift=0.0):
    """!
    @brief Open rise and copper-fill gain of the 3D solid for a footprint rule.
    @param cell Cell in mm.
    @param treatment "program" or a rule of solid_patch.
    @param shift Shift of the via array in mm.
    @return tuple (open rise, gain) in K.
    """
    out = []
    for fk in (0.0, 385.0):
        p = shifted_board(fk, shift)
        if treatment == "program":
            out.append(pc.max_rise(p, "solid3d", cell))
        else:
            with sp.patched(treatment):
                out.append(pc.max_rise(p, "solid3d", cell))
    return out[0], out[1] - out[0]


def main():
    """!
    @brief Run the three parts.
    @return None.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--fine", action="store_true")
    args = ap.parse_args()
    pc.load_libraries()
    cells = [1.0, 0.5, 0.25, 21.0 / 126] + ([0.125] if args.fine else [])
    print("## 1. 3D solid of the program, 3 x 3 array board: open rise / copper-fill gain (K)\n")
    with solid3d.size_limit(2_000_000):
        print("| rule | " + " | ".join(f"{c} mm" for c in cells) + " |")
        print("| :-- |" + " --: |" * len(cells))
        for tr in ("program", "point", "area", "tuned", "tuned_eta", "disc_eta"):
            print(f"| {tr} | " + " | ".join("{:.2f} / {:+.2f}".format(*gain(c, tr)) for c in cells) + " |", flush=True)
        print("\n## 2. Via array shifted inside the cells (0.5 mm cells; shift in mm): open / gain\n")
        print("| rule | " + " | ".join(f"{s}" for s in (0.0, 0.125, 0.25, 0.375)) + " |")
        print("| :-- |" + " --: |" * 4)
        for tr in ("program", "area", "tuned_eta", "disc_eta"):
            print(f"| {tr} | " + " | ".join("{:.2f} / {:+.2f}".format(*gain(0.5, tr, s)) for s in (0.0, 0.125, 0.25, 0.375)) + " |", flush=True)


if __name__ == "__main__":
    main()
