#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_part_across_outline.py
@brief (Review) Why does the example board cut to a T move by +0.2 K in the cut-cell copy at the default edge coefficient, and is the program right there?
@details The part U1 of the example board (30 to 40 mm x 35 to 45 mm) hangs over the cut-away corner of the T outline (stem from x = 33.33 mm
         below y = 40 mm). The program (FVM, FDM and 3D solid) gives every board cell the power of the part's cover of the whole cell, so a cell
         that the outline cuts receives the power of its whole area on its board part. The study solves (a) a small T board (30 x 24 mm, two copper
         planes, 2 W part 9 to 12 x 10 to 14 mm over the re-entrant corner at x = 31/3 mm, y = 12 mm) and (b) the example board cut to the T,
         both at h_side 10 W/m2K, at cells where the outline falls on grid lines (1/3, 1/6, 1/12 mm for (a), 2/3 mm for (b): no cell is cut and
         every rule agrees) and where it cuts cells (1, 0.5, 0.25, 0.125 mm and 1 mm), in the program's FVM and 3D solid and in copies in which the
         power of a part is spread over the board part of each cell (`rotsq.fvm_part_on_board`, variant `program_part_on_board`).
Usage: .venv/bin/python research/rotated-square-3d/scripts/study_part_across_outline.py   (from the repository root)
"""

import copy
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "outline", "scripts"))

import rotsq                                   # noqa: E402
import runs                                    # noqa: E402
from outline_rectangle_study import outlines   # noqa: E402
from pcbthermal import Problem, fvm            # noqa: E402
from pcbthermal.examples import example_board  # noqa: E402


def small_t():
    """!
    @brief The small T board with the part over its re-entrant corner.
    @return Problem.
    """
    a = 31.0 / 3.0
    b = 30.0 - a
    p = Problem.new(30.0, 24.0, 2, h_side=10.0).add_full_copper()
    p.add_heater(1, 2.0, rect=(9, 10, 12, 14), name="U")
    p.set_outline([[0, 12], [a, 12], [a, 0], [b, 0], [b, 12], [30, 12], [30, 24], [0, 24]])
    return p


def example_t():
    """!
    @brief The example board cut to the T preset, h_side 10 W/m2K.
    @return Problem.
    """
    p = example_board()
    p.board.h_side = 10.0
    p.board.outline = np.array(outlines(100.0, 80.0)["T"]) / 1000.0
    return p


def row(p, cell, with_3d=True):
    """!
    @brief Maximum temperature of one board at one cell in the four models.
    @param p Problem.
    @param cell Cell in mm.
    @param with_3d Also the 3D solid and its copy.
    @return List of four temperatures in degC (FVM, FVM copy, 3D, 3D copy; None where not run).
    """
    out = [fvm.solve_steady(copy.deepcopy(p), cell_mm=cell).t_max, rotsq.fvm_part_on_board().solve_steady(copy.deepcopy(p), cell_mm=cell).t_max]
    out += [runs.tmax(copy.deepcopy(p), m, cell) for m in ("solid3d", "program_part_on_board")] if with_3d else [None, None]
    return out


def main():
    """!
    @brief Print the two tables.
    @return None.
    """
    res = {}
    print("| board | cell (mm) | outline on grid lines | FVM | FVM, power on the board part | 3D solid | 3D, power on the board part |")
    print("| :-- | --: | :-- | --: | --: | --: | --: |")
    for name, make, cells in (("small T", small_t, (1.0, 0.5, 1 / 3, 0.25, 1 / 6, 0.125, 1 / 12)), ("example board, T", example_t, (1.0, 2 / 3))):
        for cell in cells:
            on_grid = abs((31.0 / 3.0 if name == "small T" else 100.0 / 3.0) / cell - round((31.0 / 3.0 if name == "small T" else 100.0 / 3.0) / cell)) < 1e-6
            r = row(make(), cell, with_3d=cell > 0.1)
            res[f"{name}|{cell:.4f}"] = r
            txt = " | ".join("-" if t is None else f"{t:.2f}" for t in r)
            print(f"| {name} | {cell:.4f} | {'yes' if on_grid else 'no'} | {txt} |", flush=True)
    runs.save("part_across_outline.json", res)


if __name__ == "__main__":
    main()
