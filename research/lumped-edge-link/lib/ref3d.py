#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file ref3d.py
@brief The independent 3D reference of a square part near a side or a corner of a full-copper board: the test helper `tests/helpers/layered3d.py` (imports nothing of the program).
@details Only NUMBERS are read from the program's Problem (copper and FR-4 conductivities, thicknesses, films). Insulated sides (h_side = 0), isotropic FR-4 (the through-thickness
         0.3 W/mK; the program is run with the same value in the plane), the film acting also under the source as in the program. A part centred along a side uses the symmetry plane
         (half board, half source, half power); a corner part uses the whole board. The part's surface temperatures come from the top row of cells under the part.
"""

import os
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tests", "helpers"))
import layered3d  # noqa: E402


def solve(p, pos, side_mm, place, dx_mm, n_sub=4):
    """!
    @brief Peak and mean of the part (rise in K) by the 3D solver.
    @param p Problem from boards.board with h_side 0 and isotropic FR-4 (k_fr4_inplane = k_fr4_through).
    @param pos Centre (x, y) of the part in mm.
    @param side_mm Side of the part in mm.
    @param place "edge" (centred along the left side, half board by symmetry) or "corner" (whole board).
    @param dx_mm Cell in mm (it must divide the part side and its position).
    @param n_sub Sub-slabs of every dielectric gap.
    @return dict peak, mean (K) and the number of unknowns.
    """
    b = p.board
    m = b.materials
    dx = dx_mm * 1e-3
    W = b.width
    H = b.height / 2 if place == "edge" else b.height
    nx, ny = int(round(W / dx)), int(round(H / dx))
    s = side_mm * 1e-3
    x0, x1 = pos[0] * 1e-3 - s / 2, pos[0] * 1e-3 + s / 2
    if place == "edge":
        src, power = (x0, 0.0, x1, s / 2), p.heaters[0].power / 2.0     # the symmetry plane through the part's centre line
    else:
        y0 = pos[1] * 1e-3 - s / 2
        src, power = (x0, y0, x1, y0 + s), p.heaters[0].power
    gaps = b.gap_thicknesses()
    slabs = []
    for l in range(b.layers):
        slabs.append((float(b.copper_thickness[l]), m.k_copper, 1))
        if l < b.layers - 1:
            slabs.append((float(gaps[l]), float(b.gap_properties()[0][0]), n_sub))
    res = layered3d.solve(dx, nx, ny, slabs, src, power, b.h_top, b.h_bottom, film_under_source=True)
    return {"peak": float(res["max_source"]), "mean": float(res["mean_source"]), "unknowns": int(res["T"].size)}
