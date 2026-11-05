#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_turn_frame_reference.py
@brief Are the references of the turn sweep (README 11.2) right? The turned board solved in its own frame, where no cell is cut (review, README 11.8).
@details The sweep of `study_cutcell_sweep.py` compares each turned square with the same board at a cell 8 times finer, where the turned edge still cuts
         cells. Here the board is solved in its own frame instead: the 20 mm square aligned with the grid (a rectangle without an outline, no cut cell) and
         the part turned by the opposite angle about the board centre, the program's FVM at 1/8 and 1/16 mm and a Richardson step (second order). The
         coarse schemes are then measured against this reference, and the spread of their error over the turns 0 to 45 degrees is printed next to the
         reference of the sweep. Light: about 70 s and 0.8 GB.
Usage: .venv/bin/python research/rotated-square-3d/scripts/study_turn_frame_reference.py   (from the repository root)
"""

import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import study_cutcell_sweep as sw     # noqa: E402
import fvm_cutcell as fc             # noqa: E402
from pcbthermal import Problem       # noqa: E402

SCHEMES = ("program", "program@exact", "links", "links@exact", "links+strip")
OUT = os.path.join(os.path.dirname(HERE), "out")


def frame_board(angle, h_side, off, pc):
    """!
    @brief The board of `study_cutcell_sweep.edge_board` (20 mm square turned by `angle` in a 30 mm box) seen in its own frame.
    @param angle Turn of the board in degrees (the part is turned by the opposite angle).
    @param h_side Edge coefficient in W/m2K.
    @param off Offset of the part from the box centre along x in mm (as in the sweep).
    @param pc Shift of the part on both axes in mm (half a coarse cell in the sweep).
    @return Problem: a 20 x 20 mm rectangle, full copper on two layers, 2 W in the turned 3 mm part.
    """
    a = math.radians(-angle)
    # Centre of the part relative to the board centre, turned into the frame of the board
    px, py = off + pc, pc
    cx = 10.0 + px * math.cos(a) - py * math.sin(a)
    cy = 10.0 + px * math.sin(a) + py * math.cos(a)
    pts = [[cx + x * math.cos(a) - y * math.sin(a), cy + x * math.sin(a) + y * math.cos(a)] for x, y in ((-1.5, -1.5), (1.5, -1.5), (1.5, 1.5), (-1.5, 1.5))]
    p = Problem.new(20.0, 20.0, 2, h_side=h_side).add_full_copper()
    p.add_heater(1, 2.0, polygon=pts, name="U")
    return p


def main():
    """!
    @brief Print the spread of the error over the turns against the frame reference, and the largest difference between the two references.
    @return None.
    """
    cell = 1.0
    out = {}
    print("| part offset (mm) | h_side | angle | frame reference (degC) | sweep reference (degC) | " + " | ".join(f"{s} error (K)" for s in SCHEMES) + " |")
    print("| --: | --: | --: | --: | --: | " + " | ".join("--:" for _ in SCHEMES) + " |")
    for off in (0.0, 3.5):
        for hs in (10.0, 100.0, 2000.0):
            errs = {s: [] for s in SCHEMES}
            for ang in range(0, 50, 5):
                t1 = fc.tmax(frame_board(ang, hs, off, cell / 2), 0.125, "program")
                t2 = fc.tmax(frame_board(ang, hs, off, cell / 2), 0.0625, "program")
                ref = t2 + (t2 - t1) / 3.0
                kw = dict(angle=float(ang), h_side=hs, shape="square", off=off, pc=cell / 2)
                ref_sweep = sw.reference(kw, cell)[0]
                row = []
                for s in SCHEMES:
                    e = sw.tmax(sw.edge_board(**kw), cell, s) - ref
                    errs[s].append(e)
                    row.append(f"{e:+.3f}")
                out[f"{off:g}|{hs:g}|{ang}"] = {"frame": ref, "sweep": ref_sweep}
                print(f"| {off:g} | {hs:g} | {ang} | {ref:.3f} | {ref_sweep:.3f} | " + " | ".join(row) + " |", flush=True)
            for s in SCHEMES:
                spread = max(errs[s]) - min(errs[s])
                out[f"{off:g}|{hs:g}|spread|{s}"] = spread
                print(f"SPREAD part offset {off:g} h_side {hs:g} {s}: {spread:.3f} K", flush=True)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "turn_frame_reference.json"), "w") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
