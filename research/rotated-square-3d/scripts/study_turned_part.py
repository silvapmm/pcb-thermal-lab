#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_turned_part.py
@brief (Review) Is the extra temperature of a part turned by 45 degrees in the 3D solid the discretisation of a turned source, or the sampling of its footprint?
@details A 20 mm rectangular board (no outline, so no cut cell; two copper planes, h_side 2000 W/m2K) with a 3 mm, 2 W part at the centre,
         aligned or turned by 45 degrees, at 0.5, 0.25 and 0.125 mm, in the program's 3D solid (footprint sampled on 4 x 4 points per cell) and in
         the copy `program_src8` (8 x 8, as the FVM). Prints the difference turned minus aligned in K and the share of the footprint area that the
         4 x 4 and 8 x 8 lattices keep. The continuum difference is in study_square_reference.py (-0.005 K).
Usage: .venv/bin/python research/rotated-square-3d/scripts/study_turned_part.py   (from the repository root)
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import rotsq                         # noqa: E402
import runs                          # noqa: E402
from pcbthermal import Problem, geometry   # noqa: E402


def board(turned):
    """!
    @brief The rectangular board with an aligned or turned part.
    @param turned True for the part turned by 45 degrees.
    @return Problem.
    """
    p = Problem.new(20.0, 20.0, 2, h_side=2000.0).add_full_copper()
    if turned:
        p.add_heater(1, 2.0, polygon=rotsq.turned_square(3.0, 45.0, (10.0, 10.0)), name="U")
    else:
        p.add_heater(1, 2.0, rect=(8.5, 8.5, 11.5, 11.5), name="U")
    return p


def main():
    """!
    @brief Print the table.
    @return None.
    """
    poly = np.array(rotsq.turned_square(3.0, 45.0, (10.0, 10.0))) / 1000.0
    print("| cell (mm) | area kept 4 x 4 | area kept 8 x 8 | program: turned minus aligned (K) | footprint 8 x 8: turned minus aligned (K) |")
    print("| --: | --: | --: | --: | --: |")
    for cell in (0.5, 0.25, 0.125):
        n = round(20.0 / cell)
        kept = [geometry.coverage_fraction(poly, n, n, cell / 1000, cell / 1000, s).sum() * (cell / 1000) ** 2 / geometry.polygon_area(poly) for s in (4, 8)]
        d = [runs.tmax(board(True), m, cell) - runs.tmax(board(False), m, cell) for m in ("solid3d", "program_src8")]
        print(f"| {cell:g} | {kept[0]:.4f} | {kept[1]:.4f} | {d[0]:+.2f} | {d[1]:+.2f} |", flush=True)


if __name__ == "__main__":
    main()
