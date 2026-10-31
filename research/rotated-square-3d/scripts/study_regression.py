#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_regression.py
@brief Does the cut-cell copy of the 3D solid change anything where the program was already right: rectangles, and the example board with the five outline presets at the default and at a high edge coefficient?
@details (1) A rectangular board (no outline) and a rectangle given as an outline on the grid lines must give the same answer in the program and in
         the copy (the first is bit-identical by construction: the copy only changes the outline branches). (2) The example board of the
         program (100 x 80 mm, 22 W, vias, heatsink) is cut to the five presets of the Board panel (ellipse, L, T, chamfer, rounded) and solved at
         1 mm with h_side 10 (the default) and 100 W/m2K in the program's 3D solid and in the copy; the FVM is shown for the gap between idealisations.
         The energy balance (heat to the air = power in) is printed for the copy.
Usage: .venv/bin/python research/rotated-square-3d/scripts/study_regression.py   (from the repository root)
"""

import copy
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "outline", "scripts"))

import rotsq                                  # noqa: E402
import runs                                   # noqa: E402
from outline_rectangle_study import outlines  # noqa: E402
from pcbthermal import Problem                # noqa: E402
from pcbthermal.examples import example_board  # noqa: E402


def main():
    """!
    @brief Print the two regression tables.
    @return None.
    """
    prog, cut = rotsq.variant_solid3d("program"), rotsq.variant_solid3d("cutcell")
    print("| board (cell 1 mm) | program | cut-cell copy | difference (K) |")
    print("| :-- | --: | --: | --: |")
    for name, outline in (("rectangle, no outline", None), ("rectangle as an outline", [[0, 0], [40, 0], [40, 40], [0, 40]])):
        p = Problem.new(40.0, 40.0, 2, h_side=100.0).add_full_copper()
        p.add_heater(1, 2.0, rect=(17, 17, 23, 23), name="U")
        if outline:
            p.set_outline(outline)
        a, b = runs.tmax(p, "solid3d", 1.0), runs.tmax(p, "cutcell", 1.0)
        print(f"| {name} | {a:.4f} | {b:.4f} | {b - a:+.4f} |", flush=True)

    print("\n| example board cut to | h_side | FVM | program 3D | cut-cell 3D | copy minus program (K) | heat to air / power, copy |")
    print("| :-- | --: | --: | --: | --: | --: | --: |")
    for name, poly in outlines(100.0, 80.0).items():
        for hs in (10.0, 100.0):
            p = example_board()
            p.board.h_side = hs
            p.board.outline = np.array(poly) / 1000.0
            fv = runs.tmax(p, "fvm", 1.0)
            a = runs.tmax(p, "solid3d", 1.0)
            r = cut.solve_steady(copy.deepcopy(p), cell_mm=1.0)
            out = sum(r.power_out.values()) / r.power_in
            print(f"| {name} | {hs:g} | {fv:.2f} | {a:.2f} | {r.t_max:.2f} | {r.t_max - a:+.2f} | {out:.4f} |", flush=True)


if __name__ == "__main__":
    main()
