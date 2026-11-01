#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_reference_3d.py
@brief Does the fine-grid layered reference agree with the 3D solver with the barrel drawn? The via effect of the unit cell (README 3.2).
@details The periodic unit cell of `program_cases.unit_cell_board` (pitch 4 mm, four planes, source over the whole top, via at the centre), solved on a quadrant by the
         fine-grid layered solver (`resolved_boards.unit_cell`, 1/32 mm) and by the independent 3D solver `layered3d.py` with the barrel drawn (`resolved_boards.unit_cell_3d`,
         1/16, 1/32 and 1/48 mm, four slabs per gap, the plane whole across the bore). Prints the via effect E of both and the 3D one relative to the layered one.
         Written by the review: the numbers of README 3.2 were printed by no script of the folder.
         Run from the repository root: `.venv/bin/python research/point-via-convergence/scripts/study_reference_3d.py` (about four minutes).
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import numpy as np                                                          # noqa: E402

import program_cases as pc                                                  # noqa: E402
import resolved_boards as rb                                                # noqa: E402
import sheets2d                                                             # noqa: E402

PITCH = 4.0                                                                 # mm
CELLS_3D = (1 / 16, 1 / 32, 1 / 48)                                         # mm
CELL_2D = 1 / 32                                                            # mm


def layered_effect(par, dx):
    """!
    @brief Via effect of the unit cell by the fine-grid layered solver (quadrant, 1 W on the whole cell).
    @param par layer_parameters of the unit-cell board.
    @param dx Cell size in m.
    @return float E in K.
    """
    n = int(round(par["width"] / 2 / dx))
    S, gz, g_amb = rb._arrays(par, n, dx, [], par["r_via"][0], 0.0, None)
    Q = np.zeros((len(par["S"]), n, n))
    Q[0] = 0.25 / (n * n)
    t_no = float(sheets2d.solve(S, gz, g_amb, Q, dx).max())
    return t_no - rb.unit_cell(par, dx, 1.0)


def solid_effect(par, dx):
    """!
    @brief Via effect of the unit cell by the 3D solver with the barrel drawn (quadrant, 1 W on the whole cell).
    @param par layer_parameters of the unit-cell board.
    @param dx Cell size in m.
    @return float E in K.
    """
    half = par["width"] / 2
    n = int(round(half / dx))
    t_no = rb.board_3d(par, dx, [], n, (0, 0, half, half), 0.25)
    return t_no - rb.unit_cell_3d(par, dx, 1.0)


def main():
    """!
    @brief Print the table of README 3.2 (unit cell).
    @return None.
    """
    pc.load_libraries()
    print("| via | E layered 1/32 mm (K/W) | " + " | ".join(f"3D {c:.4f} mm" for c in CELLS_3D) + " |")
    print("| :-- | --: | " + " | ".join("--:" for _ in CELLS_3D) + " |")
    for dia, fill in ((0.3, 0.0), (0.3, 385.0), (0.6, 0.0), (0.6, 385.0)):
        par = pc.layer_parameters(pc.unit_cell_board(PITCH, dia, fill, 4))
        e2 = layered_effect(par, CELL_2D * 1e-3)
        cols = []
        for c in CELLS_3D:
            e3 = solid_effect(par, c * 1e-3)
            cols.append(f"{e3:.2f} ({(e3 / e2 - 1) * 100:+.2f} %)")
        print(f"| {dia} mm {'copper' if fill else 'open'} | {e2:.2f} | " + " | ".join(cols) + " |", flush=True)


if __name__ == "__main__":
    main()
