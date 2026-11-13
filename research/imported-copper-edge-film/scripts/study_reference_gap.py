#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_reference_gap.py
@brief Question 1.1: how far is the program, imported or drawn copper, aligned or turned, from the references on the full-copper-inside-inset board, and does it converge to them?
@details The 20 mm board of `lib/study_outline_mask.py` (copper held 1.2 mm inside the edge, full copper on both layers, 4 mm heater of 1 W, h_top = h_bottom = 10) at one
         edge coefficient, for the program in its variants (imported or drawn copper, laminate rule on or off, aligned and 45 degrees) at the given cells, next to the independent
         two-sheet solver (the program's own idealisation, rule off) and the 3D truth `lib/truth3d.py` (real thickness, laminate resolved).
         Run: `.venv/bin/python research/imported-copper-edge-film/scripts/study_reference_gap.py <h_side> <cells, e.g. 0.5,0.25,0.125>`.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(HERE, "..", "lib"))

from pcbthermal import laminate                                                # noqa: E402
import study_outline_mask as sm                                                # noqa: E402
import indep_two_sheets as i2                                                  # noqa: E402
import truth3d                                                                 # noqa: E402


def program(h_side, ang, cell, imported, rule):
    """!
    @brief Mean heater rise of the program for one variant.
    @param h_side Edge coefficient W/m2K.
    @param ang Turn in degrees.
    @param cell Cell in mm.
    @param imported True for imported masks, False for zones.
    @param rule True for the laminate rule on.
    @return Mean rise K.
    """
    p = sm.problem(ang, False, h_side, imported=imported, pattern=False)
    if rule:
        return sm.heater_mean(p, cell)[0]
    with laminate.using(0.4, 1):
        return sm.heater_mean(p, cell)[0]


def main():
    """!
    @brief Print the table.
    @return None.
    """
    hs = float(sys.argv[1])
    cells = [float(c) for c in sys.argv[2].split(",")]
    print("references: two-sheet", [round(i2.solve(c * 1e-3, hs, pattern=False)[0], 4) for c in (0.1, 0.05)],
          "3D truth (cell 0.2, 0.1, nz 12)", [round(truth3d.solve(hs, c, 12)[0], 4) for c in (0.2, 0.1)])
    for imported in (True, False):
        for rule in (True, False):
            for ang in (0, 45):
                row = [round(program(hs, ang, c, imported, rule), 4) for c in cells]
                print("imported" if imported else "drawn", "rule" if rule else "norule", ang, cells, row, flush=True)


if __name__ == "__main__":
    main()
